# Builds src/data.json and public/thumbs/ from Apple's aerial manifest, the Desktop Pictures
# on this Mac, Apple's desktop-picture catalog, Basic Apple Guy extras and the Google Photos album.
# Inputs live in scripts/cache (see README). Run on a Mac: python3 scripts/build_data.py
import json, os, plistlib, re, subprocess, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
ROOT = os.path.dirname(HERE)
THUMBS = os.path.join(ROOT, 'public', 'thumbs')
os.makedirs(THUMBS, exist_ok=True)
d = json.load(open(os.path.join(CACHE, 'entries.json')))


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def thumb(src, key, width=428):
    """A small JPEG in public/thumbs, made once; returns its path relative to the site."""
    out = os.path.join(THUMBS, slug(key) + '.jpg')
    if not os.path.exists(out):
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '75', '--resampleWidth', str(width),
                        src, '--out', out], check=True, capture_output=True)
    return 'thumbs/' + os.path.basename(out)


SLICES = os.path.join(CACHE, 'slices')


def slices(key, srcs, w=428, h=268):
    """A dynamic-wallpaper thumbnail: one diagonal strip per image (light/dark, or dawn/day/dusk/night)."""
    out = os.path.join(THUMBS, slug('dyn-' + key) + '.jpg')
    if not os.path.exists(SLICES):
        subprocess.run(['swiftc', '-O', os.path.join(HERE, 'slices.swift'), '-o', SLICES], check=True)
    if not os.path.exists(out):
        subprocess.run([SLICES, out, str(w), str(h), *srcs], check=True)
    return 'thumbs/' + os.path.basename(out)


def words(key, prefix):
    s = re.sub('^' + prefix + '(Description|Cities(?=[A-Z]))?', '', key)
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)
    # keys run small words together: "SaharaandItaly", "WestAfricatotheAlps"
    return re.sub(r'(?<=[A-Za-z]{3})(and|to)(the)? ', lambda m: ' ' + m[1] + (' the ' if m[2] else ' '), s)


# ---- Aerials (Apple's idleassetsd entries.json) ------------------------------
# Thumbnails are copied locally: sylvan.apple.com's certificate isn't trusted by Chrome.
ATHUMBS = os.path.join(CACHE, 'aerial-thumbs')
os.makedirs(ATHUMBS, exist_ok=True)
INDEX = os.path.join(ATHUMBS, 'index.json')
aindex = json.load(open(INDEX)) if os.path.exists(INDEX) else {}


def aerial_thumb(url):
    src = os.path.join(ATHUMBS, aindex.setdefault(url, slug(url.rsplit('/', 1)[1]) + '.png'))
    if not os.path.exists(src):
        subprocess.run(['curl', '-sfL', '-o', src, url], check=True)
    return thumb(src, 'aerial-' + os.path.splitext(aindex[url])[0], 320)


cats, subs = [], {}
for c in sorted(d['categories'], key=lambda c: c.get('preferredOrder', 0)):
    name = words(c['localizedNameKey'], 'AerialCategory')
    cats.append(dict(id=c['id'], n=name, g='Aerials'))
    sc = c.get('subcategories', [])
    for s in sc:
        # a lone subcategory just repeats its category ("Mac", or a stray "Golden Gate Graphical" for Dynamic)
        subs[s['id']] = name if len(sc) == 1 else words(s['localizedNameKey'], 'AerialSubcategory')

# Aerials came to the Mac with Sonoma; later releases added their namesakes' sets.
AERIAL_V = {'Golden Gate': '27', 'Dynamic': '27', 'Tahoe': '26', 'Goa': '26', 'Uttarakhand': '26', 'Kerala': '26',
            'Sequoia': '15', 'Mac': '15'}
items = []
for a in d['assets']:  # file order is already grouped by category and subcategory
    sub = subs.get((a.get('subcategories') or [''])[0], '')
    name = a.get('accessibilityLabel') or a['shotID']
    if ' ' not in name and '_' in name:  # e.g. GG_A_DAY_BLUFFS_C35_V25_HFR_HEVC
        parts = name.split('_')
        name = f"{sub} {parts[2].title()}" if len(parts) > 2 else name
    v = a.get('variant') or {}
    if v:
        name += ' — ' + v.get('appearance', '').title() + (' (Portrait)' if v.get('orientation') == 'portrait' else '')
    url = a['url-4K-SDR-240FPS']
    items.append(dict(n=name, img=aerial_thumb(a['previewImage']), url=url, c=a['categories'][0], s=sub,
                      v=AERIAL_V.get(sub, '14'), kind='aerial', anim=True, video=url, ext='.mov'))

# Apple gives many shots the same label ("New York" ×4); number them so tiles are distinguishable
counts, seen = {}, {}
for x in items:
    counts[x['n']] = counts.get(x['n'], 0) + 1
for x in items:
    if counts[x['n']] > 1:
        seen[x['n']] = seen.get(x['n'], 0) + 1
        x['n'] = f"{x['n']} {seen[x['n']]}"
json.dump(aindex, open(INDEX, 'w'))

def remote_size(url):
    head = subprocess.run(['curl', '-sIL', url], capture_output=True, text=True, check=True).stdout
    return int(re.findall(r'(?im)^content-length:\s*(\d+)', head)[-1])


# Aerial sets filmed at several times of day (Tahoe Morning/Day/Evening/Night, …) become one dynamic
# wallpaper that the site packages for Wallpaper Engine; the hour each video starts playing:
START = {'Sunrise': 5, 'Morning': 6, 'Day': 10, 'Sunset': 17, 'Evening': 18, 'Night': 21}
for sub in dict.fromkeys(x['s'] for x in items):
    parts = sorted((x for x in items if x['s'] == sub and x['n'].removeprefix(sub + ' ') in START),
                   key=lambda x: START[x['n'].removeprefix(sub + ' ')])
    if len(parts) < 3:
        continue
    times = [x['n'].removeprefix(sub + ' ') for x in parts]
    first = items.index(parts[0])
    items.insert(first, dict(
        n=f'{sub} (Dynamic)', img=slices(f'{sub} wallpaper engine', [os.path.join(ROOT, 'public', x['img']) for x in parts]),
        url='', c=parts[0]['c'], s=sub, v=parts[0]['v'], kind='we', anim=True, dyn=True, video=parts[0]['url'],
        size=sum(map(remote_size, (x['url'] for x in parts))), parts=[dict(t=t, h=START[t], u=x['url']) for t, x in zip(times, parts)],
        note='One wallpaper that follows the time of day — ' + ', '.join(f'{t} from {START[t]:02}:00' for t in times)
             + '. Builds a Wallpaper Engine package from Apple’s videos; use Safari on a Mac, then copy the zip to your PC.'))

# ---- Still wallpapers ----------------------------------------------------------
# macOS lists them in /System/Library/Desktop Pictures as .madesktop stubs whose full image
# macOS downloads on demand; Apple's public MobileAsset catalog has the download for each.
# Pictures that exist only as local files can't be offered on a public site, so they're left out.
DP = '/System/Library/Desktop Pictures'
catalog = {a['DesktopPictureID']: a for a in plistlib.load(open(os.path.join(CACHE, 'catalog.xml'), 'rb'))['Assets']}
FAMILIES = ['Big Sur', 'Catalina', 'Sonoma', 'Hello Metallic', 'hello', 'iMac', 'Mac', 'Light Stream', 'Motion',
            'Radial', 'Chroma', 'Grid']
family = lambda n: next((f for f in FAMILIES if n == f or n.startswith(f + ' ')), '')
STILL_V = [(r'^Sonoma|^Hello Metallic', '14'), (r'^Ventura', '13'), (r'^iMac ', '15'),
           (r'^Radial|^Light Stream|^Grid', '13'), (r'^Monterey|^Motion|^Chroma|^Studio Color|^Pro Black', '12'),
           (r'^Big Sur|^hello |^The (Beach|Cliffs|Desert|Lake)|^(Peak|Tree|Valley|Dome|Iridescence)$', '11'),
           (r'^Catalina', '10.15'), (r'^Solar Gradients|^Mojave', '10.14')]

TIME_OF_DAY = {'Big Sur', 'Catalina', 'The Beach', 'The Cliffs', 'The Desert', 'The Lake', 'Solar Gradients'}
order = [os.path.splitext(f)[0] for f in plistlib.load(open(os.path.join(DP, '.orderedPictures.plist'), 'rb'))]
rank = lambda n: order.index(n) if n in order else len(order)
stills = []
for f in os.listdir(DP):
    base, ext = os.path.splitext(f)
    if ext not in ('.madesktop', '.heic'):
        continue
    meta = plistlib.load(open(os.path.join(DP, f), 'rb')) if ext == '.madesktop' else {}
    a = catalog.get(meta.get('mobileAssetID', base))
    if not a:
        continue
    tpath = meta.get('thumbnailPath') or os.path.join(DP, '.thumbnails', f)
    light, dark = (os.path.join(DP, '.thumbnails', f'{base} {m}.heic') for m in ('Light', 'Dark'))
    dyn = bool(meta.get('isDynamic')) or os.path.exists(dark)
    # Apple's previews for these already show diagonal time-of-day strips; the rest split light/dark down the middle
    img = slices(base, [light, dark]) if dyn and base not in TIME_OF_DAY and os.path.exists(light) else thumb(tpath, base)
    stills.append(dict(n=base, img=img, url=a['__BaseURL'] + a['__RelativePath'], c='pictures',
                       s=family(base), v=next((v for p, v in STILL_V if re.search(p, base)), 'other'), kind='still',
                       dyn=dyn, size=a['_DownloadSize'], how='zip'))

# Live wallpapers that macOS draws itself (no file to download); shown so the Dynamic list is complete
EXT = '/System/Library/ExtensionKit/Extensions'
SEQ = f'{EXT}/WallpaperSequoiaExtension.appex/Contents/Resources'
for name, img in [('Sequoia', slices('Sequoia', [f'{SEQ}/thumbnail light.heic', f'{SEQ}/thumbnail dark.heic'])),
                  ('Macintosh', thumb('/System/Library/Wallpapers/.thumbnails/Macintosh.heic', 'builtin-Macintosh'))]:
    stills.append(dict(n=name, img=img, url='', c='pictures', s='', v='15', kind='builtin',
                       dyn=True, note=f'A live wallpaper built into macOS Sequoia and later. Choose it in System Settings › Wallpaper; Apple doesn’t offer it as a file.'))

# Keep each family together, ordered the way System Settings lists them
first = {}
for x in stills:
    first[x['s'] or x['n']] = min(first.get(x['s'] or x['n'], 1e9), rank(x['n']))
stills.sort(key=lambda x: (first[x['s'] or x['n']], rank(x['n'])))  # stable: built-ins keep their listed order
items += stills
cats += [dict(id='pictures', n='Desktop Pictures', g='Pictures'), dict(id='colors', n='Colors', g='Pictures')]

# ---- Apple's own wallpapers republished by Basic Apple Guy (bag.py) -------------
EXTRA_V = {'WWDC26': '27', 'Golden Gate Adventure': '27', 'macOS Tahoe Aerials': '26', 'macOS Tahoe Lakeside': '26',
           'Apple Park': '15', 'Vision Pro': 'other'}
for x in json.load(open(os.path.join(CACHE, 'bag', 'extras.json'))):
    ext = os.path.splitext(urllib.parse.urlparse(x['url']).path)[1].lower()
    src = os.path.join(CACHE, 'bag', 'orig', os.path.basename(x['thumb']))
    tahoe = lambda *t: [os.path.join(CACHE, 'bag', 'orig', f'Tahoe{p}.png') for p in t]
    img = (slices(x['n'], tahoe('Day', 'Night')) if x['n'].startswith('Tahoe Day/Night')
           else slices(x['n'], tahoe('Dawn', 'Day', 'Dusk', 'Night')) if x['n'].startswith('Tahoe Time of Day')
           else thumb(src, 'extra-' + x['s'] + '-' + x['n']))
    items.append(dict(n=x['n'], img=img, url=x['url'], c='extras', s=x['s'],
                      v=EXTRA_V[x['s']], kind='still', dyn=x['dyn'], size=x['size'], alts=x['alts'], note=x['note'],
                      post=x['post'], how='link' if 'drive.google' in x['url'] else 'fetch', ext=ext or '.png'))
cats.append(dict(id='extras', n='Apple Extras', g='Pictures'))

# ---- The "macOS Wallpapers" Google Photos album (album.py) ----------------------
import album
items += album.entries(stills)

# Mojave's dynamic wallpaper only exists in the album as 16 frames: strip dawn, day, dusk and night together
moj = next(x for x in items if x['n'] == 'Mojave Dynamic')
frames = [moj['url']] + [a['u'] for a in moj['alts']]
srcs = []
for k in (3, 8, 12, 15):
    p = os.path.join(CACHE, 'album', f'mojave-{k}.webp')
    if not os.path.exists(p):
        subprocess.run(['curl', '-sfL', '-o', p, frames[k - 1][:-len('=d')] + '=w600'], check=True)
    srcs.append(p)
moj['img'] = slices('Mojave Dynamic', srcs)
cats.append(dict(id='archive', n='macOS Archive', g='Pictures'))

# Self-check: everything must work from a public web page
VERSIONS = {'27', '26', '15', '14', '13', '12', '11', 'other', 'classic'} | {f'10.{n}' for n in range(16)}
for x in items:
    assert x['v'] in VERSIONS, x
    assert x['url'].startswith('https://') or x['kind'] in ('builtin', 'we'), x
    assert x['img'].startswith(('https://', 'thumbs/')), x
    assert not x['img'].startswith('thumbs/') or os.path.exists(os.path.join(ROOT, 'public', x['img'])), x
assert {x['c'] for x in items} == {c['id'] for c in cats}

json.dump(dict(cats=cats, items=items), open(os.path.join(ROOT, 'src', 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
used = {os.path.basename(x['img']) for x in items if x['img'].startswith('thumbs/')}
for f in set(os.listdir(THUMBS)) - used:
    os.remove(os.path.join(THUMBS, f))
print(len(items), 'wallpapers;', len(os.listdir(THUMBS)), 'thumbnails')
