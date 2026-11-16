# むろらんグルメマップ

室蘭のまだ知らない飲食店を発見する、チーム G07 の Web アプリです。
Python / Django / SQLite とテンプレートによるサーバーサイドレンダリングを採用しています。
既存の認証・店舗検索に、地図・口コミ・お気に入り・訪問記録を接続した全16画面のプロトタイプです。

## 実装済みの機能

| 担当 | アプリ | 内容 |
| --- | --- | --- |
| A | `accounts` | 登録、メールアドレスでの認証、ログアウト、探し方の選択、マイページ、プロフィール編集 |
| B・下平 | `restaurants` | 店舗・ジャンル・特徴の管理、ジャンル／キーワード／複合条件検索、一覧、詳細、画像、デモ投入 |
| C・末武 | `maps` | Leaflet / OpenStreetMap、店舗ピン、店舗の地図、Googleマップ外部経路、自分のマップの共通描画 |
| D・坂本 | `community` | 口コミの投稿・編集・削除、平均評価、お気に入り、情報通報・修正提案、管理者の確認 |
| E・早田 | `visits` | 自己申告の訪問登録・解除、履歴、スタンプ、ポイント計算 |

全画面で共通ヘッダー・下部ナビを利用します。ゲスト利用はありません。
認証モデルと既存DBを差し替えず、店舗のデータは `restaurants` で一元管理しています。

## Windows 11 / VS Code / PowerShell での起動

Python 3.12 と Git を用意してください。DBサーバー・Node.js・APIキーは不要です。
以下は VS Code の PowerShell ターミナルで、リポジトリ直下から実行します。
仮想環境の Python を直接指定するため、実行ポリシーの変更や仮想環境の有効化は不要です。

### 1. 取得・仮想環境の作成

```powershell
git clone https://github.com/potatotipus/muroran-gourmet.git
cd muroran-gourmet
# PRレビュー中のみ。マージ後は main を利用できます。
git switch feat/complete-prototype
py -3.12 -m venv .venv
```

取得済みの場合は既存のフォルダーを使ってください。
VS Code の「Python: Select Interpreter」で `.venv\Scripts\python.exe` を選びます。
`py` がない場合は、Python 3.12 を確認して `python -m venv .venv` を使用してください。

### 2. 依存ライブラリ

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Django 5.2 LTS、画像検証用の Pillow を固定しています。Windows では日本時間の
タイムゾーン用に `tzdata` も導入します。Leaflet 1.9.4 はリポジトリ内に同梱済みです。

### 3. マイグレーション

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

既存の `db.sqlite3` を維持し、必要なテーブルを追加します。DBを削除しないでください。
新規環境では認証・店舗・口コミ・お気に入り・通報・訪問の各テーブルを作成します。

### 4. デモ店舗の登録

```powershell
.\.venv\Scripts\python.exe manage.py seed_restaurants
```

「サンプル食堂01」など架空の10店舗を登録します。住所・位置・営業時間・価格・店主紹介・
メニューはすべてデモ用です。実店舗の写真、未確認の口コミ・評価は追加しません。
画像なし・ファイル欠落時には共通のプレースホルダーを表示します。

専用の一意キー `demo_key` により、再実行しても重複せず、既存デモの編集・タグ割り当て・通常の
店舗を上書きしません。削除されたデモ店舗は再作成されます。今回の新規デモ位置は地図で選びやすい
ように分散配置していますが、旧版で登録済みの位置も書き換えません。

### 5. 管理者の作成

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

一般画面でもメールアドレスでログインしたい管理者は、ユーザー名にも小文字のメールアドレスを
指定してください。従来の管理者ユーザー名は `/admin/` で引き続き使用できます。
一般利用者の新規登録では管理者権限を付与しません。

### 6. 開発サーバー

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

ブラウザで `http://127.0.0.1:8000/`、管理画面は `http://127.0.0.1:8000/admin/` を開きます。
終了はターミナルで `Ctrl+C` です。

### 7. ブラウザでの確認例

1. 新規登録し、04「探し方の選択」へ進む。
2. ジャンル → すべて → 店舗一覧。予算1,000円以内・カレー・中島・テイクアウトで
   「サンプルカレー店02」を検索する。
3. 店舗詳細 → 店舗の地図・バス経路・口コミへ進む。Googleマップは外部サイトで開く。
4. 口コミを投稿・編集・削除し、平均評価の変化を確認する。
5. 店舗詳細または一覧からお気に入りを登録・解除する。
6. 店舗詳細で訪問済みに登録し、スタンプ・10ポイントを確認する。解除すれば減少する。
7. マイページから自分のマップを開き、赤・緑のピンと登録状態を確認する。
8. プロフィール編集・ログアウト・再ログインを確認する。

### 8. Django テスト

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --verbosity 2
```

テスト用DBは自動作成・破棄され、通常の `db.sqlite3` は変更しません。
GitHub Actions は Python 3.12 の Ubuntu / Windows で同じチェックを実行します。

## Linux / macOS / WSL の起動

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_restaurants
python manage.py createsuperuser
python manage.py runserver
# 別のターミナルで仮想環境を有効化して実行
python manage.py test
```

## 任意のブラウザ自動確認

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts\browser_smoke.py --artifacts .\browser-artifacts
```

Linuxでは同じコマンドを `.venv/bin/python` で実行できます。システムの Chromium がある場合は利用し、
別の実行ファイルには `MURORAN_CHROMIUM_PATH` を指定できます。

スクリプトは一時DB・一時画像ディレクトリでサーバーを起動し、終了時に停止・削除します。
旧認証・店舗からのマイグレーションでの保持も検証します。通常のDBにはテストアカウントを残しません。
スクリーンショット・`report.json`・`server.log` を指定先に保存します。

最初に実際のOpenStreetMap取得を試み、その後の多数の画面チェックには固定のテスト画像を利用します。
実タイル取得の結果は `real_osm_loaded` に分けて記録します。背景の実取得も必須にする場合は
`--require-osm`、外部通信なしでUIだけ確認する場合は `--tile-mode fixture` を指定してください。
通信失敗時にピンと店舗リンクが残ることも別に検証します。テスト画像は実際の地理情報ではありません。

## 画面とURL

01〜03以外はログイン必須です。未登録の店舗・口コミIDは404です。

| 番号・画面 | URL | 名前付きURL |
| --- | --- | --- |
| 01 トップ | `/` | `home` |
| 02 ログイン | `/accounts/login/` | `accounts:login` |
| 03 新規登録 | `/accounts/signup/` | `accounts:signup` |
| 04 探し方の選択 | `/accounts/choose/` | `accounts:choose` |
| 05 ジャンル選択 | `/restaurants/genres/` | `restaurants:genres` |
| 06 店舗一覧 | `/restaurants/` | `restaurants:list` |
| 07 条件検索 | `/restaurants/filters/` | `restaurants:filters` |
| 08 マップ検索 | `/maps/search/` | `maps:search` |
| 09 店舗詳細 | `/restaurants/<id>/` | `restaurants:detail` |
| 10 店舗の地図 | `/maps/stores/<id>/` | `maps:store` |
| 11 バス・徒歩経路 | `/maps/stores/<id>/directions/` | `maps:directions` |
| 12 口コミ投稿 | `/community/stores/<id>/reviews/new/` | `community:review_create` |
| 13 スタンプ | `/visits/stamps/` | `visits:stamps` |
| 14 お気に入り | `/community/favorites/` | `community:favorites` |
| 15 マイページ | `/accounts/profile/` | `accounts:profile` |
| 16 自分のマップ | `/maps/mine/` | `maps:personal` |

追加画面はプロフィール編集・口コミ編集／削除確認・訪問履歴・情報通報です。
下部ナビは04・08・13・14・15へ接続します。ログイン・新規登録成功後は04、ログアウト後は01です。
ログアウト・お気に入り・訪問の変更はCSRFトークン付きPOSTで行い、戻り先は安全な同一サイトのパスに限定します。

## データと責務

| モデル | 関係・制約 |
| --- | --- |
| Django標準 `User` | 継続利用。認証モデルの変更・DBリセットなし |
| `Restaurant` | 店名、説明、住所、地区、座標、ジャンル、価格帯、営業時間、定休日、画像、店主紹介、メニュー、特徴、デモキー |
| `Genre` / `Tag` | 料理ジャンルと特徴を分離。識別子・表示順を持つ |
| `Review` | User・Restaurantの外部キー、1〜5点、200文字以内、投稿／編集日時。平均は実データから集計 |
| `Favorite` | User・Restaurantの組が一意 |
| `Visit` | User・Restaurantの組が一意。訪問登録日時は追加時のみ記録 |
| `Report` | 投稿者・店舗・任意の口コミ・内容・確認状態・管理者メモ。口コミ削除後も報告を保持 |

`community/0001_initial`、`visits/0001_initial` は新しいテーブルだけを追加します。
既存の `restaurants/0001_initial`・`0002_search_categories` と認証のマイグレーションは変更しません。

### アカウント

- メールアドレスは前後の空白除去・小文字化し、`User.email` と一意な `User.username` に保存します。
  表示用の「ユーザー名」は `User.first_name`、各150文字以内です。Django標準 ModelBackend・ハッシュ・
  パスワード検証・セッションを使用します。
- プロフィールは本人だけ編集できます。メール変更には現在のパスワードを確認し、ログインIDも更新します。
  表示名だけの編集では従来の管理者ユーザー名は変更しません。
- 他担当はユーザー参照に `settings.AUTH_USER_MODEL` / `get_user_model()`、表示名に `get_short_name()` を使用してください。

### 検索

- 予算は**価格帯の上限**が500／1,000／1,500円以内の店舗です。上限が未登録なら予算検索から除外します。
- キーワードは店舗名・説明・住所・地区・ジャンル・タグ・店主紹介・メニューの部分一致。
  複数語と、ジャンル・予算・エリア・複数の特徴はすべて AND です。
- 「ワンコイン」はタグ。「激安大盛り」は `cheap` と `large` の両タグです。
- エリアは高砂・中島・本町・その他の地区を選択可能。「その他」はそれら3地区以外で、未登録地区は含みません。
- 営業時間のリアルタイム判定はしません。夜遅くの特徴は確認済みの営業時間と一緒に管理します。
- 条件は GET の `q`・`genre`・`budget`・`area`・複数の `tags` で保持し、一覧・地図・詳細・戻るリンクで引き継ぎます。
  不正な条件はエラー、0件は案内を表示します。リセットすると全条件を解除します。

### 口コミ・お気に入り・通報

- 口コミは文字数・評価をサーバーとDBでも検証します。画像は添付しません。
- 本人だけ編集でき、削除は本人またはスタッフで `community.delete_review` 権限のある管理者に限定します。
  変更・削除後は平均も変わり、0件は「まだ口コミがありません」「未評価」と表示します。
- お気に入りと訪問は明示的な登録／解除を使い、同じPOSTを再送しても重複しません。他人の記録は表示・変更できません。
- 店舗・口コミの通報は未確認で保存し、管理者がAdminで確認状態とメモを更新します。提案が店舗情報を直接変更する処理はありません。

### 訪問とポイント

訪問登録は自己申告で、実来店の認証ではありません。異なる1店舗につき1スタンプ・10ポイントです。
現在の登録店舗数から毎回計算し、解除すると対応分が減ります。設定 `VISIT_POINTS_PER_STORE` と
`STAMP_GOAL`（初期値5）で計算ルール・達成目標を変更できます。現金・商品への交換はありません。

### 地図と経路

- 08・10・16は同じ `maps/services.py` と `maps/static/maps/map.js` を利用します。
- 通常の未訪問は青、訪問済みは緑、お気に入りは赤。両方の場合は赤を優先し、両状態を表示します。
  個人マップは自分の記録だけを表示し、お気に入り／訪問済みで切り替えられます。
- 座標未登録の店舗はピンにせず、件数・案内を表示します。店舗単体では住所があれば外部検索へ案内できます。
- 背景取得には `tile.openstreetmap.org` へのインターネット接続が必要です。制限・オフライン時にもピンと
  店舗リンクを残します。許可設定の必要なクラウド環境では、同ドメインを許可してください。
- Google Maps URLs は `api=1` と `travelmode=transit` / `walking` を使い、出発地・時刻・実際の運行は
  Googleマップで確認します。時刻・所要時間の推測や有料APIはありません。
- 地図上にOpenStreetMapの帰属を表示します。[第三者ライブラリと利用方針](docs/THIRD_PARTY.md)も参照してください。

## 管理・共同開発

管理画面は `/admin/` です。店舗・分類・画像・口コミ・通報・訪問・お気に入りを権限に応じて管理できます。
店舗画像は掲載許可のある JPEG・PNG・WebP（5MB以内）。画像はGit対象外の `media/` に保存し、開発時のみDjangoで配信します。
初期タグの識別子 `one-coin`・`cheap`・`large`・`late-night` を維持してください。新規の識別子は一意の英数字・ハイフンです。

- 店舗・位置・分類は `restaurants` で管理し、他アプリへ複製しないでください。詳細URLは `get_absolute_url()` で取得できます。
- 座標は任意のDecimal値です。両方の入力有無と範囲、価格の大小は既存DB制約で守ります。
- ユーザー別状態・平均を付ける検索は `restaurants/query.py`、ポイントは `visits/services.py` に集約しています。
- 共通テンプレートを継承し、アプリのテンプレート・静的ファイルには名前空間を付けてください。
- モデル変更には新しいマイグレーションを追加し、共有済みの過去マイグレーションを削除しないでください。
- 変更前に関連担当と外部キー・URLを相談し、各自のブランチからPRで統合してください。
- 中断からの再開は [実装記録](docs/IMPLEMENTATION_PROGRESS.md) と `git status` を先に確認し、既存の編集を保持してください。
  このクラウド環境は分離済みなので既存チェックアウトを使います。

## 設計上の判断・対象外

今回の依頼を最優先にし、最新議事録、画面構成は画面遷移図、次にCOG仕様書を参照しています。
COG仕様書の任意のゲスト閲覧は実装せず、ログイン後は04へ遷移します。担当分担は最新議事録のB〜Eを維持します。

予約、QR/GPS来店認証、ポイント交換、メール到達確認・パスワード再設定、店主の本人確認、店舗向け分析は対象外です。
実店舗情報への置き換え・掲載許可の確認、公開サーバーへのデプロイは行っていません。

ローカル設定は `DJANGO_DEBUG=1`、許可ホストは `localhost,127.0.0.1,[::1]` が既定です。
`DJANGO_DEBUG=0` では `DJANGO_SECRET_KEY` が必要です。`.env` の自動読込はありません。
開発以外の秘密鍵・HTTPS・静的／画像配信は別途設定し、公開前に `check --deploy` を実行してください。
DB・アップロード画像・仮想環境・秘密情報・ブラウザ検証の出力はGitに登録しません。
