// A minimal ZIP writer: files are stored uncompressed (videos don't compress anyway), so large
// files can be added as Blobs without copying them. shortcut: no ZIP64, so the archive must stay
// under 4 GB; switch to ZIP64 records if a package ever gets bigger.

const TABLE = new Uint32Array(256).map((_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

// CRC-32 that can be fed chunk by chunk: crc32(next, crc32(first))
export function crc32(bytes, crc = 0) {
  let c = ~crc;
  for (let i = 0; i < bytes.length; i++) c = TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return ~c >>> 0;
}

// files: [{ name, data: Blob | Uint8Array | string, size, crc }] — size and crc are worked out for strings and Uint8Arrays
export function zip(files) {
  const enc = new TextEncoder(), parts = [], central = [];
  let offset = 0;
  for (const f of files) {
    const data = typeof f.data === 'string' ? enc.encode(f.data) : f.data;
    const size = f.size ?? data.length, crc = f.crc ?? crc32(data), name = enc.encode(f.name);
    const header = (sig, extra) => {
      const b = new DataView(new ArrayBuffer(extra + name.length));
      b.setUint32(0, sig, true);
      return b;
    };
    const local = header(0x04034b50, 30);
    local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true); // version 2.0, UTF-8 names, stored
    local.setUint32(14, crc, true); local.setUint32(18, size, true); local.setUint32(22, size, true);
    local.setUint16(26, name.length, true);
    new Uint8Array(local.buffer).set(name, 30);
    const entry = header(0x02014b50, 46);
    entry.setUint16(4, 20, true); entry.setUint16(6, 20, true); entry.setUint16(8, 0x0800, true);
    entry.setUint32(16, crc, true); entry.setUint32(20, size, true); entry.setUint32(24, size, true);
    entry.setUint16(28, name.length, true); entry.setUint32(42, offset, true);
    new Uint8Array(entry.buffer).set(name, 46);
    parts.push(local, data);
    central.push(entry);
    offset += 30 + name.length + size;
  }
  const cdSize = central.reduce((n, e) => n + e.byteLength, 0);
  if (offset + cdSize >= 2 ** 32) throw new Error('ZIP is over 4 GB');
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  return new Blob([...parts, ...central, end], { type: 'application/zip' });
}

// The first file in a zip whose name passes test, as a Blob (Apple's catalog zips store the HEIC uncompressed;
// deflated entries are inflated). Reads the central directory, as local headers may leave sizes out.
export async function unzipFile(buf, test) {
  const v = new DataView(buf);
  let e = buf.byteLength - 22;
  while (e >= 0 && v.getUint32(e, true) !== 0x06054b50) e--;
  if (e < 0) throw new Error('not a zip file');
  for (let p = v.getUint32(e + 16, true), k = v.getUint16(e + 10, true); k > 0; k--) {
    const method = v.getUint16(p + 10, true), size = v.getUint32(p + 20, true), at = v.getUint32(p + 42, true);
    const nl = v.getUint16(p + 28, true), name = new TextDecoder().decode(new Uint8Array(buf, p + 46, nl));
    if (test(name)) {
      const data = new Blob([new Uint8Array(buf, at + 30 + v.getUint16(at + 26, true) + v.getUint16(at + 28, true), size)]);
      if (method === 0) return data;
      if (method === 8) return new Response(data.stream().pipeThrough(new DecompressionStream('deflate-raw'))).blob();
      throw new Error(`unsupported zip compression ${method}`);
    }
    p += 46 + nl + v.getUint16(p + 30, true) + v.getUint16(p + 32, true);
  }
  throw new Error('file not found in the zip');
}
