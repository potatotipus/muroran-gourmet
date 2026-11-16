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
5. 訪問・スタンプ・マイページ: 未着手。Visit、件数に基づくポイント、プロフィール編集、16の個人記録を接続。
6. 結合・README・PR: 未着手。全16画面・スマートフォン表示、PowerShell手順、全テストを確認する。

## フェーズ3の検証

`.venv/bin/python manage.py test maps restaurants accounts` : 67件成功、失敗・スキップなし。
座標・詳細URL・Google Maps URLs・未登録位置・JSONエスケープ・アクセス制限を確認。

## フェーズ4の検証

`.venv/bin/python manage.py test community restaurants maps accounts` : 86件成功。
集計追加で店舗の既定の並び順が消える不具合を検出し、検索共通処理で明示的に店名・主キー順を指定して修正。
口コミ200文字・評価範囲・本人権限・管理者削除・平均更新、CSRF、重複お気に入り、利用者分離、通報の保留保存を検証。
新規マイグレーションは `community/0001_initial`。既存の店舗・認証テーブルは変更しない。

## 主な設計

- Restaurant / Genre / Tag と既存の検索条件は再利用し、他アプリに店舗情報をコピーしない。
- Favorite / Visit はユーザー・店舗の組をDBでも一意にする。POSTの追加／解除は再送しても増減が重複しない。
- 訪問登録は自己申告。異なる1店舗につき1スタンプ・10ポイント。解除すると減る。残高を別途保存しない。
- 口コミは1〜5、200文字以内。本人だけ編集でき、本人と削除権限のある管理者が削除できる。
- 位置未登録・通信失敗でも案内と店舗リンクを残す。地図表示の店舗文字列はDOMの textContent で挿入する。
- 地図はOpenStreetMapに帰属表示。Googleへのリンクで徒歩・公共交通の実際の経路を確認し、時刻を推測しない。

## 次の作業

口コミ・お気に入りのテスト結果を確認してチェックポイントを保存し、Visit と13・15・16を実装する。
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
