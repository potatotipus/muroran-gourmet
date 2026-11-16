from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from community.models import Favorite, Review
from restaurants.models import Restaurant
from visits.models import Visit


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='me@example.test', email='me@example.test', first_name='自分の表示名', password='Harbor-Profile!426')
        cls.other = get_user_model().objects.create_user(username='other@example.test', email='other@example.test', first_name='別の人')
        cls.store = Restaurant.objects.create(name='マイページ店舗')

    def setUp(self):
        self.client.force_login(self.user)

    def test_profile_shows_only_own_details_counts_and_review_history(self):
        Favorite.objects.create(user=self.user, restaurant=self.store)
        Visit.objects.create(user=self.user, restaurant=self.store)
        Review.objects.create(user=self.user, restaurant=self.store, rating=4, comment='自分の口コミ')
        Review.objects.create(user=self.other, restaurant=self.store, rating=3, comment='他人の非表示履歴')
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, self.user.email)
        self.assertContains(response, '自分の口コミ')
        self.assertNotContains(response, '他人の非表示履歴')
        self.assertNotContains(response, self.other.email)
        self.assertEqual(response.context['favorite_count'], 1)
        self.assertEqual(response.context['summary']['points'], 10)

    def test_display_name_can_change_without_granting_privileges(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': '変更した表示名', 'email': self.user.email, 'is_staff': True,
            'is_superuser': True, 'user': self.other.pk,
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.user.first_name, '変更した表示名')
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.other.first_name, '別の人')

    def test_email_change_requires_current_password(self):
        for password in ['', 'incorrect']:
            response = self.client.post(reverse('accounts:profile_edit'), {
                'first_name': '自分の表示名', 'email': 'new@example.test', 'current_password': password,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn('current_password', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'me@example.test')

    def test_email_change_updates_login_id_and_keeps_session(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': '自分の表示名', 'email': 'NEW@Example.test', 'current_password': 'Harbor-Profile!426',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'new@example.test')
        self.assertTrue(self.user.check_password('Harbor-Profile!426'))
        self.client.logout()
        response = self.client.post(reverse('accounts:login'), {'username': 'me@example.test', 'password': 'Harbor-Profile!426'})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('accounts:login'), {'username': 'new@example.test', 'password': 'Harbor-Profile!426'})
        self.assertRedirects(response, reverse('accounts:choose'))

    def test_duplicate_email_is_rejected_ignoring_case(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': '自分の表示名', 'email': 'OTHER@EXAMPLE.TEST', 'current_password': 'Harbor-Profile!426',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'me@example.test')

    def test_display_name_only_change_preserves_legacy_admin_username(self):
        self.other.username = 'legacy-admin'
        self.other.save()
        self.client.force_login(self.other)
        response = self.client.post(reverse('accounts:profile_edit'), {'first_name': '新表示名', 'email': self.other.email})
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertEqual(self.other.username, 'legacy-admin')

    def test_profile_pages_require_login_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('accounts:profile_edit'), {'first_name': '勝手な変更'}).status_code, 403)
        self.client.logout()
        for name in ['accounts:profile', 'accounts:profile_edit']:
            url = reverse(name)
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)
