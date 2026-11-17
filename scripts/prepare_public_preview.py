"""PythonAnywhere上で公開用の設定・DB・静的ファイルを準備する。"""

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hostname', required=True, help='例: shimohira.pythonanywhere.com')
    args = parser.parse_args()
    hostname = args.hostname.strip().lower()
    if not re.fullmatch(r'[a-z0-9-]+\.(?:eu\.)?pythonanywhere\.com', hostname):
        parser.error('https://やパスを含めず、PythonAnywhereのホスト名を指定してください。')

    config_path = ROOT / '.public-config.json'
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            parser.error('既存の公開設定を読み取れません。ファイルを確認してください。')
        if not isinstance(config, dict) or config.get('hostname') != hostname:
            parser.error('既存の公開設定とホスト名が異なります。設定を確認してください。')
    else:
        config = {'hostname': hostname, 'secret_key': secrets.token_urlsafe(64)}
        descriptor = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            json.dump(config, output, ensure_ascii=False, indent=2)

    (ROOT / 'public-data' / 'media').mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(DJANGO_SETTINGS_MODULE='config.settings_public',
                       DJANGO_PUBLIC_CONFIG=str(config_path), PYTHONIOENCODING='utf-8')
    for command in [('migrate', '--noinput'), ('seed_restaurants',), ('collectstatic', '--noinput'),
                    ('check', '--deploy')]:
        subprocess.run([sys.executable, str(ROOT / 'manage.py'), *command],
                       cwd=ROOT, env=environment, check=True)

    wsgi = (
        'import sys\n'
        f'project_path = {str(ROOT)!r}\n'
        'if project_path not in sys.path:\n'
        '    sys.path.insert(0, project_path)\n'
        'from config.wsgi_public import application\n'
    )
    (ROOT / '.pythonanywhere-wsgi.py').write_text(wsgi, encoding='utf-8')
    print('\n公開データの準備が完了しました。Webタブで次を設定してReloadしてください。')
    print(f'公開先: https://{hostname}/')
    print(f'Virtualenv: {ROOT / ".venv"}')
    print(f'WSGI設定に貼り付ける内容: {ROOT / ".pythonanywhere-wsgi.py"}')
    print(f'Static files: /static/ -> {ROOT / "staticfiles"}')
    print(f'Static files: /media/ -> {ROOT / "public-data" / "media"}')
    print('秘密鍵と公開用DBは再実行しても上書きしません。')


if __name__ == '__main__':
    main()

