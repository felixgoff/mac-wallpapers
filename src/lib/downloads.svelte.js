import { SvelteMap } from 'svelte/reactivity';
import { mb } from './versions.js';
import { crc32, zip } from './zip.js';
import { packageFiles, videoName } from './wallpaperEngine.js';
import { fetchable } from './proxy.js';
import { heicPicture, heicFrames, heicFile, heicJpeg } from './heic.js';
import { invoke, Channel } from '@tauri-apps/api/core';
import { APP, PLATFORM } from './desktop.js';
import { wallpaperSource } from './wallpaper.js';

export const toast = $state({ msg: '', show: false });
let timer;
export function say(msg, ms = 2400) {
  toast.msg = msg;
  toast.show = true;
  clearTimeout(timer);
  timer = setTimeout(() => (toast.show = false), ms);
}

// Downloads stream through fetch so the badge can show real progress. If the browser can't
// fetch, the next click just follows the link.
// key -> { state: 'loading'|'done', title, step (what it's doing now), p (0–1, null if unknown), got, total, ctrl }.
// The activity panel lists the loading ones with a Cancel button.
export const jobs = new SvelteMap();
const newJob = (key, title, step, p = null, total = 0) => {
  const j = $state({ state: 'loading', title, step, p, got: 0, total, ctrl: new AbortController() });
  jobs.set(key, j);
  return j;
};
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
  const j = newJob(d.i, `“${d.n}”`, 'Starting the download');
  try {
    const res = await fetch(fetchable(d.url), { signal: j.ctrl.signal });
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
      if (now - last > 120) {
        last = now;
        j.got = got;
        if (j.total) j.p = got / j.total;
        j.step = `Downloading — ${mb(got)}${j.total ? ` of ${mb(j.total)}` : ''}`;
      }
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

// In the desktop app the Rust side (src-tauri) downloads straight from the servers, no proxy or zip, into real folders.
// files(job) gives [{ name, url } | { name, data: Blob | Uint8Array | string }]; size is the expected total, for progress.
// Resolves to { path, installed }, or null when it failed or was cancelled (the toast says so).
async function appSave(key, title, dest, folder, files, size = 0) {
  const cur = jobs.get(key);
  if (cur?.state === 'loading') return void cur.ctrl.abort();
  const j = newJob(key, title, 'Starting', size ? 0 : null, size);
  const job = `${key}#${Date.now()}`;
  j.ctrl.signal.addEventListener('abort', () => invoke('cancel', { job }));
  try {
    const specs = [];
    for (const f of await files(j)) {
      if (f.url) { specs.push({ name: f.name, url: f.url }); continue; }
      const bytes = typeof f.data === 'string' ? new TextEncoder().encode(f.data)
        : f.data instanceof Blob ? new Uint8Array(await f.data.arrayBuffer()) : f.data;
      specs.push({ name: f.name, staged: await invoke('stage', bytes) });
    }
    j.ctrl.signal.throwIfAborted(); // cancelled while staging: Rust hasn't heard of the job yet
    const got = [], onProgress = new Channel();
    onProgress.onmessage = m => {
      got[m.file] = m.got;
      const sum = got.reduce((a, b) => a + (b ?? 0), 0);
      j.p = size ? Math.min(sum / size, 0.99) : m.total ? m.got / m.total : null;
      j.step = `Downloading${m.files > 1 ? ` file ${m.file + 1} of ${m.files}` : ''} — ${mb(sum)}${size ? ` of ${mb(size)}` : m.total ? ` of ${mb(m.total)}` : ''}`;
    };
    j.step = 'Saving';
    const saved = await invoke('save', { job, dest, folder, files: specs, onProgress });
    Object.assign(j, { state: 'done', p: 1 });
    setTimeout(() => jobs.get(key) === j && jobs.delete(key), 2200);
    return saved;
  } catch (err) {
    jobs.delete(key);
    say(j.ctrl.signal.aborted ? `Stopped ${title}` : `Couldn’t save ${title} — ${err?.message ?? err}`, 7000);
    return null;
  }
}

async function appDownload(key, title, folder, files, size) {
  const saved = await appSave(key, title, 'downloads', folder, async () => files, size);
  if (saved) say(`Saved to ${saved.path}`, 5000);
}

const imageName = part => `${part.t.toLowerCase()}.jpg`;

// Wallpaper Engine and portrait downloads are tracked separately from the normal download
export const weKey = d => `${d.i}:we`;
export const portraitKey = d => `${d.i}:portrait`;

// mode 'we': a Wallpaper Engine package (videos inside for aerial sets, web images for stills);
// mode 'videos' / 'portrait': the raw videos of an aerial set, zipped
async function buildPackage(d, mode) {
  const key = mode === 'we' ? weKey(d) : mode === 'portrait' ? portraitKey(d) : d.i;
  const parts = mode === 'portrait' ? d.portrait.parts : mode === 'videos' || d.we.video ? d.we.parts : [];
  const total = mode === 'portrait' ? d.portrait.size : d.size;
  const cur = jobs.get(key);
  if (cur?.state === 'loading') return cur.ctrl.abort();
  const what = mode === 'we' ? `“${d.n}” for Wallpaper Engine` : `“${d.n}” ${mode === 'portrait' ? 'portrait ' : ''}videos`;
  const j = newJob(key, what, 'Starting', 0, total);
  try {
    const videos = []; // the files that go inside the package: videos, or images taken out of Apple's HEIC
    let got = 0, last = 0;
    if (mode === 'we' && d.we.heic) {
      const jpegs = await heicFrames(d, j);
      for (const [k, blob] of jpegs.slice(0, d.we.parts.length).entries()) {
        const bytes = new Uint8Array(await blob.arrayBuffer());
        videos.push({ name: imageName(d.we.parts[k]), blob, size: bytes.length, crc: crc32(bytes) });
      }
    }
    for (const [k, part] of parts.entries()) {
      const res = await fetch(fetchable(part.u), { signal: j.ctrl.signal });
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
        if (now - last > 120) {
          last = now;
          j.got = got;
          j.p = Math.min(got / total, 0.99);
          j.step = `Downloading ${parts.length > 1 ? `video ${k + 1} of ${parts.length}` : 'the video'} — ${mb(got)} of ${mb(total)}`;
        }
      }
      videos.push({ name: videoName(part), blob: new Blob(chunks), size, crc });
    }
    j.step = 'Packing the zip';
    j.p = 0.99;
    const name = `${d.n} (${mode === 'we' ? 'Wallpaper Engine' : mode === 'portrait' ? 'portrait videos' : 'videos'})`;
    if (mode === 'we') {
      const preview = new Uint8Array(await (await fetch(d.img)).arrayBuffer());
      // HEIC images travel inside the package under their own file names
      const pkg = d.we.heic ? { ...d, we: { ...d.we, parts: d.we.parts.map(p => ({ ...p, u: imageName(p) })) } } : d;
      saveBlob(zip(packageFiles(pkg, videos, preview)), fileName(name, '.zip'));
    } else {
      saveBlob(zip(videos.map(v => ({ name: `${d.n}/${v.name}`, data: v.blob, size: v.size, crc: v.crc }))), fileName(name, '.zip'));
    }
    Object.assign(j, { state: 'done', p: 1, got });
    say(mode === 'we' ? `Saved “${name}.zip” — see the README inside to add it` : `Saved “${name}.zip”`, 6000);
    setTimeout(() => jobs.get(key) === j && jobs.delete(key), 2200);
  } catch (err) {
    jobs.delete(key);
    if (err.name === 'AbortError') return say(`Stopped building ${what}`);
    say(`Couldn’t download ${what} — try again`, 7000);
  }
}

// The app puts the package straight into Wallpaper Engine's projects folder (Downloads when it isn't installed)
async function installWallpaperEngine(d) {
  const saved = await appSave(weKey(d), `“${d.n}” for Wallpaper Engine`, 'wallpaper-engine', d.n, async j => {
    const preview = new Uint8Array(await (await fetch(d.img)).arrayBuffer());
    const media = d.we.heic ? (await heicFrames(d, j)).slice(0, d.we.parts.length).map((data, k) => ({ name: imageName(d.we.parts[k]), data }))
      : d.we.video ? d.we.parts.map(p => ({ name: videoName(p), url: p.u })) : [];
    const pkg = d.we.heic ? { ...d, we: { ...d.we, parts: d.we.parts.map(p => ({ ...p, u: imageName(p) })) } } : d;
    // the package's own folder is `folder` here
    return [...packageFiles(pkg, [], preview).map(f => ({ name: f.name.split('/').pop(), data: f.data })), ...media];
  }, d.we.video ? d.size : 0);
  if (saved) say(saved.installed ? `Installed “${d.n}” in Wallpaper Engine` : `Saved to ${saved.path} — see the README inside to add it`, 6000);
}

export function onWallpaperEngine(e, d) {
  e.preventDefault();
  if (APP) installWallpaperEngine(d);
  else buildPackage(d, 'we');
}

export function onPortrait(e, d) {
  e.preventDefault();
  if (APP) appDownload(portraitKey(d), `“${d.n}” portrait videos`, `${d.n} (portrait videos)`,
    d.portrait.parts.map(p => ({ name: videoName(p), url: p.u })), d.portrait.size);
  else buildPackage(d, 'portrait');
}

export function onDownloadClick(e, d) {
  if (APP) {
    e.preventDefault();
    if (d.kind === 'set') return appDownload(d.i, `“${d.n}” videos`, d.n, d.we.parts.map(p => ({ name: videoName(p), url: p.u })), d.size);
    // a name without an extension gets one from the server's Content-Type
    return appDownload(d.i, `“${d.n}”`, null, [{ name: fileName(d.n, d.ext || (d.how === 'zip' ? '.zip' : '')), url: d.url }], d.size);
  }
  if (d.kind === 'set') {
    e.preventDefault();
    return buildPackage(d, 'videos');
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
  const ext = (alt.u.match(/\.\w+(?=$|\?)/) || [d.ext || ''])[0];
  if (APP) {
    e.preventDefault();
    return appDownload(`${d.i}:${alt.l}`, `“${d.n}” (${alt.l})`, null, [{ name: fileName(`${d.n} (${alt.l})`, ext), url: alt.u }], alt.size);
  }
  if (d.how !== 'fetch' || fetchBroken) return say(`Downloading “${d.n}” — ${alt.l}`);
  e.preventDefault();
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

// The app only: saves the picture into the app's wallpapers folder and makes it the desktop picture
export const wallpaperKey = d => `${d.i}:wallpaper`;
export async function setWallpaper(d) {
  const src = wallpaperSource(d, PLATFORM === 'mac');
  const saved = await appSave(wallpaperKey(d), `“${d.n}” for your desktop`, 'wallpapers', null, async j =>
    src === 'heic' ? [{ name: fileName(d.n, '.heic'), data: await heicFile(d, j) }]
    : src === 'jpeg' ? [{ name: fileName(d.n, '.jpg'), data: await heicJpeg(d, j) }]
    : [{ name: fileName(d.n, src.match(/\.(jpe?g|png|heic)$/i)?.[0] ?? ''), url: src }]);
  if (!saved) return;
  try {
    await invoke('set_wallpaper', { path: saved.path });
    say(`“${d.n}” is now your wallpaper`);
  } catch (err) {
    say(`Couldn’t set the wallpaper — ${err}`, 7000);
  }
}

// The full-size picture of one of Apple's zipped HEIC wallpapers, for Quick Look; the URL is kept for the next visit
// shortcut: kept URLs (≈10 MB each) live until the page closes; fine for browsing, evict if people open hundreds
const pictures = new Map();
export const fullKey = d => `${d.i}:full`;
export function fullPicture(d) {
  if (!pictures.has(d.i)) {
    const j = newJob(fullKey(d), `“${d.n}” at full size`, 'Starting');
    const done = heicPicture(d, j).finally(() => jobs.get(fullKey(d)) === j && jobs.delete(fullKey(d)));
    pictures.set(d.i, done);
    done.catch(err => {
      pictures.delete(d.i);
      if (err.name !== 'AbortError') say(`Couldn’t load “${d.n}” at full size — showing the preview`, 5000);
    });
  }
  return pictures.get(d.i);
}
