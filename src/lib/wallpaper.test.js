import { test } from 'node:test';
import assert from 'node:assert/strict';
import { wallpaperSource } from './wallpaper.js';

test('Set as Wallpaper keeps HEIC on a Mac and turns it into JPEG elsewhere', () => {
  const zipped = { how: 'zip', url: 'https://updates.cdn-apple.com/a.zip' };
  const heic = { how: 'fetch', url: 'https://x.com/goa.heic', full: 'https://x.com/goa.heic' };
  const light = { how: 'zip', url: 'https://updates.cdn-apple.com/b.zip', full: 'https://raw.githubusercontent.com/l.jpg' };
  assert.equal(wallpaperSource(zipped, true), 'heic');
  assert.equal(wallpaperSource(zipped, false), 'jpeg');
  assert.equal(wallpaperSource(heic, true), heic.url);
  assert.equal(wallpaperSource(heic, false), 'jpeg');
  assert.equal(wallpaperSource(light, false), light.full);
});
