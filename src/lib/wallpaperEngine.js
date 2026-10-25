// A Wallpaper Engine "web" wallpaper: a page that plays the aerial filmed closest to the time of day
// and crossfades to the next one on schedule. videos: [{ name, blob, size, crc }]; preview: JPEG bytes.
import { mb } from './versions.js';

export const videoName = part => `${part.t.toLowerCase()}.mp4`; // Apple's .mov files are MP4-compatible

export function packageFiles(d, videos, preview) {
  const dir = d.n.replace(/[/\\:*?"<>|]/g, '-');
  const schedule = d.parts.map(p => `${p.t} from ${String(p.h).padStart(2, '0')}:00`).join(', ');
  const html = `<!doctype html>
<meta charset="utf-8">
<title>${d.n}</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
  video { position: fixed; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 4s ease; }
  video.on { opacity: 1; }
</style>
<video muted loop playsinline></video>
<video muted loop playsinline></video>
<script>
  // [file, hour it starts] — ${schedule}
  const PARTS = ${JSON.stringify(d.parts.map(p => [videoName(p), p.h]))};
  const vids = document.querySelectorAll('video');
  let current = -1, front = 0;

  function partNow() {
    const now = new Date(), h = now.getHours() + now.getMinutes() / 60;
    let k = PARTS.length - 1; // before the first start it's still the last part (night)
    PARTS.forEach(([, start], i) => { if (h >= start) k = i; });
    return k;
  }

  function update() {
    const k = partNow();
    if (k === current) return;
    current = k;
    const next = vids[1 - front], prev = vids[front];
    next.src = PARTS[k][0];
    next.oncanplay = () => {
      next.oncanplay = null;
      next.classList.add('on');
      prev.classList.remove('on');
      front = 1 - front;
      // after the crossfade, unload the old video unless it has become the current one again
      setTimeout(() => { if (prev !== vids[front]) { prev.pause(); prev.removeAttribute('src'); prev.load(); } }, 4500);
    };
    next.play().catch(() => {});
  }

  update();
  setInterval(update, 30000);
</script>
`;
  const project = {
    title: d.n,
    type: 'web',
    file: 'index.html',
    preview: 'preview.jpg',
    description: `Apple's macOS aerials as one wallpaper that follows the time of day: ${schedule}.`,
    tags: ['Landscape'],
  };
  const readme = `${d.n} — a dynamic wallpaper for Wallpaper Engine

Plays Apple's macOS aerial videos by time of day: ${schedule}.

To add it:
1. Unzip this file.
2. Move the "${dir}" folder into Wallpaper Engine's projects folder:
   C:\\Program Files (x86)\\Steam\\steamapps\\common\\wallpaper_engine\\projects\\myprojects
   (create the "myprojects" folder if it isn't there yet).
3. Open Wallpaper Engine; "${d.n}" appears under Installed.

The videos are Apple's 4K HEVC aerials (${mb(d.size)} in total). If the wallpaper stays black, Windows
can't decode HEVC on your PC; installing Microsoft's "HEVC Video Extensions" usually fixes that.

Videos © Apple Inc. For personal use. Made with https://felixgoff.github.io/mac-wallpapers/
`;
  return [
    { name: `${dir}/project.json`, data: JSON.stringify(project, null, 2) },
    { name: `${dir}/index.html`, data: html },
    { name: `${dir}/README.txt`, data: readme },
    { name: `${dir}/preview.jpg`, data: preview },
    ...videos.map(v => ({ name: `${dir}/${v.name}`, data: v.blob, size: v.size, crc: v.crc })),
  ];
}
