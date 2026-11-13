"""登録・認証・アクセス制御・共通ナビゲーションの振る舞いを検証する。"""

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = 'Harbor-Map!42-Walk'


class SignUpTests(TestCase):
    def signup_data(self, **overrides):
        return {
            'first_name': 'むろらん太郎',
            'email': 'new@example.test',
            'password1': PASSWORD,
            'password2': PASSWORD,
            **overrides,
        }

    def test_signup_page_shows_named_fields_and_password_confirmation(self):
        response = self.client.get(reverse('accounts:signup'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')
        for label in ['ユーザー名', 'メールアドレス', 'パスワード', '確認用']:
            self.assertContains(response, label)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_signup_hashes_password_and_logs_in_without_granting_admin_rights(self):
        response = self.client.post(reverse('accounts:signup'), self.signup_data(email='NEW@Example.test'))

        self.assertRedirects(response, reverse('accounts:choose'))
        user = User.objects.get(email='new@example.test')
        self.assertEqual(user.username, 'new@example.test')
        self.assertEqual(user.get_short_name(), 'むろらん太郎')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))

    def test_duplicate_email_is_rejected_ignoring_case(self):
        self.client.post(reverse('accounts:signup'), self.signup_data())
        self.client.logout()
        response = self.client.post(reverse('accounts:signup'), self.signup_data(email='NEW@EXAMPLE.TEST'))

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'このメールアドレスはすでに登録されています。')
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_existing_standard_user_email_cannot_be_registered_again(self):
        User.objects.create_user(username='legacy-admin', email='new@example.test')
        response = self.client.post(reverse('accounts:signup'), self.signup_data())

        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_inputs_do_not_create_accounts(self):
        cases = [
            ({'first_name': '   '}, 'first_name'),
            ({'first_name': '名' * 151}, 'first_name'),
            ({'email': 'invalid-address'}, 'email'),
            ({'email': 'x' * 140 + '@example.test'}, 'email'),
            ({'password2': 'Different-password!'}, 'password2'),
            ({'password1': '123', 'password2': '123'}, 'password2'),
            ({'password1': 'new@example.test', 'password2': 'new@example.test'}, 'password2'),
        ]
        for overrides, field in cases:
            with self.subTest(field=field, overrides=overrides):
                response = self.client.post(reverse('accounts:signup'), self.signup_data(**overrides))
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.assertEqual(User.objects.count(), 0)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_signup_does_not_echo_passwords_on_error(self):
        response = self.client.post(reverse('accounts:signup'), self.signup_data(password2='Mismatch!'))

        self.assertNotContains(response, f'value="{PASSWORD}"')
        self.assertNotContains(response, 'value="Mismatch!"')
        self.assertContains(response, 'role="alert"')

    def test_display_name_is_escaped(self):
        response = self.client.post(
            reverse('accounts:signup'),
            self.signup_data(first_name='<script>alert(1)</script>'),
            follow=True,
        )

        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_signup_ignores_next_and_always_opens_selection(self):
        response = self.client.post(
            reverse('accounts:signup') + '?next=https://example.invalid/',
            self.signup_data(),
        )

        self.assertRedirects(response, reverse('accounts:choose'))


class AccountFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='member@example.test', email='member@example.test',
            first_name='室蘭メンバー', password=PASSWORD,
        )

    def login_data(self, **overrides):
        return {'username': 'member@example.test', 'password': PASSWORD, **overrides}

    def test_login_page_uses_email_and_has_no_welcome_back_text(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'type="email"')
        self.assertContains(response, 'メールアドレス')
        self.assertNotContains(response, 'おかえりなさい')
        self.assertContains(response, f'href="{reverse("accounts:signup")}"')

    def test_login_accepts_normalized_email_and_goes_to_selection(self):
        response = self.client.post(
            reverse('accounts:login'), self.login_data(username='MEMBER@Example.test'),
        )

        self.assertRedirects(response, reverse('accounts:choose'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_wrong_password_and_unknown_email_show_same_error(self):
        for data in [self.login_data(password='Wrong-password!'), self.login_data(username='missing@example.test')]:
            with self.subTest(data=data):
                response = self.client.post(reverse('accounts:login'), data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'メールアドレスまたはパスワードが正しくありません。')
                self.assertNotContains(response, 'value="Wrong-password!"')
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(reverse('accounts:login'), self.login_data())

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_ignores_external_and_internal_next_destinations(self):
        for destination in ['https://example.invalid/', '//example.invalid/', '/admin/', reverse('maps:search')]:
            with self.subTest(destination=destination):
                response = self.client.post(
                    reverse('accounts:login') + '?next=' + destination,
                    self.login_data(next=destination),
                )
                self.assertRedirects(response, reverse('accounts:choose'))
                self.client.logout()

    def test_logged_in_user_is_redirected_away_from_login_and_signup(self):
        self.client.force_login(self.user)
        for name in ['accounts:login', 'accounts:signup']:
            with self.subTest(name=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse('accounts:choose'))

    def test_protected_screens_redirect_anonymous_visitors_to_login(self):
        for name in ['accounts:choose', 'restaurants:genres', 'maps:search']:
            with self.subTest(name=name):
                url = reverse(name)
                self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)

    def test_selection_links_to_both_placeholder_screens(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:choose'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'お店の探し方を選ぶ')
        for name in ['restaurants:genres', 'maps:search']:
            self.assertContains(response, f'href="{reverse(name)}"')
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_placeholders_are_available_only_after_login_and_can_return_home(self):
        self.client.force_login(self.user)
        for name, title in [('restaurants:genres', 'ジャンル選択'), ('maps:search', 'マップ検索')]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertContains(response, '現在準備中です。')
                self.assertContains(response, f'href="{reverse("accounts:choose")}"')
                self.assertIn('no-store', response.headers['Cache-Control'])

    def test_shared_navigation_shows_current_location_and_unavailable_items(self):
        self.client.force_login(self.user)
        for name in ['accounts:choose', 'restaurants:genres', 'maps:search']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertTemplateUsed(response, 'includes/header.html')
                self.assertTemplateUsed(response, 'includes/bottom_nav.html')
                self.assertContains(response, '室蘭メンバー さん')
                self.assertContains(response, f'action="{reverse("accounts:logout")}"')
                self.assertContains(response, 'aria-disabled="true"', count=3)
                self.assertContains(response, 'aria-current="page"', count=1)
                for title in ['ホーム', '地図', 'スタンプ', 'お気に入り', 'マイページ']:
                    self.assertContains(response, title)

    def test_authenticated_top_has_continue_link(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'お店を探す')
        self.assertContains(response, f'href="{reverse("accounts:choose")}"')
        self.assertNotContains(response, f'href="{reverse("accounts:signup")}"')

    def test_logout_requires_post_and_get_does_not_change_session(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:logout'))

        self.assertEqual(response.status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_logout_clears_session_and_protected_screens_become_unavailable(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:logout'), {'next': 'https://example.invalid/'})

        self.assertRedirects(response, reverse('home'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        for name in ['accounts:choose', 'restaurants:genres', 'maps:search']:
            url = reverse(name)
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)

    def test_post_requests_without_csrf_tokens_are_rejected(self):
        client = Client(enforce_csrf_checks=True)
        for name in ['accounts:login', 'accounts:signup']:
            with self.subTest(name=name):
                self.assertEqual(client.post(reverse(name), self.login_data()).status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('accounts:logout')).status_code, 403)
        self.assertIn(SESSION_KEY, client.session)

    def test_login_and_logout_work_with_real_csrf_tokens(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('accounts:login'))
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('accounts:login'), {
            **self.login_data(), 'csrfmiddlewaretoken': token,
        })
        self.assertRedirects(response, reverse('accounts:choose'))
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('accounts:logout'), {'csrfmiddlewaretoken': token})
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn(SESSION_KEY, client.session)
