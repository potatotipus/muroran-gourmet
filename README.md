# むろらんグルメマップ

室蘭のまだ知らない飲食店を発見するための、チーム G07 の Web アプリです。
Python / Django のテンプレートによるサーバーサイドレンダリングを採用しています。

## 今回の実装範囲

- Django プロジェクト `config` と、担当別の5アプリを作成・登録
- SQLite、日本語表示、タイムゾーン `Asia/Tokyo` の設定
- 共通のヘッダー・フッター・テンプレート、レスポンシブなトップ画面
- 依存バージョンの固定、基本テスト、GitHub Actions によるチェック

ログイン・新規登録ボタンは、画面遷移図に合わせた**操作できない準備中表示**です。
一般利用者向けの認証、店舗検索、地図、口コミ、お気に入り、訪問履歴、
独自モデル、デモデータはまだ実装していません。ゲスト利用の導線も設けていません。
Django 標準の管理画面のみ `/admin/` で利用できます。

## 必要なもの

- Python 3.12 以上（今回の動作確認は Python 3.12）
- Git
- 推奨環境: Windows 11 + WSL Ubuntu + VS Code

SQLite は Python 標準の `sqlite3` を使うため、別途 DB サーバーは不要です。
Node.js や API キーも、この初期構築では不要です。

## ローカル起動手順（WSL Ubuntu / Linux / macOS）

以下は WSL の Ubuntu ターミナルなどで実行します。

### 1. リポジトリを取得する

```bash
git clone https://github.com/potatotipus/muroran-gourmet.git
cd muroran-gourmet
```

PR のレビュー中は、初期構築が入ったブランチに切り替えてください。

```bash
git switch feat/django-initial-setup
```

すでに取得済みの場合は、そのチェックアウトを利用してください。
マージ後は `main` で同じ手順を実行できます。

### 2. 仮想環境を作成・有効化する

```bash
python3 -m venv .venv
source .venv/bin/activate
python --version
```

WSL Ubuntu で `venv` が見つからない場合は、Python のバージョンを確認して
対応する `python3-venv` パッケージをインストールしてください。
ターミナルを開き直した場合は `source .venv/bin/activate` を再実行します。

### 3. 依存ライブラリを導入する

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` は Django 5.2 LTS と、その依存ライブラリの動作確認済み
バージョンを固定しています。更新時はテストも実行してください。

### 4. データベースを初期化する

```bash
python manage.py migrate
```

プロジェクト直下に `db.sqlite3` が作成され、Django 標準の認証・セッションなどの
テーブルが初期化されます。同じコマンドは繰り返し実行できます。
独自アプリにはまだモデルがないため、独自のマイグレーションはありません。
DB、仮想環境、秘密情報は Git に登録しません。

### 5. 開発サーバーを起動する

```bash
python manage.py runserver
```

ローカルのブラウザで `http://127.0.0.1:8000/` を開きます。
トップ画面と、準備中のログイン・新規登録ボタンが表示されます。
終了は `Ctrl+C`、仮想環境の終了は `deactivate` です。

### 管理画面を使う場合（任意）

```bash
python manage.py createsuperuser
```

開発サーバーを起動し、`http://127.0.0.1:8000/admin/` にアクセスします。
管理者の認証は Django 標準機能です。一般利用者向けのログイン機能とは別です。
現段階では独自の店舗などのデータ登録機能はありません。

## チェックとテスト

仮想環境を有効化し、リポジトリ直下で実行してください。

```bash
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
```

テストではトップ画面・共通テンプレート・静的ファイルの検出・未実装機能の非公開・
管理画面のアクセス制御・環境変数による設定を確認します。
テスト用 DB は Django が自動作成・破棄し、ローカルの `db.sqlite3` を変更しません。
GitHub Actions でも、依存導入・マイグレーション・上記チェックを実行します。

## ディレクトリと担当範囲

```text
muroran-gourmet/
├── config/          # 全体設定、ルーティング、トップ画面
├── accounts/        # A: アカウント・ユーザー管理
├── restaurants/     # B: 店舗情報・検索
├── maps/            # C: 地図・経路案内
├── community/       # D: 口コミ・お気に入り
├── visits/          # E: 訪問履歴・スタンプ
├── templates/       # base.html、home.html、includes/
├── static/css/      # 共通スタイル
├── tests/           # 基本テスト
├── requirements.txt
└── manage.py
```

| アプリ | 今後の責務 | データ・依存関係の方針 |
| --- | --- | --- |
| `accounts` | 認証、ユーザー管理 | 認証方式・ユーザーモデルは機能実装前に相談する |
| `restaurants` | 店舗情報、ジャンル、検索 | 店舗データの管理元を一本化する |
| `maps` | 店舗の地図、経路案内、自分のマップ | 店舗位置は `restaurants`、訪問状態は `visits` から参照する |
| `community` | 口コミ、お気に入り | ユーザーと店舗を参照する |
| `visits` | 訪問履歴、スタンプ、ポイント | ユーザーと店舗を参照する |

現在の URL は `/`（トップ画面、URL 名 `home`）と `/admin/`（Django 標準管理画面）のみです。
5アプリは `AppConfig` と空の `migrations` パッケージまで用意しており、
独自モデル・URL・フォーム・アプリ間依存はまだ定義していません。

## 設計上の判断・今後の開発

- 添付テキストと画面遷移図・議事録の画像を参考にしています。
  `COG仕様書.pdf` 本体は今回の添付にはなく、未確認です。
  全16画面の仕様よりも、今回の依頼にある「初期構築のみ」を優先しました。
- トップ画面を特定の担当アプリに所属させず、`config.views.HomeView` に配置しました。
- 本格機能に備えた独自データモデルやデモ店舗は、今回追加していません。
  Django 標準の User は管理画面用に利用します。メールアドレス認証やカスタム User を
  採用する場合は、共有データを蓄積する前にモデルと移行方針を合意してください。
- 共通 UI は `templates/base.html` を継承してください。アプリごとのテンプレートや
  静的ファイルは `restaurants/templates/restaurants/` などの名前空間で分けてください。
- 各担当は機能ごとのブランチで開発し、モデル変更時はマイグレーションを同梱してください。
  他アプリのモデル・URL、共通設定、依存関係の変更は事前に担当者間で調整してください。
- Leaflet / OpenStreetMap や Googleマップ外部リンクは、地図機能の実装時に導入します。
  この画面のイラストは CSS による装飾で、実際の店舗・地図・経路を表しません。

## 環境変数と注意点

| 変数 | 既定値 | 用途 |
| --- | --- | --- |
| `DJANGO_DEBUG` | `1` | 開発時のみ `1`。`0` でデバッグ無効 |
| `DJANGO_SECRET_KEY` | 開発専用の固定値 | 開発以外では秘密鍵を環境変数で指定する |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | 許可ホストをカンマ区切りで指定する |

ローカル開発では追加設定なしで起動できます。必要なら `export DJANGO_ALLOWED_HOSTS=...`
などで指定してください。`.env` ファイルの自動読み込みは行いません。
`DJANGO_DEBUG=0` で秘密鍵が未指定の場合は、起動エラーにします。

この設定と `runserver` は開発用です。本番公開の際は、専用の設定・秘密鍵・HTTPS・
静的ファイルの配信方法などを別途整備し、`check --deploy` を実行してください。
静的ファイル収集先は `staticfiles/` で、Git の対象外です。
