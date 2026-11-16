# 地図の依存と帰属表示

- Leaflet 1.9.4: https://leafletjs.com/ / BSD 2-Clause License。
- 同梱元: npm の `leaflet@1.9.4`。配布tarballのSHA-512をnpmレジストリの integrity と照合してから必要なファイルをコピーした。
- ライセンス: `maps/static/maps/vendor/leaflet/LICENSE`。テキストの改行のみLFに統一している。
- Leaflet 本体・CSS・画像はローカルのstaticとして配信し、実行時のCDNは不要。
- 背景タイル: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`。
- 地図上に `© OpenStreetMap contributors` と著作権ページへのリンクを表示する。
- タイル利用方針: https://operations.osmfoundation.org/policies/tiles/ 。一括取得・オフライン用の先読みは行わない。
- 本番でアクセスが増える際は、同方針に従い適切なタイル配信サービスを選ぶ。
- 経路は Google Maps URLs（`api=1`、`travelmode=transit` / `walking`）を生成するだけで、APIキーや有料APIは使わない。
- 任意のブラウザテストは、最初の実タイル取得の結果と固定テスト画像・通信失敗の模擬を区別して `report.json` に記録する。
