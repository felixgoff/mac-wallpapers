import { SvelteMap } from 'svelte/reactivity';
import { mb } from './versions.js';
import { crc32, zip } from './zip.js';
import { packageFiles, videoName } from './wallpaperEngine.js';

export const toast = $state({ msg: '', show: false });
let timer;
export function say(msg, ms = 2400) {
  toast.msg = msg;
  toast.show = true;
  clearTimeout(timer);
  timer = setTimeout(() => (toast.show = false), ms);
}

// Downloads stream through fetch so the badge can show real progress. If the browser can't
// fetch (Chrome doesn't trust Apple's aerial server certificate), the next click just follows the link.
export const jobs = new SvelteMap(); // item index -> { state: 'loading'|'done', p, got, total, ctrl }
let fetchBroken = false;

const fileName = (n, ext) => n.replace(/[/\\:*?"<>|]/g, '-') + ext;

function saveBlob(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
}

async function download(d) {
  const cur = jobs.get(d.i);
  if (cur?.state === 'loading') return cur.ctrl.abort();
  const j = $state({ state: 'loading', p: null, got: 0, total: 0, ctrl: new AbortController() });
  jobs.set(d.i, j);
  try {
    const res = await fetch(d.url, { signal: j.ctrl.signal });
    if (!res.ok || !res.body) throw new Error('HTTP ' + res.status);
    j.total = +res.headers.get('content-length') || 0;
    say(`Downloading “${d.n}”${j.total ? ` — ${mb(j.total)}` : ''}`);
    const reader = res.body.getReader(), chunks = [];
    let got = 0, last = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      got += value.length;
      const now = performance.now();
      if (now - last > 120) { last = now; j.got = got; if (j.total) j.p = got / j.total; }
    }
    saveBlob(new Blob(chunks, { type: res.headers.get('content-type') || 'application/octet-stream' }), fileName(d.n, d.ext || '.mov'));
    Object.assign(j, { state: 'done', p: 1, got });
    say(`Saved “${d.n}” to your Downloads folder`);
    setTimeout(() => jobs.get(d.i) === j && jobs.delete(d.i), 2200);
  } catch (err) {
    jobs.delete(d.i);
    if (err.name === 'AbortError') return say(`Stopped downloading “${d.n}”`);
    fetchBroken = true;
    say(`This browser can’t download it here — click again to open the ${d.kind === 'aerial' ? 'video' : 'file'} instead`, 5000);
  }
}

// Downloads every time-of-day video of an aerial set and packs them into a Wallpaper Engine wallpaper
async function buildPackage(d) {
  const cur = jobs.get(d.i);
  if (cur?.state === 'loading') return cur.ctrl.abort();
  const j = $state({ state: 'loading', p: 0, got: 0, total: d.size, ctrl: new AbortController() });
  jobs.set(d.i, j);
  try {
    say(`Building “${d.n}” for Wallpaper Engine — downloading ${mb(d.size)} of Apple’s videos…`, 6000);
    const videos = [];
    let got = 0, last = 0;
    for (const part of d.parts) {
      const res = await fetch(part.u, { signal: j.ctrl.signal });
      if (!res.ok || !res.body) throw new Error('HTTP ' + res.status);
      const reader = res.body.getReader(), chunks = [];
      let crc = 0, size = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        crc = crc32(value, crc);
        size += value.length;
        got += value.length;
        const now = performance.now();
        if (now - last > 120) { last = now; j.got = got; j.p = Math.min(got / d.size, 0.99); }
      }
      videos.push({ name: videoName(part), blob: new Blob(chunks), size, crc });
    }
    const preview = new Uint8Array(await (await fetch(d.img)).arrayBuffer());
    saveBlob(zip(packageFiles(d, videos, preview)), fileName(`${d.n} (Wallpaper Engine)`, '.zip'));
    Object.assign(j, { state: 'done', p: 1, got });
    say(`Saved “${d.n} (Wallpaper Engine).zip” — see the README inside to add it`, 6000);
    setTimeout(() => jobs.get(d.i) === j && jobs.delete(d.i), 2200);
  } catch (err) {
    jobs.delete(d.i);
    if (err.name === 'AbortError') return say(`Stopped building “${d.n}”`);
    say('This browser can’t download Apple’s videos — open this page in Safari on a Mac to build the package', 7000);
  }
}

export function onDownloadClick(e, d) {
  if (d.kind === 'we') {
    e.preventDefault();
    return buildPackage(d);
  }
  if (d.kind === 'still' && d.how !== 'fetch') {
    // These hosts don't allow in-page downloads; the link downloads the file itself
    say(d.how === 'zip' ? `Downloading “${d.n}” — ${mb(d.size)} zip with a .heic inside`
      : `Downloading “${d.n}”${d.size ? ` — ${mb(d.size)}` : ''}`, 3500);
    return;
  }
  if (fetchBroken) return;
  e.preventDefault();
  download(d);
}

// Extra versions (iPad, iPhone, frames…) of a wallpaper
export async function onAltClick(e, d, alt) {
  if (d.how !== 'fetch' || fetchBroken) return say(`Downloading “${d.n}” — ${alt.l}`);
  e.preventDefault();
  const ext = (alt.u.match(/\.\w+(?=$|\?)/) || [d.ext || ''])[0];
  try {
    say(`Downloading “${d.n}” — ${alt.l}${alt.size ? ` (${mb(alt.size)})` : ''}…`, 60000);
    const res = await fetch(alt.u);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    saveBlob(await res.blob(), fileName(`${d.n} (${alt.l})`, ext));
    say(`Saved “${d.n}” (${alt.l}) to your Downloads folder`);
  } catch {
    fetchBroken = true;
    say('This browser can’t download it here — click again to open the file instead', 5000);
  }
}
