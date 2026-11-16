from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from restaurants.models import Restaurant
from .models import Favorite, Report, Review


class CommunityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='author', first_name='投稿者')
        cls.other = get_user_model().objects.create_user(username='other')
        cls.store = Restaurant.objects.create(name='口コミテスト店')
        cls.another = Restaurant.objects.create(name='別の店舗')

    def setUp(self):
        self.client.force_login(self.user)

    def create_review(self, user=None, rating=4, comment='また食べたいです。'):
        return Review.objects.create(user=user or self.user, restaurant=self.store, rating=rating, comment=comment)

    def test_create_review_saves_only_current_user_and_returns_to_detail(self):
        response = self.client.post(reverse('community:review_create', args=[self.store.pk]), {
            'rating': 5, 'comment': 'とてもおいしかったです。', 'user': self.other.pk, 'restaurant': self.another.pk,
        })
        self.assertRedirects(response, self.store.get_absolute_url())
        review = Review.objects.get()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.restaurant, self.store)
        self.assertEqual(review.rating, 5)
        self.assertIsNone(review.edited_at)

    def test_invalid_ratings_long_or_empty_comments_are_rejected(self):
        for data in [{'rating': 0, 'comment': 'テスト'}, {'rating': 6, 'comment': 'テスト'},
                     {'rating': 4, 'comment': '長' * 201}, {'rating': 4, 'comment': '   '}]:
            with self.subTest(data=data):
                response = self.client.post(reverse('community:review_create', args=[self.store.pk]), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertEqual(Review.objects.count(), 0)

    def test_two_hundred_characters_are_accepted(self):
        response = self.client.post(reverse('community:review_create', args=[self.store.pk]), {'rating': 1, 'comment': 'あ' * 200})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Review.objects.get().comment), 200)

    def test_owner_can_edit_and_timestamp_is_shown(self):
        review = self.create_review()
        response = self.client.post(reverse('community:review_edit', args=[review.pk]), {'rating': 2, 'comment': '追記しました。'})
        self.assertRedirects(response, self.store.get_absolute_url())
        review.refresh_from_db()
        self.assertEqual(review.rating, 2)
        self.assertIsNotNone(review.edited_at)
        response = self.client.get(self.store.get_absolute_url())
        self.assertContains(response, '編集：')
        self.assertContains(response, '追記しました。')

    def test_other_users_cannot_edit_or_delete_a_review(self):
        review = self.create_review(self.other)
        for name in ['community:review_edit', 'community:review_delete']:
            for method in [self.client.get, self.client.post]:
                with self.subTest(name=name, method=method):
                    self.assertEqual(method(reverse(name, args=[review.pk]), {'rating': 1, 'comment': '書き換え'}).status_code, 404)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)

    def test_delete_requires_confirmation_post(self):
        review = self.create_review()
        url = reverse('community:review_delete', args=[review.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.assertRedirects(self.client.post(url), self.store.get_absolute_url())
        self.assertFalse(Review.objects.exists())

    def test_moderator_with_delete_permission_can_remove_review(self):
        moderator = get_user_model().objects.create_user(username='moderator', is_staff=True)
        moderator.user_permissions.add(Permission.objects.get(codename='delete_review'))
        review = self.create_review(self.other)
        self.client.force_login(moderator)
        self.assertEqual(self.client.post(reverse('community:review_delete', args=[review.pk])).status_code, 302)
        self.assertFalse(Review.objects.exists())

    def test_staff_status_and_delete_permission_are_both_required_to_moderate(self):
        review = self.create_review(self.other)
        for is_staff, grant_permission in [(False, True), (True, False)]:
            actor = get_user_model().objects.create_user(username=f'role-{is_staff}', is_staff=is_staff)
            if grant_permission:
                actor.user_permissions.add(Permission.objects.get(codename='delete_review'))
            self.client.force_login(actor)
            self.assertEqual(self.client.post(reverse('community:review_delete', args=[review.pk])).status_code, 404)
            self.assertTrue(Review.objects.filter(pk=review.pk).exists())

    def test_average_reflects_edits_and_deletes_without_fake_default(self):
        first = self.create_review(rating=5)
        second = self.create_review(self.other, rating=3)
        self.assertEqual(self.client.get(self.store.get_absolute_url()).context['restaurant'].avg_rating, 4)
        self.client.post(reverse('community:review_edit', args=[first.pk]), {'rating': 1, 'comment': '変更しました'})
        self.assertEqual(self.client.get(self.store.get_absolute_url()).context['restaurant'].avg_rating, 2)
        self.client.post(reverse('community:review_delete', args=[first.pk]))
        self.assertEqual(self.client.get(self.store.get_absolute_url()).context['restaurant'].avg_rating, 3)
        second.delete()
        response = self.client.get(self.store.get_absolute_url())
        self.assertIsNone(response.context['restaurant'].avg_rating)
        self.assertContains(response, 'まだ口コミがありません')

    def test_review_text_is_escaped(self):
        self.create_review(comment='<script>alert(1)</script>')
        response = self.client.get(self.store.get_absolute_url())
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_public_author_name_does_not_expose_email_when_display_name_is_empty(self):
        self.other.username = self.other.email = 'private-author@example.test'
        self.other.first_name = ''
        self.other.save()
        self.create_review(self.other)
        response = self.client.get(self.store.get_absolute_url())
        self.assertNotContains(response, self.other.email)
        self.assertContains(response, '名前未設定のユーザー')

    def test_review_database_constraints_reject_direct_invalid_writes(self):
        for rating, comment in [(9, 'テスト'), (2, '長' * 201), (3, ' ' * 5)]:
            with self.subTest(rating=rating):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.create_review(rating=rating, comment=comment)

    def test_favorite_add_remove_are_idempotent_and_user_scoped(self):
        other = Favorite.objects.create(user=self.other, restaurant=self.store)
        url = reverse('community:favorite_update', args=[self.store.pk])
        for _ in range(2):
            self.assertRedirects(self.client.post(url, {'action': 'add', 'user': self.other.pk}), self.store.get_absolute_url())
        self.assertEqual(Favorite.objects.filter(user=self.user).count(), 1)
        for _ in range(2):
            self.client.post(url, {'action': 'remove'})
        self.assertFalse(Favorite.objects.filter(user=self.user).exists())
        self.assertTrue(Favorite.objects.filter(pk=other.pk).exists())

    def test_favorite_database_constraint_prevents_duplicates(self):
        Favorite.objects.create(user=self.user, restaurant=self.store)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=self.user, restaurant=self.store)

    def test_favorites_page_does_not_reveal_other_users_records(self):
        Favorite.objects.create(user=self.other, restaurant=self.another)
        response = self.client.get(reverse('community:favorites'))
        self.assertEqual(response.context['result_count'], 0)
        self.assertContains(response, 'お気に入りはまだありません。')
        self.assertNotContains(response, self.another.name)
        Favorite.objects.create(user=self.user, restaurant=self.store)
        response = self.client.get(reverse('community:favorites'))
        self.assertContains(response, self.store.name)
        self.assertContains(response, 'お気に入りを解除')
        self.assertEqual(response.context['result_count'], 1)

    def test_list_card_favorite_state_is_current_users_state(self):
        Favorite.objects.create(user=self.other, restaurant=self.store)
        response = self.client.get(reverse('restaurants:list'))
        self.assertFalse(next(store for store in response.context['restaurants'] if store.pk == self.store.pk).is_favorite)
        Favorite.objects.create(user=self.user, restaurant=self.store)
        response = self.client.get(reverse('restaurants:list'))
        self.assertTrue(next(store for store in response.context['restaurants'] if store.pk == self.store.pk).is_favorite)

    def test_favorite_requires_valid_post_and_does_not_redirect_externally(self):
        url = reverse('community:favorite_update', args=[self.store.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'action': 'invalid'}).status_code, 400)
        self.assertFalse(Favorite.objects.exists())
        for next_url in ['https://example.invalid/', '//example.invalid/', '/\\example.invalid/']:
            self.assertRedirects(self.client.post(url, {'action': 'add', 'next': next_url}), self.store.get_absolute_url())
        self.assertRedirects(self.client.post(url, {'action': 'remove', 'next': reverse('community:favorites')}), reverse('community:favorites'))

    def test_csrf_is_required_for_reviews_favorites_and_deletion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        review = self.create_review()
        for url, data in [
            (reverse('community:review_create', args=[self.store.pk]), {'rating': 4, 'comment': 'テスト'}),
            (reverse('community:favorite_update', args=[self.store.pk]), {'action': 'add'}),
            (reverse('community:review_delete', args=[review.pk]), {}),
        ]:
            self.assertEqual(client.post(url, data).status_code, 403)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.assertFalse(Favorite.objects.exists())

    def test_reports_are_pending_and_do_not_modify_store_or_review(self):
        review = self.create_review(self.other)
        for name, pk in [('community:report_store', self.store.pk), ('community:report_review', review.pk)]:
            response = self.client.post(reverse(name, args=[pk]), {'reason': '情報の確認をお願いします。', 'status': 'resolved', 'name': '無断の変更'})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(Report.objects.filter(status='new').count(), 2)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, '口コミテスト店')
        review.delete()
        report = Report.objects.get(kind='review')
        self.assertIsNone(report.review_id)
        self.assertEqual(report.restaurant, self.store)

    def test_community_views_require_login(self):
        review = self.create_review()
        self.client.logout()
        for url in [reverse('community:favorites'), reverse('community:review_create', args=[self.store.pk]),
                    reverse('community:review_edit', args=[review.pk]), reverse('community:review_delete', args=[review.pk]),
                    reverse('community:report_store', args=[self.store.pk])]:
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)

    def test_missing_targets_return_404(self):
        self.assertEqual(self.client.get(reverse('community:review_create', args=[99999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('community:review_edit', args=[99999])).status_code, 404)

    def test_admin_can_manage_review_and_pending_report(self):
        admin = get_user_model().objects.create_superuser(username='site-admin', email='admin@example.test', password='Admin-Only!426')
        review = self.create_review(self.other)
        report = Report.objects.create(user=self.user, restaurant=self.store, review=review, kind='review', reason='確認依頼')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('admin:community_review_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:community_report_change', args=[report.pk])).status_code, 200)
        response = self.client.post(reverse('admin:community_review_delete', args=[review.pk]), {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())
        report.refresh_from_db()
        self.assertIsNone(report.review_id)
        self.assertEqual(report.status, 'new')

    def test_invalid_report_is_not_saved(self):
        for reason in ['', '長' * 501]:
            response = self.client.post(reverse('community:report_store', args=[self.store.pk]), {'reason': reason})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(Report.objects.exists())

    def test_review_can_return_to_filtered_detail_and_rejects_external_return(self):
        next_url = self.store.get_absolute_url() + '?q=口コミ&source=map'
        response = self.client.post(reverse('community:review_create', args=[self.store.pk]), {'rating': 3, 'comment': 'テスト', 'next': next_url})
        self.assertRedirects(response, next_url)
        response = self.client.get(reverse('community:review_create', args=[self.store.pk]), {'next': 'https://example.invalid/'})
        self.assertEqual(response.context['return_url'], self.store.get_absolute_url())

    def test_delete_confirmation_preserves_safe_return_location(self):
        review = self.create_review()
        url = reverse('community:review_delete', args=[review.pk])
        next_url = self.store.get_absolute_url() + '?q=口コミ&source=map'
        response = self.client.get(url, {'next': next_url})
        self.assertEqual(response.context['return_url'], next_url)
        self.assertRedirects(self.client.post(url, {'next': next_url}), next_url)
