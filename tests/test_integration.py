from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from restaurants.models import Restaurant


class FullScreenFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='flow@example.test', email='flow@example.test', password='Full-Flow!426')
        cls.store = Restaurant.objects.create(name='結合テスト店舗', latitude=42.33, longitude=140.98)

    def test_all_sixteen_screens_render_and_five_navigation_links_work(self):
        for name in ['home', 'accounts:login', 'accounts:signup']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.client.force_login(self.user)
        urls = [
            reverse('accounts:choose'), reverse('restaurants:genres'), reverse('restaurants:list'),
            reverse('restaurants:filters'), reverse('maps:search'), self.store.get_absolute_url(),
            reverse('maps:store', args=[self.store.pk]), reverse('maps:directions', args=[self.store.pk]),
            reverse('community:review_create', args=[self.store.pk]), reverse('visits:stamps'),
            reverse('community:favorites'), reverse('accounts:profile'), reverse('maps:personal'),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-current="page"', count=1)
                for name in ['accounts:choose', 'maps:search', 'visits:stamps', 'community:favorites', 'accounts:profile']:
                    self.assertContains(response, f'href="{reverse(name)}"')
                self.assertNotContains(response, 'aria-disabled="true"')

    def test_logged_out_visitor_cannot_open_any_of_the_thirteen_private_screens(self):
        urls = [reverse('accounts:choose'), reverse('restaurants:genres'), reverse('restaurants:list'),
                reverse('restaurants:filters'), reverse('maps:search'), self.store.get_absolute_url(),
                reverse('maps:store', args=[self.store.pk]), reverse('maps:directions', args=[self.store.pk]),
                reverse('community:review_create', args=[self.store.pk]), reverse('visits:stamps'),
                reverse('community:favorites'), reverse('accounts:profile'), reverse('maps:personal')]
        for url in urls:
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)

    def test_login_search_review_favorite_visit_and_profile_integration(self):
        self.assertRedirects(self.client.post(reverse('accounts:login'), {
            'username': 'flow@example.test', 'password': 'Full-Flow!426',
        }), reverse('accounts:choose'))
        response = self.client.get(reverse('restaurants:list'), {'q': '結合'})
        self.assertEqual(response.context['result_count'], 1)
        self.client.post(reverse('community:review_create', args=[self.store.pk]), {'rating': 5, 'comment': '結合確認'})
        self.client.post(reverse('community:favorite_update', args=[self.store.pk]), {'action': 'add'})
        self.client.post(reverse('visits:update', args=[self.store.pk]), {'action': 'add'})
        response = self.client.get(self.store.get_absolute_url())
        self.assertEqual(response.context['restaurant'].avg_rating, 5)
        self.assertTrue(response.context['restaurant'].is_favorite)
        self.assertTrue(response.context['restaurant'].is_visited)
        self.assertEqual(self.client.get(reverse('accounts:profile')).context['summary']['points'], 10)
        records = self.client.get(reverse('maps:personal')).context['map_data']['stores']
        self.assertEqual(records[0]['color'], 'red')
