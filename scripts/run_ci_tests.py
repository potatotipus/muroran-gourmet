"""OS間でテスト出力を統一し、失敗時はChecksにも詳細を残す。終了コードは保持する。"""

import os
from pathlib import Path
import subprocess
import sys

environment = os.environ.copy()
environment['PYTHONIOENCODING'] = 'utf-8'
result = subprocess.run(
    [sys.executable, 'manage.py', 'test', '--verbosity', '2'],
    cwd=Path(__file__).resolve().parents[1], env=environment,
    capture_output=True, text=True, encoding='utf-8', errors='replace',
)
output = result.stdout + result.stderr
print(output, end='')
if result.returncode and os.environ.get('GITHUB_ACTIONS') == 'true':
    # GitHub workflow command の改行・%をエスケープして注釈にする。
    details = output[-12000:].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error title=Django test failure::{details}')
sys.exit(result.returncode)
