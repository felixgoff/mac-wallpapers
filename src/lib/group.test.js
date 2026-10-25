import { test } from 'node:test';
import assert from 'node:assert/strict';
import { visibleItems, groupItems } from './group.js';

const catName = c => ({ land: 'Landscapes', sea: 'Underwater', archive: 'macOS Archive' })[c];
const items = [
  { n: 'Tahoe Day', c: 'land', s: 'Tahoe', v: '26' },
  { n: 'Tahoe Night', c: 'land', s: 'Tahoe', v: '26' },
  { n: 'Seals', c: 'sea', s: 'Seals', v: '14' },
  { n: 'Kelp', c: 'sea', s: 'Kelp', v: '14' },
  { n: 'Aqua Blue', c: 'archive', s: '10.4', v: '10.4' },
  { n: 'Aurora', c: 'archive', s: '10.5', v: '10.5' },
].map((d, i) => ({ ...d, i }));

test('category view keeps places together and folds one-shot places into "More"', () => {
  const list = visibleItems(items, { cat: 'all', q: '', sortBy: 'category', catName });
  assert.deepEqual(list.map(d => d.n), ['Tahoe Day', 'Tahoe Night', 'Seals', 'Kelp', 'Aurora', 'Aqua Blue']);
  const groups = groupItems(list, { sortBy: 'category', catName });
  assert.deepEqual(groups.map(g => [g.label, g.items.length]),
    [['Tahoe', 2], ['Underwater', 2], ['Leopard', 1], ['Tiger', 1]]);
});

test('version view groups newest release first', () => {
  const list = visibleItems(items, { cat: 'all', q: '', sortBy: 'version', catName });
  const groups = groupItems(list, { sortBy: 'version', catName });
  assert.deepEqual(groups.map(g => g.label), ['macOS Tahoe 26', 'macOS Sonoma 14', 'Mac OS X Leopard 10.5', 'Mac OS X Tiger 10.4']);
});

test('Dynamic shows every light/dark wallpaper, newest release first', () => {
  const extra = [...items, { n: 'Golden Gate', c: 'dynamic-aerials', s: 'Dynamic', v: '27' },
    { n: 'Mojave', c: 'archive', s: '10.14', v: '10.14', dyn: true }, { n: 'Sonoma', c: 'land', s: 'Sonoma', v: '14', dyn: true }]
    .map((d, i) => ({ ...d, i }));
  const list = visibleItems(extra, { cat: 'dynamic-aerials', q: '', sortBy: 'category', catName: c => catName(c) ?? 'Dynamic' });
  assert.deepEqual(list.map(d => d.n), ['Golden Gate', 'Sonoma', 'Mojave']);
  assert.equal(groupItems(list, { sortBy: 'category', catName: () => 'Dynamic', cat: 'dynamic-aerials' }).length, 1);
});

test('search matches names, places and release names', () => {
  const q = query => visibleItems(items, { cat: 'all', q: query, sortBy: 'category', catName }).map(d => d.n);
  assert.deepEqual(q('night'), ['Tahoe Night']);
  assert.deepEqual(q('leopard'), ['Aurora']);
  assert.deepEqual(q('underwater'), ['Seals', 'Kelp']);
});
