// index.html を 1 枚の HTML（dist/InvisibleRoommates.html）に固める。依存なし（Node 18 以上）。
// - three と addons は tools/vendor/three@<版>/ にキャッシュ（無ければ jsDelivr から取得）し、
//   importmap に data: URL として埋め込む。addons 内の相対 import は bare 指定子に書き換える。
// - assets/room.glb と assets/sounds/*.mp3 は base64 で埋め込み、実行時に Blob URL にして読ませる。
// - index.html 本体は書き換えない。読み込み箇所だけ出力時に置換する（見つからなければ失敗させる）。
// 使い方: node tools/bundle.mjs
import { readFile, writeFile, mkdir, readdir, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const THREE_VERSION = '0.170.0';
const CDN = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/`;
const VENDOR = path.join(ROOT, 'tools', 'vendor', `three@${THREE_VERSION}`);
const OUT = path.join(ROOT, 'dist', 'InvisibleRoommates.html');

const exists = (p) => access(p).then(() => true, () => false);

// パッケージ内パス（例: build/three.module.js）を vendor から読む。無ければ CDN から取得して保存
async function getPkgFile(rel) {
  const local = path.join(VENDOR, ...rel.split('/'));
  if (await exists(local)) return readFile(local, 'utf8');
  const res = await fetch(CDN + rel);
  if (!res.ok) throw new Error(`取得失敗: ${CDN + rel} (${res.status})`);
  const text = await res.text();
  await mkdir(path.dirname(local), { recursive: true });
  await writeFile(local, text);
  console.log('vendor に保存:', rel);
  return text;
}

// 指定子 → パッケージ内パス（importmap の 2 行と同じ対応）
function specToPkg(spec) {
  if (spec === 'three') return 'build/three.module.js';
  if (spec.startsWith('three/addons/')) return 'examples/jsm/' + spec.slice('three/addons/'.length);
  throw new Error('未対応の import: ' + spec);
}
const pkgToSpec = (rel) => rel === 'build/three.module.js' ? 'three' : 'three/addons/' + rel.slice('examples/jsm/'.length);

const IMPORT_RE = /(\bimport\s*(?:[\w*{}\s,$]+\s*from\s*)?|\bexport\s*(?:\*|\{[^}]*\})\s*from\s*)(['"])([^'"]+)\2/g;

// モジュールの import を集め、相対指定は bare 指定子に書き換えて再帰的に読む
async function collect(entrySpecs) {
  const mods = new Map(); // spec -> source
  const queue = [...entrySpecs];
  while (queue.length) {
    const spec = queue.shift();
    if (mods.has(spec)) continue;
    const rel = specToPkg(spec);
    let src = await getPkgFile(rel);
    src = src.replace(IMPORT_RE, (m, head, q, target) => {
      let s = target;
      if (target.startsWith('.')) {
        s = pkgToSpec(path.posix.normalize(path.posix.join(path.posix.dirname(rel), target)));
      }
      queue.push(s);
      return head + q + s + q;
    });
    if (/\bimport\s*\(/.test(src)) console.warn('注意: 動的 import を含む:', spec);
    mods.set(spec, src);
  }
  return mods;
}

function replaceOnce(text, from, to) {
  const i = text.indexOf(from);
  if (i < 0 || text.indexOf(from, i + 1) >= 0) throw new Error('置換箇所が 1 か所に定まりません: ' + from);
  return text.slice(0, i) + to + text.slice(i + from.length);
}

const html = await readFile(path.join(ROOT, 'index.html'), 'utf8');

// 1) メインのモジュールから使っている指定子を集める
const mainMatch = html.match(/<script type="module">([\s\S]*?)<\/script>/);
if (!mainMatch) throw new Error('index.html に <script type="module"> がありません');
const entry = [...mainMatch[1].matchAll(IMPORT_RE)].map((m) => m[3]);
const mods = await collect(entry);
const imports = {};
for (const [spec, src] of mods) imports[spec] = 'data:text/javascript;base64,' + Buffer.from(src).toString('base64');
const importmap = `<script type="importmap">\n${JSON.stringify({ imports })}\n</script>`;

// 2) 素材を base64 で埋め込む
const assets = { 'assets/room.glb': ['model/gltf-binary', await readFile(path.join(ROOT, 'assets', 'room.glb'))] };
for (const f of (await readdir(path.join(ROOT, 'assets', 'sounds'))).filter((f) => f.endsWith('.mp3')).sort()) {
  assets['assets/sounds/' + f] = ['audio/mpeg', await readFile(path.join(ROOT, 'assets', 'sounds', f))];
}
const assetJson = JSON.stringify(Object.fromEntries(Object.entries(assets).map(([k, [type, buf]]) => [k, [type, buf.toString('base64')]])));
const assetScript = `<script>
// バンドル用: 埋め込んだ素材を Blob URL にして返す（初回だけ変換）
(() => {
  const data = ${assetJson};
  const cache = {};
  window.__IR_ASSET = (p) => {
    if (cache[p]) return cache[p];
    const e = data[p];
    if (!e) throw new Error('埋め込まれていない素材: ' + p);
    const bin = atob(e[1]);
    const u8 = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return (cache[p] = URL.createObjectURL(new Blob([u8], { type: e[0] })));
  };
})();
</script>`;

// 3) index.html の読み込み箇所だけ差し替える
let out = html;
out = out.replace(/<script type="importmap">[\s\S]*?<\/script>/, () => importmap + '\n' + assetScript);
out = replaceOnce(out, "loadAsync('assets/room.glb')", "loadAsync(__IR_ASSET('assets/room.glb'))");
out = replaceOnce(out, "fetch('assets/sounds/' + n + '.mp3')", "fetch(__IR_ASSET('assets/sounds/' + n + '.mp3'))");
if (/https?:\/\/(?!www\.w3\.org)/.test(out.replace(/data:[^"']*/g, ''))) console.warn('注意: 出力に http(s) の URL が残っています');

await mkdir(path.dirname(OUT), { recursive: true });
await writeFile(OUT, out);
console.log(`書き出し: ${path.relative(ROOT, OUT)} (${(Buffer.byteLength(out) / 1048576).toFixed(1)} MB, モジュール ${mods.size} 個, 素材 ${Object.keys(assets).length} 個)`);
