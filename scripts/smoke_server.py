"""browser_smoke.py 専用。一時 DB だけを使い、既存DBとファイルに触れない。"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command, execute_from_command_line


def main():
    directory = os.environ.get('MURORAN_SMOKE_DIRECTORY')
    if not directory:
        raise SystemExit('scripts/browser_smoke.py から実行してください。')
    settings.DATABASES['default']['NAME'] = Path(directory) / 'smoke.sqlite3'
    settings.MEDIA_ROOT = Path(directory) / 'media'
    settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
    # 既存リリース相当の認証・店舗を作り、新しいマイグレーションで維持されるか検証。
    execute_from_command_line(['manage.py', 'migrate', 'restaurants', '0002_search_categories', '--noinput'])
    call_command('migrate', 'auth', interactive=False)
    User = get_user_model()
    user = User.objects.create_user(username='browser@example.test', email='browser@example.test',
                                    first_name='画面確認', password='Smoke-Only!426')
    call_command('seed_restaurants')
    from restaurants.models import Restaurant
    snapshot = list(Restaurant.objects.values_list('pk', 'name', 'latitude', 'longitude'))
    call_command('migrate', interactive=False)
    user.refresh_from_db()
    assert user.check_password('Smoke-Only!426')
    assert snapshot == list(Restaurant.objects.values_list('pk', 'name', 'latitude', 'longitude'))
    call_command('seed_restaurants')
    assert Restaurant.objects.count() == 10
    from community.models import Favorite, Review
    from visits.models import Visit
    other = User.objects.create_user(username='other@example.test', email='other@example.test')
    other_store = Restaurant.objects.get(demo_key='muroran-sample-03')
    Favorite.objects.create(user=other, restaurant=other_store)
    Visit.objects.create(user=other, restaurant=other_store)
    Review.objects.create(user=other, restaurant=other_store, rating=3, comment='他の利用者だけの履歴')
    print('MIGRATION_PRESERVATION_OK', flush=True)
    port = os.environ['MURORAN_SMOKE_PORT']
    execute_from_command_line(['manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'])


if __name__ == '__main__':
    main()
