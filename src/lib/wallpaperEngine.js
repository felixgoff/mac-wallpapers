// A Wallpaper Engine "web" wallpaper: a page that shows the picture or video for the time of day and
// crossfades to the next one on schedule. Videos travel inside the package (Wallpaper Engine's browser
// can't reach Apple's video server); still images load from the web while the wallpaper runs.
// videos: [{ name, blob, size, crc }] (empty for stills); preview: JPEG bytes.
import { mb } from './versions.js';

export const videoName = part => `${part.t.toLowerCase()}.mp4`; // Apple's .mov files are MP4-compatible

// Copies this folder into Wallpaper Engine's projects\myprojects, finding Wallpaper Engine in any Steam library
const installer = dir => `@echo off
setlocal
set "SRC=%~dp0"
set "STEAM="
for /f "tokens=2,*" %%a in ('reg query "HKCU\\Software\\Valve\\Steam" /v SteamPath 2^>nul ^| find "SteamPath"') do set "STEAM=%%b"
set "STEAM=%STEAM:/=\\%"
set "WE="
if exist "%STEAM%\\steamapps\\common\\wallpaper_engine" set "WE=%STEAM%\\steamapps\\common\\wallpaper_engine"
if not defined WE for /f "tokens=1,*" %%p in ('findstr /c:"\\"path\\"" "%STEAM%\\steamapps\\libraryfolders.vdf" 2^>nul') do (
  if exist "%%~q\\steamapps\\common\\wallpaper_engine" set "WE=%%~q\\steamapps\\common\\wallpaper_engine"
)
if not defined WE (
  echo Couldn't find Wallpaper Engine. Move this folder into
  echo   ...\\steamapps\\common\\wallpaper_engine\\projects\\myprojects
  echo by hand, as the README explains.
  pause
  exit /b 1
)
set "DEST=%WE%\\projects\\myprojects\\${dir}"
echo Installing to %DEST%
robocopy "%SRC%." "%DEST%" /E /XF "Install to Wallpaper Engine.bat" /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
  echo Copying failed.
  pause
  exit /b 1
)
echo Done. Open Wallpaper Engine: "${dir}" is under Installed.
pause
`.replace(/\n/g, '\r\n'); // Windows batch files want CRLF line endings

export function packageFiles(d, videos, preview) {
  const { video, parts } = d.we;
  const dir = d.n.replace(/[/\\:*?"<>|]/g, '-');
  const schedule = parts.map(p => `${p.t} from ${String(p.h).padStart(2, '0')}:00`).join(', ');
  const tag = video ? 'video' : 'img';
  const el = video ? '<video muted loop playsinline></video>' : '<img alt="">';
  const html = `<!doctype html>
<meta charset="utf-8">
<title>${d.n}</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
  ${tag} { position: fixed; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 4s ease; }
  ${tag}.on { opacity: 1; }
</style>
${el}
${el}
<script>
  // [source, hour it starts] — ${schedule}
  const PARTS = ${JSON.stringify(parts.map(p => [video ? videoName(p) : p.u, p.h]))};
  const els = document.querySelectorAll('${tag}');
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
    const next = els[1 - front], prev = els[front];
    next.${video ? 'oncanplay' : 'onload'} = () => {
      next.${video ? 'oncanplay' : 'onload'} = null;
      next.classList.add('on');
      prev.classList.remove('on');
      front = 1 - front;
      // after the crossfade, unload the old one unless it now shows (or is loading) the current part
      setTimeout(() => { if (+prev.dataset.part !== current) { ${video ? 'prev.pause(); prev.removeAttribute(\'src\'); prev.load();' : 'prev.removeAttribute(\'src\');'} } }, 4500);
    };
    next.dataset.part = k;
    next.src = PARTS[k][0];${video ? '\n    next.play().catch(() => {});' : ''}
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
    description: `Apple's ${d.n} as a wallpaper that follows the time of day: ${schedule}.`,
    tags: [video ? 'Landscape' : 'Abstract'],
  };
  const media = video
    ? `The videos are Apple's 4K HEVC aerials (${mb(d.size)} in total). If the wallpaper stays black, Windows
can't decode HEVC on your PC; installing Microsoft's "HEVC Video Extensions" usually fixes that.`
    : `The pictures load from the web while the wallpaper runs (Google Photos, GitHub or Basic Apple Guy),
so the PC needs an internet connection, at least the first time each one shows.`;
  const readme = `${d.n} — a dynamic wallpaper for Wallpaper Engine

Shows Apple's ${d.n} by time of day: ${schedule}.

To add it:
1. Unzip this file (right-click > Extract All).
2. Double-click "Install to Wallpaper Engine.bat" inside the "${dir}" folder. Done: open Wallpaper Engine,
   "${d.n}" is under Installed. (If Windows warns about the file, choose More info > Run anyway.)

Or by hand: move the "${dir}" folder into Wallpaper Engine's projects folder:
   C:\\Program Files (x86)\\Steam\\steamapps\\common\\wallpaper_engine\\projects\\myprojects
   (create the "myprojects" folder if it isn't there yet).
then open Wallpaper Engine; "${d.n}" appears under Installed.

${media}

Wallpapers © Apple Inc. For personal use. Made with https://felixgoff.github.io/mac-wallpapers/
`;
  return [
    { name: `${dir}/project.json`, data: JSON.stringify(project, null, 2) },
    { name: `${dir}/index.html`, data: html },
    { name: `${dir}/README.txt`, data: readme },
    { name: `${dir}/preview.jpg`, data: preview },
    { name: `${dir}/Install to Wallpaper Engine.bat`, data: installer(dir) },
    ...videos.map(v => ({ name: `${dir}/${v.name}`, data: v.blob, size: v.size, crc: v.crc })),
  ];
}
