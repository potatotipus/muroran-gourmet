"""一時コピーの公開設定で、初期準備・HTTPS認証・記録の保持を確認する。"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent
HOST = 'preview-test.pythonanywhere.com'


class PublicPreviewTests(SimpleTestCase):
    def run_python(self, project, *arguments, overrides=None):
        environment = os.environ.copy()
        for name in ['DJANGO_SETTINGS_MODULE', 'DJANGO_PUBLIC_CONFIG', 'DJANGO_DEBUG', 'DJANGO_SECRET_KEY']:
            environment.pop(name, None)
        environment.update(PYTHONIOENCODING='utf-8', **(overrides or {}))
        return subprocess.run([sys.executable, *arguments], cwd=project, env=environment,
                              capture_output=True, text=True, encoding='utf-8', check=False)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_public_setup_https_features_and_repeated_setup_preserve_data(self):
        with tempfile.TemporaryDirectory(prefix='muroran-public-test-') as temporary:
            project = Path(temporary) / 'muroran-gourmet'
            shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns(
                '.git', '.venv', '__pycache__', '*.pyc', 'db.sqlite3*', 'media', 'staticfiles',
                'public-data', '.public-config.json', '.pythonanywhere-wsgi.py', 'browser-artifacts',
            ))
            development_db = project / 'db.sqlite3'
            development_db.write_bytes(b'preserve-the-existing-development-database')
            prepare = ['scripts/prepare_public_preview.py', '--hostname', HOST]
            self.assert_success(self.run_python(project, *prepare))
            secret_config = (project / '.public-config.json').read_bytes()
            self.assertTrue((project / 'staticfiles/maps/vendor/leaflet/leaflet.js').is_file())
            self.assertTrue((project / 'staticfiles/restaurants/images/placeholder.svg').is_file())
            self.assertNotIn(json.loads(secret_config)['secret_key'], (project / '.pythonanywhere-wsgi.py').read_text())

            integration = textwrap.dedent('''
                import django
                django.setup()
                from django.conf import settings
                from django.test import Client
                from django.contrib.auth import get_user_model
                from restaurants.models import Restaurant
                from community.models import Favorite, Review
                from visits.models import Visit
                from config.wsgi_public import application
                assert callable(application)
                assert settings.DEBUG is False
                assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
                host = settings.ALLOWED_HOSTS[0]
                client = Client(enforce_csrf_checks=True)
                assert client.get('/', HTTP_HOST=host).status_code == 301
                assert client.get('/', HTTP_HOST='other.invalid', secure=True).status_code == 400
                signup = client.get('/accounts/signup/', HTTP_HOST=host, secure=True)
                assert signup.status_code == 200
                assert signup.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
                def post(url, values, origin=None):
                    return client.post(url, {**values, 'csrfmiddlewaretoken': client.cookies['csrftoken'].value},
                                       HTTP_HOST=host, secure=True, HTTP_ORIGIN=origin or 'https://' + host)
                response = post('/accounts/signup/', {'first_name': '公開テスト', 'email': 'public@example.test',
                                                       'password1': 'Public-Test!473', 'password2': 'Public-Test!473'})
                assert response.status_code == 302 and response.url == '/accounts/choose/'
                assert client.cookies['sessionid']['secure']
                store = Restaurant.objects.order_by('pk').first()
                from django.urls import reverse
                favorite_url = reverse('community:favorite_update', args=[store.pk])
                assert post(favorite_url, {'action': 'add'}, 'https://other.invalid').status_code == 403
                assert Favorite.objects.count() == 0
                assert post(favorite_url, {'action': 'add'}).status_code == 302
                assert post(reverse('community:review_create', args=[store.pk]), {'rating': 5, 'comment': 'HTTPSで投稿'}).status_code == 302
                response = post(reverse('visits:update', args=[store.pk]), {'action': 'add'})
                assert response.status_code == 302 and response.url == reverse('maps:personal')
                assert client.get(response.url, HTTP_HOST=host, secure=True).status_code == 200
                assert Restaurant.objects.count() == 10
                assert Favorite.objects.count() == Review.objects.count() == Visit.objects.count() == 1
                assert get_user_model().objects.filter(email='public@example.test').exists()
            ''')
            overrides = {'DJANGO_SETTINGS_MODULE': 'config.settings_public'}
            self.assert_success(self.run_python(project, '-c', integration, overrides=overrides))
            self.assert_success(self.run_python(project, *prepare))
            self.assertEqual((project / '.public-config.json').read_bytes(), secret_config)
            self.assertEqual(development_db.read_bytes(), b'preserve-the-existing-development-database')
            self.assert_success(self.run_python(project, '-c', textwrap.dedent('''
                import django
                django.setup()
                from visits.models import Visit
                from restaurants.models import Restaurant
                assert Visit.objects.count() == 1
                assert Restaurant.objects.count() == 10
            '''), overrides=overrides))

    def test_public_settings_fail_closed_without_valid_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'public.json'
            for value in [None, [], {'hostname': '*', 'secret_key': 'x' * 64},
                          {'hostname': HOST, 'secret_key': 'short'}]:
                with self.subTest(value=value):
                    if value is not None:
                        config.write_text(json.dumps(value), encoding='utf-8')
                    result = self.run_python(ROOT, '-c', 'from config import settings_public',
                                             overrides={'DJANGO_PUBLIC_CONFIG': str(config)})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('ImproperlyConfigured', result.stderr)

    def test_prepare_rejects_non_pythonanywhere_hosts_before_writing_files(self):
        result = self.run_python(ROOT, 'scripts/prepare_public_preview.py', '--hostname', '*.example.com')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PythonAnywhere', result.stderr)
