import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { crc32, zip, unzipFile } from './zip.js';

test('crc32 matches the standard check value, also when fed in chunks', () => {
  const bytes = new TextEncoder().encode('123456789');
  assert.equal(crc32(bytes), 0xcbf43926);
  assert.equal(crc32(bytes.subarray(4), crc32(bytes.subarray(0, 4))), 0xcbf43926);
});

test('zip produces an archive unzip accepts, with Blob and text entries', async () => {
  const video = new Uint8Array(70000).map((_, i) => i % 251);
  const blob = await zip([
    { name: 'Tahoe (Dynamic)/project.json', data: '{"type":"web"}' },
    { name: 'Tahoe (Dynamic)/day.mov', data: new Blob([video]), size: video.length, crc: crc32(video) },
  ]).arrayBuffer();
  const dir = mkdtempSync(join(tmpdir(), 'zip-'));
  writeFileSync(join(dir, 'a.zip'), Buffer.from(blob));
  execFileSync('unzip', ['-tq', 'a.zip'], { cwd: dir }); // throws if the archive is broken
  execFileSync('unzip', ['-q', 'a.zip'], { cwd: dir });
  assert.deepEqual(new Uint8Array(readFileSync(join(dir, 'Tahoe (Dynamic)/day.mov'))), video);
  assert.equal(readFileSync(join(dir, 'Tahoe (Dynamic)/project.json'), 'utf8'), '{"type":"web"}');
});

test('unzipFile takes a stored file out of a zip, and inflates a deflated one', async () => {
  const heic = new Uint8Array(5000).map((_, i) => i % 7);
  const stored = await zip([{ name: 'META-INF/', data: '' }, { name: 'AssetData/Grid Green.heic', data: heic }]).arrayBuffer();
  const out = await unzipFile(stored, n => n.endsWith('.heic'));
  assert.deepEqual(new Uint8Array(await out.arrayBuffer()), heic);
  const dir = mkdtempSync(join(tmpdir(), 'unzip-'));
  writeFileSync(join(dir, 'a.txt'), 'hello hello hello hello');
  execFileSync('zip', ['-q', 'b.zip', 'a.txt'], { cwd: dir }); // deflates by default
  const b = readFileSync(join(dir, 'b.zip'));
  const txt = await unzipFile(b.buffer.slice(b.byteOffset, b.byteOffset + b.length), n => n === 'a.txt');
  assert.equal(await txt.text(), 'hello hello hello hello');
  await assert.rejects(unzipFile(stored, n => n === 'nope'));
});
