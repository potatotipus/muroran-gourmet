# スマートフォンから使う公開URL（PythonAnywhere）

GitHub PagesはHTML等の静的配信向けです。ログイン・口コミ・訪問記録も使うこのDjangoアプリは、
PythonAnywhereのWebアプリとして公開します。SQLiteはPythonAnywhereのホーム内に保存します。
無料アカウントの制限や更新期限は、利用中のダッシュボードで確認してください。

以下はユーザー名 `Shimohira` の設定例です。設定完了後のURLは `https://shimohira.pythonanywhere.com/` です。
URLが表示されるだけではアプリの公開完了ではなく、最後の動作確認まで行ってください。

## 1. ZIPをアップロード

非公開のGitHubリポジトリのため、チャットで渡す `muroran-gourmet-preview.zip` を利用できます。
PythonAnywhereの **Files** タブでホーム `/home/Shimohira` にZIPをアップロードします。
ZIPはソースコードのみで、DB・秘密鍵・仮想環境は含みません。

GitHub認証をPythonAnywhere側で設定済みの場合は、ZIPの代わりにリポジトリを取得しても構いません。

## 2. Bash consoleで準備

**Consoles → Bash** を開き、次を実行します。Python 3.12を使用します。

```bash
cd ~
unzip -n muroran-gourmet-preview.zip
cd muroran-gourmet
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/prepare_public_preview.py --hostname shimohira.pythonanywhere.com
```

秘密鍵を自動作成し、公開用DBのマイグレーション・架空の10店舗の投入・静的ファイル収集を行います。
再実行しても既存の秘密鍵・店舗データを上書きしません。開発用 `db.sqlite3` も変更しません。
`security.W021` が出る場合は、試用用ドメインでHSTSプリロードを有効にしていない旨の警告です。
HTTPSへのリダイレクトや安全なCookieの設定は有効です。

## 3. Webアプリを追加

**Web → Add a new web app → Manual configuration → Python 3.12** を選びます。
既存のWebアプリがある場合は削除せず、その設定を確認してください。

- **Source code / Working directory**: `/home/Shimohira/muroran-gourmet`
- **Virtualenv**: `/home/Shimohira/muroran-gourmet/.venv`

WSGI configuration fileを開き、生成された `.pythonanywhere-wsgi.py` の内容に置き換えます。
次のコマンドで表示できます。秘密鍵はこのファイルに含みません。

```bash
cat /home/Shimohira/muroran-gourmet/.pythonanywhere-wsgi.py
```

**Static files** に次の2行を追加します。

| URL | Directory |
| --- | --- |
| `/static/` | `/home/Shimohira/muroran-gourmet/staticfiles` |
| `/media/` | `/home/Shimohira/muroran-gourmet/public-data/media` |

**Reload** を押します。

## 4. スマートフォンで確認

`https://shimohira.pythonanywhere.com/` を開き、新規登録して操作します。
検索・店舗詳細・地図・口コミ・お気に入り・訪問登録・スタンプまで確認してください。
この環境の店舗情報は架空のサンプルです。管理者が必要な場合だけ次を実行します。

```bash
.venv/bin/python manage.py createsuperuser --settings=config.settings_public
```

この時点で、ログインや投稿を扱うアプリがインターネットから利用できます。
Webタブで指定したドメイン以外は許可せず、DEBUGは無効、CookieはHTTPSでのみ送ります。
公開用秘密鍵 `.public-config.json` と、記録を保存する `public-data/` はGit対象外です。
これらは更新時に削除せず、必要に応じてバックアップしてください。

## 更新時

ソースコードを更新後、準備コマンドを再実行してWebタブでReloadします。
初回用の `unzip -n` は既存ファイルを上書きしません。更新ZIPを使う場合は、秘密設定・DB・画像を含まない
ソースのみを更新し、`public-data/` や `.public-config.json` を保持してください。
ローカルPCの開発は従来どおり `config.settings` を利用します。
