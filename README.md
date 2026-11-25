# InvisibleRoommates

だれもいない部屋。でも、だれかが住んでいる——見えない同居人の暮らしを、家具の動きと生活音だけで描く箱庭（Three.js）。

## 遊び方

- clone して `dist/InvisibleRoommates.html` をダブルクリックで開く（Chrome / Edge）。サーバーもネット接続も要らない
- 最初のクリックで音が出る
- 同居人の人数は画面下の −／＋ で変える（URL に `?n=3` を付けると最初の人数を指定できる）
- 画面下の「見る」（または V キー）で、同居人の姿を見える状態にする。もう一度押すと見えない状態に戻る

## 開発

- 開き方: `npx serve .` で立てて、表示された URL を開く（`index.html` は three を jsDelivr から読む）
- バンドルの作り直し: `node tools/bundle.mjs` → `dist/InvisibleRoommates.html` を書き出す。three 0.170.0 は `tools/vendor/` にキャッシュ済み
- モデルの作り直し: `blender -b --factory-startup --python blender/build_room.py` → `assets/room.glb`

素材の出典は [assets/CREDITS.md](assets/CREDITS.md)（すべて CC0／パブリックドメイン）。
