"""起動時の環境変数による設定切り替えを、新規プロセスで検証する。"""

import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def run_with_settings(self, overrides):
        environment = os.environ.copy()
        for name in ['DJANGO_DEBUG', 'DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS']:
            environment.pop(name, None)
        environment.update(overrides)
        # Windows の既定の出力コードページにも依存せず、日本語エラーを検証する。
        environment['PYTHONIOENCODING'] = 'utf-8'
        return subprocess.run(
            [sys.executable, '-c', (
                'from config import settings; '
                'print(settings.DEBUG); print(settings.ALLOWED_HOSTS)'
            )],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False,
        )

    def test_development_starts_without_extra_environment_variables(self):
        result = self.run_with_settings({})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['True', "['localhost', '127.0.0.1', '[::1]']"])

    def test_non_debug_mode_requires_a_secret_key(self):
        result = self.run_with_settings({'DJANGO_DEBUG': '0'})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY が必要です。', result.stderr)

    def test_environment_overrides_are_respected(self):
        result = self.run_with_settings({
            'DJANGO_DEBUG': '0',
            'DJANGO_SECRET_KEY': 'test-only-key-never-use-for-deployment',
            'DJANGO_ALLOWED_HOSTS': ' example.test, localhost, ',
        })

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['False', "['example.test', 'localhost']"])
