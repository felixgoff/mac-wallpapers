# Mac OS 8.5–9's default desktop pattern, which only exists inside the Appearance theme file
# "Apple platinum": each theme ('scen' resource) carries its desktop pattern as a colour pattern (PixPat).
# Input: cache/Theme Files/Apple platinum — from Mac OS 9.2.2's Theme_Files.sit on Macintosh Repository
# (https://www.macintoshrepository.org/16554), unpacked with `unar -o scripts/cache Theme_Files.sit`.
import os, struct, zlib

THEMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'Theme Files', 'Apple platinum')
# unar puts the resource fork in the file's own fork on a Mac, and in a .rsrc file next to it elsewhere
FORK = THEMES + '.rsrc' if os.path.exists(THEMES + '.rsrc') else os.path.join(THEMES, '..namedfork', 'rsrc')


def resources(b):
    """{(type, id): (name, data)} from a resource fork, or an AppleDouble file holding one (as unar writes them)."""
    if b[:4] == b'\x00\x05\x16\x07':
        for i in range(struct.unpack('>H', b[24:26])[0]):
            eid, off, ln = struct.unpack('>3I', b[26 + 12 * i:38 + 12 * i])
            if eid == 2:
                b = b[off:off + ln]
    doff, moff, _, mlen = struct.unpack('>4I', b[:16])
    m = b[moff:moff + mlen]
    tl_off, nl_off = struct.unpack('>HH', m[24:28])
    tl, out = m[tl_off:], {}
    for i in range(struct.unpack('>H', tl[:2])[0] + 1):
        typ, cnt, ref = struct.unpack('>4sHH', tl[2 + 8 * i:10 + 8 * i])
        for j in range(cnt + 1):
            rid, noff, attr_off = struct.unpack('>hHI', tl[ref + 12 * j:ref + 12 * j + 8])
            name = '' if noff == 0xFFFF else m[nl_off + noff + 1:nl_off + noff + 1 + m[nl_off + noff]].decode('mac_roman')
            at = doff + (attr_off & 0xFFFFFF)
            out[typ.decode('mac_roman'), rid] = name, b[at + 4:at + 4 + struct.unpack('>I', b[at:at + 4])[0]]
    return out


def pixpat(d):
    """A colour PixPat (indexed pixels and their colour table) as PNG bytes; its offsets count from its start."""
    pat_type, pmap, pdata = struct.unpack('>HII', d[:10])
    assert pat_type == 1, 'not a colour pattern'
    row_bytes, top, left, bottom, right = struct.unpack('>H4h', d[pmap + 4:pmap + 14])
    row_bytes &= 0x3FFF
    depth = struct.unpack('>H', d[pmap + 32:pmap + 34])[0]
    ct = struct.unpack('>I', d[pmap + 42:pmap + 46])[0]
    colors = {}
    for k in range(struct.unpack('>H', d[ct + 6:ct + 8])[0] + 1):
        v, r, g, b = struct.unpack('>4H', d[ct + 8 + 8 * k:ct + 16 + 8 * k])
        colors[k if d[ct + 4] & 0x80 else v] = (r >> 8, g >> 8, b >> 8)  # device tables index by position
    w, h = right - left, bottom - top
    rows = b''
    for y in range(h):
        row = d[pdata + y * row_bytes:pdata + (y + 1) * row_bytes]
        rows += b'\0' + b''.join(bytes(colors[(row[x * depth // 8] >> (8 - depth - x * depth % 8)) & ((1 << depth) - 1)])
                                 for x in range(w))
    chunk = lambda t, c: struct.pack('>I', len(c)) + t + c + struct.pack('>I', zlib.crc32(t + c))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def pattern(theme, out):
    """Saves the desktop pattern of the theme named `theme` as a PNG at `out`."""
    scen = next(d for (t, _), (n, d) in resources(open(FORK, 'rb').read()).items() if t == 'scen' and n == theme)
    # the PixPat sits inside the theme's flattened collection; it starts with type 1 and a PixMap at offset 28
    open(out, 'wb').write(pixpat(scen[scen.index(b'\x00\x01\x00\x00\x00\x1c'):]))
