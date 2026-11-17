# STEP 8〜11 実装記録

## 再開時に読むこと

- 2026-11-17の仕様比較後の修正は末尾の「仕様比較後の修正」を参照。以前の実装履歴とは分けて記録する。
- ブランチ: `feat/complete-prototype`
- 基点: `origin/main` の `1e9fb0f`（店舗検索 PR #3 マージ済み）
- 既存のアカウント・店舗・DBを維持する。既存マイグレーションの削除やDBリセットはしない。
- この作業環境は分離済み。既存チェックアウトを使い、追加の worktree は作らない。
- `git status` とこの記録を確認し、未コミットの変更を保持してから再開する。
- フェーズの区切りでテスト結果を追記し、同じブランチにコミット・pushする。

## 計画と状態

1. 既存調査: 完了。認証・共通UI・店舗検索を再利用。
2. 店舗検索: 完了済み機能を確認。`python manage.py test restaurants` の35件成功。
3. 地図・経路: 08・10・11と共通描画を実装。Leaflet 1.9.4はnpm配布物のSHA-512を照合して同梱。16への共通描画の接続も完了。
4. 口コミ・お気に入り: Review / Favorite / Report、本人の編集・削除、管理者削除、平均評価、詳細・カード・14への接続を実装。
5. 訪問・スタンプ・マイページ: 実装済み。Visit、13・15・16、プロフィール編集、履歴、全ナビゲーションを接続。
6. 結合・README・PR: 完了。実ブラウザ・PowerShell手順・全テスト・README更新、Windows/Ubuntu CI成功。PR #4を作成済み。

PR: https://github.com/potatotipus/muroran-gourmet/pull/4

## フェーズ3の検証

`.venv/bin/python manage.py test maps restaurants accounts` : 67件成功、失敗・スキップなし。
座標・詳細URL・Google Maps URLs・未登録位置・JSONエスケープ・アクセス制限を確認。

## フェーズ4の検証

`.venv/bin/python manage.py test community restaurants maps accounts` : 86件成功。
集計追加で店舗の既定の並び順が消える不具合を検出し、検索共通処理で明示的に店名・主キー順を指定して修正。
口コミ200文字・評価範囲・本人権限・管理者削除・平均更新、CSRF、重複お気に入り、利用者分離、通報の保留保存を検証。
新規マイグレーションは `community/0001_initial`。既存の店舗・認証テーブルは変更しない。

## フェーズ5の検証

`.venv/bin/python manage.py test visits accounts.test_profile tests.test_integration community maps restaurants accounts.tests` : 109件成功。
新規マイグレーションは `visits/0001_initial`。ポイントは訪問件数から算出し、独立したポイント残高テーブルを作らない。
重複・解除・利用者分離・自己申告表示・プロフィール権限・メール変更時の再認証・全16画面の表示とナビを検証。
個人マップは本人の記録だけを表示し、お気に入り＋訪問済みの赤優先と両状態の表示データを確認。

## フェーズ6の最終結果

- 全Djangoテスト124件成功。表示名未設定時に公開口コミへメールアドレスを出さないこと、他人の口コミ削除にはスタッフ状態と削除権限の両方が必要なことも回帰テストに追加。
- `python3 scripts/browser_smoke.py --artifacts /tmp/muroran-complete-browser` が成功。
  口コミCRUD、お気に入りの詳細・カード双方からの登録／解除、訪問解除とポイント減算、プロフィール・メール変更、
  再ログイン、新規登録、本人以外の履歴非表示、通報を実操作した。
- 13の保護画面を320/390/768/1440pxで確認し、横スクロール・ページエラーなし。
- 最初の背景実取得は失敗（`real_osm_loaded: false`）。以後の固定画像によるUI確認・通信失敗の模擬と区別して記録。
- `scripts/smoke_server.py` は一時DBだけを使い、既存の認証・店舗・座標の移行保持も成功。
- 読みやすいポイント表記、地図の44pxタップ領域、戻り先維持を調整。調整後の最終ブラウザ再確認も成功（`/tmp/muroran-complete-browser-final/report.json`）。
- READMEをPowerShell向けに更新。Windows用tzdataを取得確認済み。CIのUbuntu/Windows行列はいずれも124件成功。

### Windows CIの診断

最初のCIはUbuntu成功・Windowsの依存導入とマイグレーション成功・Windowsテスト失敗。
既存の設定テストが子プロセスの日本語エラーをOS既定のエンコーディングで扱う問題を、
`PYTHONIOENCODING=ascii` で同テストを実行して再現した。
子プロセスの出力と読み取りをUTF-8に固定し、CIのテスト出力も統一した。
失敗時にChecksの注釈へ詳細を残すラッパーを追加した（終了コードはそのまま返す）。
修正後はUbuntu・Windowsとも成功（run `43808321748`、コードのコミット `869141b`）。
https://github.com/potatotipus/muroran-gourmet/actions/runs/43808321748

## 主な設計

- Restaurant / Genre / Tag と既存の検索条件は再利用し、他アプリに店舗情報をコピーしない。
- Favorite / Visit はユーザー・店舗の組をDBでも一意にする。POSTの追加／解除は再送しても増減が重複しない。
- 訪問登録は自己申告。異なる1店舗につき1スタンプ・10ポイント。解除すると減る。残高を別途保存しない。
- 口コミは1〜5、200文字以内。本人だけ編集でき、本人とスタッフかつ削除権限のある管理者が削除できる。
- 位置未登録・通信失敗でも案内と店舗リンクを残す。地図表示の店舗文字列はDOMの textContent で挿入する。
- 地図はOpenStreetMapに帰属表示。Googleへのリンクで徒歩・公共交通の実際の経路を確認し、時刻を推測しない。

## 初回実装時に残っていた外部設定（2026-11-16の記録）

最新の状態は末尾の「仕様比較後の修正」を参照。

今回の範囲のコード実装は完了。現在発生中のアプリ／Djangoテストのエラーはない。
OpenStreetMapの `tile.openstreetmap.org` は現クラウド環境で403。許可ドメイン追加を下書きに保存済み、設定の反映待ち。
背景の実取得には成功していないため、固定画像を使うUI検証を実地理情報の確認とは扱わない。
設定反映後に `scripts/browser_smoke.py --require-osm` を実行し、`report.json` の `real_osm_loaded: true` を確認する。
ブラウザテストの依存は `requirements-dev.txt`、詳しいコマンドはREADMEに記載。
QR/GPS認証・ポイント交換・予約・メール到達確認／パスワード再設定・公開デプロイは今回の対象外。

## 最終確認用コマンド

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_restaurants
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
```

## 仕様比較後の修正（2026-11-17）

- 作業ブランチ：`fix/preserve-map-context-and-visit-flow`。最新 `origin/main` の `7231dd6` を基点とする。
- 対象：10の店舗ピンから09へ戻ると検索条件が失われる経路、09の訪問登録後に16へ進まない遷移。
- 方針：地図上部とピンで検証済みの同じ詳細URLを使う。訪問の登録・再送後は16へ進み、解除後は元の詳細・履歴へ戻る。
- DBモデル・マイグレーションは変更しない。元の店舗・認証・訪問データを維持する。
- 現在の環境では `tile.openstreetmap.org` の許可が反映され、HTTP 200を確認。08・10・16の実背景もブラウザで確認する。
- 回帰テストで検索条件・個人マップの表示モードの消失、登録後に09へ戻る動作を再現してから修正した。
- 地図・訪問のテスト27件成功。登録の再送で件数・ポイントが増えないこと、解除時は元の画面に戻ること、外部URLへ移動しないことも確認。
- 全Djangoテスト129件成功（従来124件＋回帰5件）。`manage.py check`、`makemigrations --check --dry-run`、`git diff --check` も成功。
- `python3 scripts/browser_smoke.py --require-osm --artifacts /tmp/muroran-navigation-fixes-browser` を実行。
  検索条件を保った地図・詳細の往復、訪問登録直後の16への移動、口コミCRUD、お気に入り、ポイント増減、プロフィール、認証・利用者分離、320/390/768/1440pxでの操作が成功。
  `functional_flow`・`search_context_preserved`・`visit_registration_opens_personal_map`・`migration_preserved` はすべて `true`。
- 実背景の取得は08・10・16すべて未成功。Chromium単体で `net::ERR_CERT_AUTHORITY_INVALID` を確認し、同じURLへのcurlはHTTP 200。
  このため `--require-osm` の終了結果は失敗であり、ブラウザ検証全体の成功とは報告しない。
- OSで信頼済みの環境CAをユーザーのChromium/NSSストアに追加する操作は、自動承認レビューで拒否された。理由は永続的な信頼設定の変更が明示承認されていないこと。
  証明書の追加・検証無効化は行っていない。外部の実地図確認は未完了として残す。
- READMEに修正後の遷移・各地図の背景取得結果の読み方を追記し、古い実装ブランチへの切り替え手順を削除した。
- 状態：アプリ修正・回帰テスト・主要操作の検証・README更新まで完了。コミット・push・PR作成とCI確認を続ける。
- 再開時：`git status` とこの節を確認。アプリのテストは成功済み。未完了のPR/CIを確認し、環境CAの永続登録にはユーザーの明示承認が必要。
