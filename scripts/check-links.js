// Checks every outside link in src/data.json (downloads, videos, images, sources) and fails if any is dead.
// Run weekly by .github/workflows/check-links.yml; `node scripts/check-links.js` runs it locally.
import fs from 'node:fs';

const { items } = JSON.parse(fs.readFileSync(new URL('../src/data.json', import.meta.url)));
const urls = [...new Set(items.flatMap(d => [d.url, d.video, d.img, d.post, ...(d.alts ?? []).map(a => a.u),
  ...(d.we?.parts ?? []).map(p => p.u), ...(d.workshop ?? []).map(w => w.u)]).filter(u => u?.startsWith('https://')))];

async function check(u) {
  for (let attempt = 0; ; attempt++) {
    try {
      // the first byte only: many links are multi-GB videos
      const r = await fetch(u, { headers: { Range: 'bytes=0-0' }, signal: AbortSignal.timeout(30000) });
      await r.body?.cancel();
      if (r.ok || attempt === 2) return r.ok ? null : `${r.status} ${u}`;
    } catch (e) {
      if (attempt === 2) return `${e.cause?.code ?? e.name} ${u}`;
    }
  }
}

const dead = [], queue = [...urls];
await Promise.all(Array.from({ length: 8 }, async () => {
  while (queue.length) { const bad = await check(queue.pop()); if (bad) dead.push(bad); }
}));
console.log(`${urls.length} links checked, ${dead.length} dead`);
dead.sort().forEach(x => console.log('  ' + x));
process.exit(dead.length ? 1 : 0);
