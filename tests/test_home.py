"""共通画面と、初期段階で公開する URL の基本テスト。"""

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class HomeTests(SimpleTestCase):
    def test_home_renders_shared_templates_and_japanese_copy(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        for template in ['home.html', 'base.html', 'includes/header.html', 'includes/footer.html']:
            self.assertTemplateUsed(response, template)
        self.assertContains(response, 'むろらんグルメマップ')
        self.assertContains(response, '食べて、歩いて、')
        self.assertContains(response, 'もっと室蘭が好きになる。')
        self.assertContains(response, '<html lang="ja">')

    def test_mobile_viewport_and_local_stylesheet_are_available(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'name="viewport" content="width=device-width, initial-scale=1"')
        self.assertContains(response, 'href="/static/css/site.css"')
        self.assertIsNotNone(finders.find('css/site.css'))

    def test_account_actions_link_to_login_and_signup(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, f'href="{reverse("accounts:login")}"')
        self.assertContains(response, f'href="{reverse("accounts:signup")}"')
        self.assertNotContains(response, 'disabled')
        self.assertNotContains(response, 'メインナビゲーション')
        self.assertNotContains(response, 'ゲスト')
        self.assertNotContains(response, '<form')

    def test_future_features_are_not_exposed(self):
        for url in ['/restaurants/', '/maps/', '/community/', '/visits/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)


class AdminTests(TestCase):
    def test_standard_admin_is_not_publicly_accessible(self):
        response = self.client.get(reverse('admin:index'))

        self.assertRedirects(response, '/admin/login/?next=/admin/', fetch_redirect_response=False)
