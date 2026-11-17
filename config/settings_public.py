"""PythonAnywhere向けの公開設定。秘密鍵はGit対象外のJSONから読む。"""

import json
import os
from pathlib import Path
import re

from django.core.exceptions import ImproperlyConfigured


_config_path = Path(os.environ.get(
    'DJANGO_PUBLIC_CONFIG', Path(__file__).resolve().parent.parent / '.public-config.json',
))
try:
    _config = json.loads(_config_path.read_text(encoding='utf-8'))
except (OSError, ValueError) as error:
    raise ImproperlyConfigured('公開設定がありません。scripts/prepare_public_preview.py を実行してください。') from error
if not isinstance(_config, dict):
    raise ImproperlyConfigured('公開設定の形式が正しくありません。')

_hostname = _config.get('hostname', '')
_secret = _config.get('secret_key', '')
if not isinstance(_hostname, str) or not re.fullmatch(r'[a-z0-9-]+\.(?:eu\.)?pythonanywhere\.com', _hostname):
    raise ImproperlyConfigured('公開先にはPythonAnywhereの正確なホスト名を指定してください。')
if not isinstance(_secret, str) or len(_secret) < 50:
    raise ImproperlyConfigured('公開用の秘密鍵が正しく設定されていません。')

# ベース設定の初期化にも、公開用の同じ秘密鍵とDEBUG設定を使う。
os.environ['DJANGO_SECRET_KEY'] = _secret
os.environ['DJANGO_DEBUG'] = '0'
from .settings import *  # noqa: E402,F403

DEBUG = False
SECRET_KEY = _secret
ALLOWED_HOSTS = [_hostname]
CSRF_TRUSTED_ORIGINS = [f'https://{_hostname}']

# 開発用SQLiteや画像を上書きしない。PythonAnywhereのホーム内に保持する。
PUBLIC_DATA_ROOT = BASE_DIR / 'public-data'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': PUBLIC_DATA_ROOT / 'db.sqlite3',
    'OPTIONS': {'timeout': 20},
}}
MEDIA_ROOT = PUBLIC_DATA_ROOT / 'media'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

