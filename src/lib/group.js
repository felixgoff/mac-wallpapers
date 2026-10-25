import { VLABEL, VORDER, section } from './versions.js';

// The wallpapers shown for a category and search, in display order
export function visibleItems(items, { cat, q, sortBy, catName }) {
  q = q.trim().toLowerCase();
  const list = items.filter(d => (cat === 'all' || d.c === cat) &&
    (!q || `${d.n} ${section(d)} ${catName(d.c)} ${VLABEL[d.v]}`.toLowerCase().includes(q)));
  // Archive items sort by release even when grouping by category (they come last in the data)
  return list.sort((a, b) => sortBy === 'version' || (a.c === 'archive' && b.c === 'archive')
    ? VORDER[a.v] - VORDER[b.v] || a.i - b.i
    : a.i - b.i);
}

// Sections for the grid: one per macOS release, or per category and place
export function groupItems(list, { sortBy, catName }) {
  const groups = [];
  if (sortBy === 'version') {
    for (const d of list) {
      if (groups.at(-1)?.v !== d.v) groups.push({ key: d.v, v: d.v, label: VLABEL[d.v], items: [] });
      groups.at(-1).items.push(d);
    }
    return groups;
  }
  for (const d of list) {
    const s = section(d), last = groups.at(-1);
    if (!last || last.c !== d.c || last.s !== s) groups.push({ c: d.c, s, items: [] });
    groups.at(-1).items.push(d);
  }
  // One-shot places (common in Underwater and Space) collect into a single
  // "More …" section at the end of their category instead of a header each
  const merged = [];
  for (const c of new Set(groups.map(g => g.c))) {
    const run = groups.filter(g => g.c === c);
    const loose = g => c !== 'archive' && (g.items.length === 1 || !g.s);
    const singles = run.filter(loose);
    if (singles.length < 2) { merged.push(...run); continue; }
    const rest = run.filter(g => !loose(g));
    merged.push(...rest, { c, s: '', more: rest.length > 0, items: singles.flatMap(g => g.items) });
  }
  return merged.map((g, k) => {
    const label = g.s || (g.more && merged.length > 1 ? `More ${catName(g.c)}` : catName(g.c));
    return { ...g, key: `${k}:${g.c}:${label}`, label };
  });
}
