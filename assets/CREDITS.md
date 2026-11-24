# 素材の出典

`assets/textures/` のテクスチャは、すべて CC0（パブリックドメイン）の素材です。
各素材は diff（色）/ nor（法線、OpenGL 形式）/ arm（R=AO・G=粗さ・B=金属）の 3 枚組で、Web 向けに JPG で再圧縮しています。

## Poly Haven（https://polyhaven.com 、ライセンス: CC0）

| 素材 | 使った場所 | 解像度 | URL |
|---|---|---|---|
| Laminate Floor 02 | 床（フローリング） | 2K | https://polyhaven.com/a/laminate_floor_02 |
| Plastered Wall 04 | 壁・床下の台 | 2K | https://polyhaven.com/a/plastered_wall_04 |
| Oak Veneer 01 | 流し台と吊戸棚の扉、机 | 1K | https://polyhaven.com/a/oak_veneer_01 |
| Wood Table 001 | 椅子 | 1K | https://polyhaven.com/a/wood_table_001 |
| Kitchen Wood | ベッド、テレビ台、ローテーブル、上がり框 | 1K | https://polyhaven.com/a/kitchen_wood |
| Long White Tiles | 浴室の壁、キッチンの壁 | 1K | https://polyhaven.com/a/long_white_tiles |
| Granite Tile | 玄関の三和土、浴室の床 | 1K | https://polyhaven.com/a/granite_tile |
| Fabric Pattern 05（色違い col_01） | 掛け布団 | 1K | https://polyhaven.com/a/fabric_pattern_05 |
| Cotton Jersey | シーツ、枕、座布団、タオル、椅子の座面 | 1K | https://polyhaven.com/a/cotton_jersey |
| Rough Linen | カーテン | 1K | https://polyhaven.com/a/rough_linen |

## ambientCG（https://ambientcg.com 、ライセンス: CC0）

| 素材 | 使った場所 | 解像度 | URL |
|---|---|---|---|
| Metal 012 | ステンレスの天板・シンク・レンジフード・取っ手 | 1K | https://ambientcg.com/view?id=Metal012 |
| Carpet 016 | ラグ | 1K | https://ambientcg.com/view?id=Carpet016 |

## 手を加えた点

- `plastered_wall_04_diff_2k.jpg` は、白い壁に見えるよう明るさを持ち上げています（ffmpeg の `lutyuv=y=val*0.6+132`）。
- ambientCG の素材は、粗さ・金属・AO の画像を 1 枚の arm 画像にまとめています（Metal012 は AO なし＝白、Carpet016 は金属なし＝黒）。
- 色の違い（座布団の色、タオルの色など）は、glTF のベースカラー係数で掛け合わせています。

3D モデル（`assets/room.glb`）は `blender/build_room.py` で一から作ったものです。

# 音の出典

`assets/sounds/` の音は、すべて CC0 またはパブリックドメインの実録音です。
元の録音から必要な部分だけを切り出し、モノラルの mp3（44.1kHz、効果音 96kbps・テレビ 64kbps）にしています。

## Freesound（https://freesound.org 、ライセンス: CC0 1.0）

Freesound のページでライセンスが CC0（http://creativecommons.org/publicdomain/zero/1.0/）であることを確かめて、公開プレビュー（mp3）から切り出しました。

| ファイル | 使った場面 | 素材名 | 作者 | URL |
|---|---|---|---|---|
| door_unlock_open.mp3 / door_close.mp3 | 帰宅したときの鍵とドア、ドアが閉まる音 | Unlock open close apartment door from hallway.wav | radiojaja | https://freesound.org/people/radiojaja/sounds/524779/ |
| door_open.mp3 / door_lock.mp3 | 出かけるときのドア、出たあとの鍵 | Front door open close lock | jmayoff | https://freesound.org/people/jmayoff/sounds/475987/ |
| switch.mp3 | 部屋と浴室の電気のスイッチ | Switch Light 06.wav | tbrook | https://freesound.org/people/tbrook/sounds/348224/ |
| lamp_switch.mp3 | スタンドのスイッチ | Desk lamp switch | jsbarrett | https://freesound.org/people/jsbarrett/sounds/395125/ |
| bath_door_open.mp3 / bath_door_close.mp3 | 浴室のドアの開け閉め | Door (Opening and Closing) | Breviceps | https://freesound.org/people/Breviceps/sounds/457042/ |
| knob_rattle.mp3 | 浴室が使用中のときのドアノブ | jp_lockedknob09.flac | JPolito | https://freesound.org/people/JPolito/sounds/391723/ |
| knob_rattle2.mp3 | 浴室が使用中のときのドアノブ（短いほう） | doorknob jiggle | nathanmanaker | https://freesound.org/people/nathanmanaker/sounds/486946/ |
| water.mp3 | 水道の水（ループ） | Kitchen Faucet Running Water | Tom_Kaszuba | https://freesound.org/people/Tom_Kaszuba/sounds/657244/ |
| stove_ignite.mp3 | コンロの点火のカチカチ | Stove Range Igniting Clicking.wav | baidonovan | https://freesound.org/people/baidonovan/sounds/187344/ |
| gas.mp3 | コンロの火（ループ） | Burner Gas Flame Sound (24Bit/48kHz) | neilraouf | https://freesound.org/people/neilraouf/sounds/435643/ |
| kettle.mp3 | やかんのフタのカタカタ（ループ） | Pan Lid - Steam Bobbing | Sadiquecat | https://freesound.org/people/Sadiquecat/sounds/825740/ |
| fridge_open.mp3 / fridge_close.mp3 | 冷蔵庫の扉の開け閉め | Open fridge + fridge interior + close fridge | Breviceps | https://freesound.org/people/Breviceps/sounds/458402/ |
| tv_on.mp3 / tv_off.mp3 | テレビの電源 | TV television, on off.wav | SpliceSound | https://freesound.org/people/SpliceSound/sounds/188197/ |
| tv_ch0.mp3 / tv_ch1.mp3 | テレビの番組（スポーツ）。くぐもらせて流す | Muffled Sports Program（元はパブリックドメインの米国防総省の映像の音声） | milcahrawr | https://freesound.org/people/milcahrawr/sounds/875353/ |
| remote_1.mp3 / remote_2.mp3 | リモコンを置く音 | CONTROL SOBRE MADERA.wav | el.kanty | https://freesound.org/people/el.kanty/sounds/626432/ |
| cushion_1.mp3 | 座布団に座る・立つ | Pillow hit impact | jhamelatejome | https://freesound.org/people/jhamelatejome/sounds/449443/ |
| cushion_2.mp3 | 座布団に座る・立つ | 006-Libro_En_Almohada.wav | salo_c_r_711 | https://freesound.org/people/salo_c_r_711/sounds/446700/ |
| chair_pull.mp3 / chair_push.mp3 | 椅子を引く・戻す | Wooden chair, push in, pull out.wav | SpliceSound | https://freesound.org/people/SpliceSound/sounds/218316/ |
| laptop_open.mp3 / laptop_close.mp3 | ノートPCのふたの開け閉め | laptop open and close.wav | lartti | https://freesound.org/people/lartti/sounds/519337/ |
| typing.mp3 | ノートPCのキーボード | quiet typing on laptop computer | lmz36 | https://freesound.org/people/lmz36/sounds/721033/ |
| curtain_1.mp3 / curtain_2.mp3 | カーテンを引く | Curtains Opening or Closing 3 Short.wav | RutgerMuller | https://freesound.org/people/RutgerMuller/sounds/51139/ |
| blanket_1.mp3 | 布団の衣擦れ | Blanket Movement 6 | OwlStorm | https://freesound.org/people/OwlStorm/sounds/320144/ |
| blanket_2.mp3 | 布団の衣擦れ | Comforter Rustle.wav | H0wlr | https://freesound.org/people/H0wlr/sounds/404903/ |

## Internet Archive（https://archive.org 、ライセンス: Public Domain Mark 1.0）

| ファイル | 使った場面 | 素材名 | 作者 | URL |
|---|---|---|---|---|
| tv_ch2.mp3 | テレビの番組（朗読）。言葉が聞き取れないくらいにくぐもらせて流す | LibriVox「Short Story Collection 088」01 The Blind Man（Kate Chopin 作、LibriVox のボランティアの朗読） | LibriVox | https://archive.org/details/ss088_2006_librivox |
| tv_ch3.mp3 | テレビの番組（音楽）。くぐもらせて流す | F. Chopin - Waltz In A Flat Major, Op. 69 No. 1（Luke Faulkner の演奏） | Musopen | https://archive.org/details/MusopenChopinWaltzOp69no1 |

## 手を加えた点（音）

- 低い雑音を除くハイパスフィルター（50〜150Hz）をかけ、効果音はピークを -3dBFS にそろえています。
- ループの音（水道・コンロの火・やかん・テレビ）は、終わりを始まりに重ねて（クロスフェード）継ぎ目が目立たないようにしています。
- テレビの番組は、ファイルの段階で 3kHz より上を落とし、再生時にさらに 380〜700Hz のローパスで、壁越しのようなくぐもった音にしています。
