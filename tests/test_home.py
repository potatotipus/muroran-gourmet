"""共通画面と、初期段階で公開する URL の基本テスト。"""

from html.parser import HTMLParser

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class ButtonParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        if tag == 'button':
            self.buttons.append(dict(attrs))


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

    def test_account_actions_are_disabled_and_explained(self):
        response = self.client.get(reverse('home'))
        parser = ButtonParser()
        parser.feed(response.content.decode())

        self.assertEqual(len(parser.buttons), 2)
        for button in parser.buttons:
            self.assertIn('disabled', button)
            self.assertEqual(button['type'], 'button')
        self.assertContains(response, 'ログイン・新規登録はまだご利用いただけません。')
        self.assertNotContains(response, '<form')

    def test_future_features_are_not_exposed(self):
        for url in ['/accounts/login/', '/accounts/signup/', '/restaurants/', '/maps/', '/community/', '/visits/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)


class AdminTests(TestCase):
    def test_standard_admin_is_not_publicly_accessible(self):
        response = self.client.get(reverse('admin:index'))

        self.assertRedirects(response, '/admin/login/?next=/admin/', fetch_redirect_response=False)
