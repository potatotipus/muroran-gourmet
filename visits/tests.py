from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from community.models import Favorite, Review
from restaurants.models import Restaurant
from .models import Visit
from .services import visit_summary


class VisitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='visitor')
        cls.other = get_user_model().objects.create_user(username='another-visitor')
        cls.store = Restaurant.objects.create(name='訪問店舗')
        cls.another = Restaurant.objects.create(name='別の訪問店舗')

    def setUp(self):
        self.client.force_login(self.user)

    def test_repeated_add_does_not_duplicate_or_change_registration_time(self):
        url = reverse('visits:update', args=[self.store.pk])
        self.assertRedirects(self.client.post(url, {'action': 'add'}), reverse('maps:personal'))
        first = Visit.objects.get(user=self.user)
        self.assertRedirects(self.client.post(url, {'action': 'add'}), reverse('maps:personal'))
        self.assertEqual(Visit.objects.count(), 1)
        self.assertEqual(Visit.objects.get().visited_at, first.visited_at)
        self.assertEqual(visit_summary(self.user)['points'], 10)
        self.assertEqual(visit_summary(self.user)['stamp_count'], 1)

    def test_visit_registration_opens_personal_map_even_with_detail_return_url(self):
        response = self.client.post(reverse('visits:update', args=[self.store.pk]), {
            'action': 'add', 'next': self.store.get_absolute_url() + '?q=訪問&budget=1000',
        })
        self.assertRedirects(response, reverse('maps:personal'))
        personal = self.client.get(response.url)
        self.assertEqual(personal.context['record_count'], 1)
        self.assertEqual(visit_summary(self.user)['points'], 10)

    def test_visit_removal_returns_to_detail_or_history_and_updates_points(self):
        for destination in [self.store.get_absolute_url() + '?q=訪問&budget=1000', reverse('visits:history')]:
            with self.subTest(destination=destination):
                Visit.objects.create(user=self.user, restaurant=self.store)
                response = self.client.post(reverse('visits:update', args=[self.store.pk]), {
                    'action': 'remove', 'next': destination,
                })
                self.assertRedirects(response, destination)
                self.assertEqual(visit_summary(self.user)['points'], 0)

    def test_distinct_stores_increase_points_and_removal_decreases_them(self):
        for store in [self.store, self.another]:
            self.client.post(reverse('visits:update', args=[store.pk]), {'action': 'add'})
        summary = visit_summary(self.user)
        self.assertEqual(summary['visit_count'], 2)
        self.assertEqual(summary['points'], 20)
        for _ in range(2):
            self.client.post(reverse('visits:update', args=[self.store.pk]), {'action': 'remove'})
        self.assertEqual(visit_summary(self.user)['points'], 10)

    def test_duplicate_database_records_are_rejected(self):
        Visit.objects.create(user=self.user, restaurant=self.store)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Visit.objects.create(user=self.user, restaurant=self.store)

    def test_posted_user_is_ignored_and_others_records_cannot_be_removed(self):
        other = Visit.objects.create(user=self.other, restaurant=self.store)
        url = reverse('visits:update', args=[self.store.pk])
        self.client.post(url, {'action': 'add', 'user': self.other.pk})
        self.assertTrue(Visit.objects.filter(user=self.user, restaurant=self.store).exists())
        self.client.post(url, {'action': 'remove', 'user': self.other.pk})
        self.assertTrue(Visit.objects.filter(pk=other.pk).exists())
        self.assertEqual(visit_summary(self.user)['points'], 0)

    def test_history_and_stamps_are_private_and_describe_self_reporting(self):
        Visit.objects.create(user=self.other, restaurant=self.another)
        for name in ['visits:history', 'visits:stamps']:
            response = self.client.get(reverse(name))
            self.assertNotContains(response, self.another.name)
            self.assertContains(response, '自己申告')
            self.assertContains(response, '交換する機能はありません')
            self.assertEqual(response.context['summary']['points'], 0)
        Visit.objects.create(user=self.user, restaurant=self.store)
        response = self.client.get(reverse('visits:stamps'))
        self.assertContains(response, self.store.name)
        self.assertEqual(response.context['summary']['stamp_count'], 1)

    @override_settings(VISIT_POINTS_PER_STORE=3, STAMP_GOAL=1)
    def test_scoring_rule_is_configurable_and_goal_progress_is_capped(self):
        Visit.objects.create(user=self.user, restaurant=self.store)
        Visit.objects.create(user=self.user, restaurant=self.another)
        summary = visit_summary(self.user)
        self.assertEqual(summary['points'], 6)
        self.assertEqual(summary['progress_percent'], 100)
        self.assertEqual(summary['goal_count'], 1)

    def test_get_invalid_action_csrf_and_external_redirect_are_rejected(self):
        url = reverse('visits:update', args=[self.store.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'action': 'invalid'}).status_code, 400)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(url, {'action': 'add'}).status_code, 403)
        self.assertFalse(Visit.objects.exists())
        self.assertRedirects(self.client.post(url, {'action': 'add', 'next': 'https://example.invalid/'}), reverse('maps:personal'))
        self.assertRedirects(self.client.post(url, {'action': 'remove', 'next': 'https://example.invalid/'}), self.store.get_absolute_url())

    def test_visits_screens_and_updates_require_login_and_unknown_store_is_404(self):
        self.assertEqual(self.client.post(reverse('visits:update', args=[99999]), {'action': 'add'}).status_code, 404)
        self.client.logout()
        for url in [reverse('visits:history'), reverse('visits:stamps')]:
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)
        url = reverse('visits:update', args=[self.store.pk])
        self.assertEqual(self.client.post(url, {'action': 'add'}).status_code, 302)
        self.assertFalse(Visit.objects.exists())


class PersonalMapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='map-owner')
        cls.other = get_user_model().objects.create_user(username='other-map-owner')
        cls.favorite = Restaurant.objects.create(name='自分のお気に入り', latitude=42, longitude=140)
        cls.visited = Restaurant.objects.create(name='自分の訪問', latitude=42.1, longitude=140.1)
        cls.unknown = Restaurant.objects.create(name='他人の記録', latitude=42.2, longitude=140.2)
        Favorite.objects.create(user=cls.user, restaurant=cls.favorite)
        Visit.objects.create(user=cls.user, restaurant=cls.favorite)
        Visit.objects.create(user=cls.user, restaurant=cls.visited)
        Favorite.objects.create(user=cls.other, restaurant=cls.unknown)
        Visit.objects.create(user=cls.other, restaurant=cls.unknown)

    def setUp(self):
        self.client.force_login(self.user)

    def test_personal_map_shows_only_my_records_and_red_takes_priority(self):
        response = self.client.get(reverse('maps:personal'))
        records = {store['id']: store for store in response.context['map_data']['stores']}
        self.assertEqual(set(records), {self.favorite.pk, self.visited.pk})
        self.assertEqual(records[self.favorite.pk]['color'], 'red')
        self.assertTrue(records[self.favorite.pk]['is_visited'])
        self.assertTrue(records[self.favorite.pk]['is_favorite'])
        self.assertEqual(records[self.visited.pk]['color'], 'green')
        self.assertNotContains(response, self.unknown.name)

    def test_personal_map_can_switch_favorites_or_visited(self):
        response = self.client.get(reverse('maps:personal'), {'mode': 'favorites'})
        records = response.context['map_data']['stores']
        self.assertEqual([store['id'] for store in records], [self.favorite.pk])
        detail = self.client.get(records[0]['detail_url'])
        self.assertEqual(detail.context['back_url'], reverse('maps:personal') + '?mode=favorites')
        response = self.client.get(reverse('maps:personal'), {'mode': 'visited'})
        self.assertEqual(len(response.context['map_data']['stores']), 2)

    def test_general_map_uses_private_states_and_unregistered_stores_are_blue(self):
        response = self.client.get(reverse('maps:search'))
        colors = {store['id']: store['color'] for store in response.context['map_data']['stores']}
        self.assertEqual(colors[self.favorite.pk], 'red')
        self.assertEqual(colors[self.visited.pk], 'green')
        self.assertEqual(colors[self.unknown.pk], 'blue')

    def test_invalid_filter_and_empty_records_have_safe_empty_state(self):
        response = self.client.get(reverse('maps:personal'), {'mode': 'someone-else'})
        self.assertEqual(response.context['map_data']['stores'], [])
        self.assertContains(response, '選び直してください')
        self.client.force_login(self.other)
        Favorite.objects.filter(user=self.other).delete()
        Visit.objects.filter(user=self.other).delete()
        response = self.client.get(reverse('maps:personal'))
        self.assertContains(response, 'まだ表示する記録がありません')

    def test_personal_map_requires_login(self):
        self.client.logout()
        url = reverse('maps:personal')
        self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)
