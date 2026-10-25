// Runs after `vite build`: one tiny page per wallpaper (dist/w/<id>/index.html) whose title and picture show up
// when the link is pasted into a chat or a post, and which sends the visitor on to the gallery's …/#<id>.
import fs from 'node:fs';
import { slugs } from '../src/lib/group.js';

const SITE = 'https://felixgoff.github.io/mac-wallpapers/';
const { items } = JSON.parse(fs.readFileSync(new URL('../src/data.json', import.meta.url)));
const esc = s => s.replace(/[&<>"]/g, c => `&#${c.charCodeAt(0)};`);
const ids = slugs(items.map(d => d.n));

items.forEach((d, k) => {
  const id = ids[k], title = esc(`${d.n} — Mac Wallpapers`), img = esc(new URL(d.img, SITE).href);
  const about = esc(d.note ?? 'A Mac wallpaper — preview and download it free.');
  fs.mkdirSync(`dist/w/${id}`, { recursive: true });
  fs.writeFileSync(`dist/w/${id}/index.html`, `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>${title}</title>
<meta name="description" content="${about}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Mac Wallpapers">
<meta property="og:title" content="${title}">
<meta property="og:description" content="${about}">
<meta property="og:image" content="${img}">
<meta property="og:url" content="${SITE}w/${id}/">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="${SITE}#${id}">
<meta http-equiv="refresh" content="0; url=../../#${id}">
</head><body><a href="../../#${id}">${esc(d.n)}</a></body></html>
`);
});
console.log(`share pages: ${items.length} in dist/w/`);
