# STEP 8〜11 実装記録

## 再開時に読むこと

- ブランチ: `feat/complete-prototype`
- 基点: `origin/main` の `1e9fb0f`（店舗検索 PR #3 マージ済み）
- 既存のアカウント・店舗・DBを維持する。既存マイグレーションの削除やDBリセットはしない。
- この作業環境は分離済み。既存チェックアウトを使い、追加の worktree は作らない。
- `git status` とこの記録を確認し、未コミットの変更を保持してから再開する。
- フェーズの区切りでテスト結果を追記し、同じブランチにコミット・pushする。

## 計画と状態

1. 既存調査: 完了。認証・共通UI・店舗検索を再利用。
2. 店舗検索: 完了済み機能を確認。`python manage.py test restaurants` の35件成功。
3. 地図・経路: 08・10・11と共通描画を実装。Leaflet 1.9.4はnpm配布物のSHA-512を照合して同梱。16は次のフェーズで接続する。
4. 口コミ・お気に入り: Review / Favorite / Report、本人の編集・削除、管理者削除、平均評価、詳細・カード・14への接続を実装。
5. 訪問・スタンプ・マイページ: 実装済み。Visit、13・15・16、プロフィール編集、履歴、全ナビゲーションを接続。
6. 結合・README・PR: 実ブラウザ・PowerShell手順・全テスト・README更新を実施済み。最終のWindows/Ubuntu CIとPR確認が残る。

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

## フェーズ6の途中結果

- 全Djangoテスト124件成功。表示名未設定時に公開口コミへメールアドレスを出さないこと、他人の口コミ削除にはスタッフ状態と削除権限の両方が必要なことも回帰テストに追加。
- `python3 scripts/browser_smoke.py --artifacts /tmp/muroran-complete-browser` が成功。
  口コミCRUD、お気に入りの詳細・カード双方からの登録／解除、訪問解除とポイント減算、プロフィール・メール変更、
  再ログイン、新規登録、本人以外の履歴非表示、通報を実操作した。
- 13の保護画面を320/390/768/1440pxで確認し、横スクロール・ページエラーなし。
- 最初の背景実取得は失敗（`real_osm_loaded: false`）。以後の固定画像によるUI確認・通信失敗の模擬と区別して記録。
- `scripts/smoke_server.py` は一時DBだけを使い、既存の認証・店舗・座標の移行保持も成功。
- 読みやすいポイント表記、地図の44pxタップ領域、戻り先維持を調整。調整後の最終ブラウザ再確認も成功（`/tmp/muroran-complete-browser-final/report.json`）。
- READMEをPowerShell向けに更新。Windows用tzdataを取得確認済み。CIにUbuntu/Windows行列を追加したが、まだその結果は未確認。

### Windows CIの診断

最初のCIはUbuntu成功・Windowsの依存導入とマイグレーション成功・Windowsテスト失敗。
既存の設定テストが子プロセスの日本語エラーをOS既定のエンコーディングで扱う問題を、
`PYTHONIOENCODING=ascii` で同テストを実行して再現した。
子プロセスの出力と読み取りをUTF-8に固定し、CIのテスト出力も統一した。
失敗時にChecksの注釈へ詳細を残すラッパーを追加した（終了コードはそのまま返す）。
修正後のWindows CI確認が必要。

## 主な設計

- Restaurant / Genre / Tag と既存の検索条件は再利用し、他アプリに店舗情報をコピーしない。
- Favorite / Visit はユーザー・店舗の組をDBでも一意にする。POSTの追加／解除は再送しても増減が重複しない。
- 訪問登録は自己申告。異なる1店舗につき1スタンプ・10ポイント。解除すると減る。残高を別途保存しない。
- 口コミは1〜5、200文字以内。本人だけ編集でき、本人と削除権限のある管理者が削除できる。
- 位置未登録・通信失敗でも案内と店舗リンクを残す。地図表示の店舗文字列はDOMの textContent で挿入する。
- 地図はOpenStreetMapに帰属表示。Googleへのリンクで徒歩・公共交通の実際の経路を確認し、時刻を推測しない。

## 次の作業

1. フェーズ6のチェックポイントをpushし、Ubuntu/WindowsのCIを確認・必要なら修正する。
2. 記録を最終結果で更新し、`feat/complete-prototype` からmainへの日本語PRを作成する。
OpenStreetMapの `tile.openstreetmap.org` は現環境で403。許可ドメイン追加を下書きに保存済み、設定の反映待ち。
Leafletは同梱済みで、背景の取得失敗時もピン・店舗リンクを表示する設計。実ブラウザ確認は結合フェーズで実施する。

## 最終確認用コマンド

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_restaurants
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
```
