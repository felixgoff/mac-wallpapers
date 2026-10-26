// Apple's catalog wallpapers only come as zipped HEIC files, which most browsers can't show: fetch the zip
// through the proxy, take out the HEIC and decode it (Safari natively; elsewhere with libheif, ~2 MB, loaded on first use).
// job: { step, p, ctrl } from downloads.svelte.js, updated as it goes so the activity panel can show it.
import { unzipFile } from './zip.js';
import { fetchable } from './proxy.js';
import { mb } from './versions.js';

let libheif;
const aborted = () => new DOMException('Cancelled', 'AbortError');

// Apple's original HEIC file of the wallpaper, as a Blob (out of the zip, for Apple's catalog)
export async function heicFile(d, job) {
  const res = await fetch(fetchable(d.url), { signal: job.ctrl.signal });
  if (!res.ok || !res.body) throw new Error('HTTP ' + res.status);
  const total = +res.headers.get('content-length') || d.size || 0, reader = res.body.getReader(), chunks = [];
  let got = 0, last = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.length;
    const now = performance.now();
    if (now - last > 120) {
      last = now;
      job.step = `Downloading Apple’s original — ${mb(got)}${total ? ` of ${mb(total)}` : ''}`;
      job.p = total ? (got / total) * 0.6 : null; // downloading is most of the wait
    }
  }
  if (d.how !== 'zip') return new Blob(chunks);
  job.step = 'Unzipping';
  return unzipFile(await new Blob(chunks).arrayBuffer(), n => n.toLowerCase().endsWith('.heic'));
}

// The first `count` images in the HEIC (all by default) as ImageData
async function decode(heic, job, count = Infinity) {
  job.step = 'Loading the HEIC decoder';
  job.p = 0.6;
  libheif ??= import('libheif-js/libheif-wasm/libheif-bundle.mjs').then(m => m.default());
  const images = new (await libheif).HeifDecoder().decode(new Uint8Array(await heic.arrayBuffer()));
  if (!images.length) throw new Error('no image in the HEIC file');
  const n = Math.min(count, images.length), out = [];
  try {
    for (let i = 0; i < n; i++) {
      if (job.ctrl.signal.aborted) throw aborted();
      job.step = n > 1 ? `Decoding image ${i + 1} of ${n}` : 'Decoding the image';
      job.p = 0.6 + (0.35 * i) / n;
      await new Promise(r => setTimeout(r, 30)); // let the panel show the step before decoding blocks the page
      const img = images[i], width = img.get_width(), height = img.get_height();
      const data = await new Promise((res, rej) => img.display({ data: new Uint8ClampedArray(width * height * 4), width, height },
        d => (d ? res(d) : rej(new Error('couldn’t decode the HEIC image')))));
      out.push(new ImageData(data.data, width, height));
    }
  } finally {
    images.forEach(img => img.free());
  }
  return out;
}

function toJpeg(img) {
  const c = new OffscreenCanvas(img.width, img.height);
  c.getContext('2d').putImageData(img, 0, 0);
  return c.convertToBlob({ type: 'image/jpeg', quality: 0.92 });
}

// Average brightness from a sample of pixels, to tell the night image from the day one
function luma({ data }) {
  let sum = 0, n = 0;
  for (let i = 0; i < data.length; i += 4 * 997, n++) sum += data[i] * 0.3 + data[i + 1] * 0.59 + data[i + 2] * 0.11;
  return sum / n;
}

// A URL an <img> can show for the wallpaper's full-size picture
export async function heicPicture(d, job) {
  const heic = await heicFile(d, job);
  const url = URL.createObjectURL(heic);
  try { // Safari shows HEIC itself
    const img = new Image();
    img.src = url;
    await img.decode();
    return url;
  } catch {
    URL.revokeObjectURL(url);
  }
  const [img] = await decode(heic, job, 1);
  job.step = 'Preparing the picture';
  return URL.createObjectURL(await toJpeg(img));
}

// The picture Quick Look shows, as a JPEG: for desktops that can't use HEIC
export async function heicJpeg(d, job) {
  const [img] = await decode(await heicFile(d, job), job, 1);
  job.step = 'Converting to JPEG';
  return toJpeg(img);
}

// Every image in the HEIC as a JPEG, brightest (day) first
export async function heicFrames(d, job) {
  const frames = await decode(await heicFile(d, job), job);
  frames.sort((a, b) => luma(b) - luma(a));
  job.step = 'Converting to JPEG';
  const out = [];
  for (const f of frames) out.push(await toJpeg(f)); // one at a time: each 6K image is ~150 MB in memory
  return out;
}
