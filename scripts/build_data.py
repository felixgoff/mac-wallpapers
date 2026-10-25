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


def remote_size(url):
    head = subprocess.run(['curl', '-sIL', url], capture_output=True, text=True, check=True).stdout
    return int(re.findall(r'(?im)^content-length:\s*(\d+)', head)[-1])


def luma(url, key):
    """Average brightness (0–255) of a tiny copy of an image, to tell night frames from day ones."""
    p = os.path.join(CACHE, 'luma', slug(key) + '.img')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p):
        subprocess.run(['curl', '-sfL', '--retry', '4', '--retry-all-errors', '-o', p, url], check=True)
    px = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', p, '-vf', 'scale=1:1,format=gray',
                         '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    return px[0]


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
    url = a['url-4K-SDR-240FPS']
    items.append(dict(n=name, img=aerial_thumb(a['previewImage']), url=url, c=a['categories'][0], s=sub,
                      v=AERIAL_V.get(sub, '14'), kind='aerial', anim=True, video=url, ext='.mov', variant=a.get('variant')))

# macOS Golden Gate's wallpaper comes as four videos (light/dark × landscape/portrait): make it one dynamic
# wallpaper whose Download saves the landscape pair, Portrait the portrait pair, and Wallpaper Engine follows the clock
var = {(x['variant']['appearance'], x['variant']['orientation']): x for x in items if x.get('variant')}
if var:
    first = min(items.index(x) for x in var.values())
    for x in var.values():
        items.remove(x)
    land = [var[('light', 'landscape')], var[('dark', 'landscape')]]
    port = [var[('light', 'portrait')], var[('dark', 'portrait')]]
    items.insert(first, dict(
        n='macOS Golden Gate', img=slices('macOS Golden Gate', [os.path.join(ROOT, 'public', x['img']) for x in land]),
        url='', c=land[0]['c'], s=land[0]['s'], v=land[0]['v'], kind='set', anim=True, dyn=True, video=land[0]['url'],
        size=sum(remote_size(x['url']) for x in land),
        we=dict(video=True, parts=[dict(t=t, h=h, u=x['url']) for t, h, x in zip(('Light', 'Dark'), (7, 19), land)]),
        portrait=dict(size=sum(remote_size(x['url']) for x in port), parts=[dict(t=t, u=x['url']) for t, x in zip(('Light', 'Dark'), port)]),
        note='macOS Golden Gate’s default wallpaper: light by day, dark at night. Download saves the landscape videos, Portrait the'
             ' portrait ones (best in Safari on a Mac, as Chrome doesn’t trust Apple’s video server).'))
for x in items:
    x.pop('variant', None)

# Apple gives many shots the same label ("New York" ×4); number them so tiles are distinguishable
counts, seen = {}, {}
for x in items:
    counts[x['n']] = counts.get(x['n'], 0) + 1
for x in items:
    if counts[x['n']] > 1:
        seen[x['n']] = seen.get(x['n'], 0) + 1
        x['n'] = f"{x['n']} {seen[x['n']]}"
json.dump(aindex, open(INDEX, 'w'))

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
        url='', c=parts[0]['c'], s=sub, v=parts[0]['v'], kind='set', anim=True, dyn=True, video=parts[0]['url'],
        size=sum(map(remote_size, (x['url'] for x in parts))),
        we=dict(video=True, parts=[dict(t=t, h=START[t], u=x['url']) for t, x in zip(times, parts)]),
        note='Apple’s ' + ', '.join(f'{t} from {START[t]:02}:00' for t in times)
             + ' aerials as one set. Download saves the videos; Wallpaper Engine builds one wallpaper that follows the clock'
             + ' (both need Safari on a Mac, as Chrome doesn’t trust Apple’s video server).'))

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

# Tahoe and Sequoia ship as live extensions, not files; their light and dark images come from the
# LAYTAT/macOS-Wallpapers collection on GitHub. Macintosh is drawn live and has no image to offer.
LAYTAT = 'https://raw.githubusercontent.com/LAYTAT/macOS-Wallpapers/main/'
EXT = '/System/Library/ExtensionKit/Extensions'
for name, v, light, dark, thumbs in [
        ('Tahoe', '26', '26-Tahoe-Light-6K.png', '26-Tahoe-Dark-6K.png',
         [f'{EXT}/NeptuneOneWallpaper.appex/Contents/Resources/Tahoe{m}.heic' for m in ('Light', 'Dark')]),
        ('Sequoia', '15', '15-Sequoia-Light-6K.jpg', '15-Sequoia-Dark-6K.jpg',
         [f'{EXT}/WallpaperSequoiaExtension.appex/Contents/Resources/thumbnail {m}.heic' for m in ('light', 'dark')])]:
    stills.append(dict(n=name, img=slices(name, thumbs), url=LAYTAT + light, c='pictures', s='', v=v, kind='still',
                       dyn=True, size=remote_size(LAYTAT + light), how='fetch', ext=os.path.splitext(light)[1],
                       alts=[dict(l='Dark', u=LAYTAT + dark, size=remote_size(LAYTAT + dark))],
                       note=f'macOS {name}’s default wallpaper (light; dark is an extra download), via LAYTAT/macOS-Wallpapers on GitHub.',
                       post='https://github.com/LAYTAT/macOS-Wallpapers'))
stills.append(dict(n='Macintosh', img=thumb('/System/Library/Wallpapers/.thumbnails/Macintosh.heic', 'builtin-Macintosh'),
                   url='', c='pictures', s='', v='15', kind='builtin', dyn=True,
                   note='A live wallpaper built into macOS Sequoia and later. Choose it in System Settings › Wallpaper; Apple doesn’t offer it as a file.'))

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

# ---- Wallpaper Engine frames for still dynamic wallpapers ------------------------
# The package's page loads these images from the web while it runs (Google Photos doesn't allow
# in-page downloads), switching by the clock: light/dark, or dawn/day/dusk/night.
FROM_LAYTAT = {'Sonoma': ('14-Sonoma-Light.jpg', '14-Sonoma-Dark.jpg'), 'Monterey Graphic': ('12-Light.jpg', '12-Dark.jpg'),
               'Ventura Graphic': ('13-Ventura-Light.jpg', '13-Ventura-Dark.jpg'),
               'Big Sur Graphic': ('11-0-Color-Day.jpg', '11-0-Big-Sur-Color-Night.jpg')}
TWO, FOUR = (('Day', 7), ('Night', 19)), (('Dawn', 6), ('Day', 9), ('Dusk', 17), ('Night', 20))
bag = {x['n']: x['url'] for x in items if x['c'] == 'extras'}
for x in items:
    if not x.get('dyn') or x['kind'] in ('builtin', 'set'):
        continue
    if x['n'] in FROM_LAYTAT:
        urls = [LAYTAT + f for f in FROM_LAYTAT[x['n']]]
    elif x['n'] in ('Tahoe', 'Sequoia'):
        urls = [x['url'], x['alts'][0]['u']]
    elif x['n'].startswith('Tahoe Day/Night'):
        urls = [bag['Tahoe Day'], bag['Tahoe Night']]
    elif x['n'].startswith('Tahoe Time of Day'):
        urls = [bag[f'Tahoe {t}'] for t in ('Dawn', 'Day', 'Dusk', 'Night')]
    else:  # album frames (Frame N) or light/dark copies, ordered darkest (night) to brightest (day)
        frames = [a['u'] for a in x.get('alts', []) if a['l'].startswith(('Frame', 'Light', 'Dark'))]
        if x['n'] == 'Mojave Dynamic':
            frames = [x['url']] + frames
        frames = [u[:-len('=d')] + '=s0' if u.endswith('=d') else u for u in frames]  # =s0 serves HEIC as JPEG
        if len(frames) < 2:
            continue
        frames.sort(key=lambda u: luma(u.removesuffix('=s0') + '=w32', x['n'] + u[-40:]))
        n = len(frames)
        urls = [frames[-1], frames[0]] if n < 4 else [frames[round(n * .45)], frames[-1], frames[round(n * .65)], frames[0]]
    sched = TWO if len(urls) == 2 else FOUR
    x['we'] = dict(video=False, parts=[dict(t=t, h=h, u=u) for (t, h), u in zip(sched, urls)])

# Self-check: everything must work from a public web page
VERSIONS = {'27', '26', '15', '14', '13', '12', '11', 'other', 'classic'} | {f'10.{n}' for n in range(16)}
for x in items:
    assert x['v'] in VERSIONS, x
    assert x['url'].startswith('https://') or x['kind'] in ('builtin', 'set'), x
    assert x['img'].startswith(('https://', 'thumbs/')), x
    assert not x['img'].startswith('thumbs/') or os.path.exists(os.path.join(ROOT, 'public', x['img'])), x
assert {x['c'] for x in items} == {c['id'] for c in cats}

json.dump(dict(cats=cats, items=items), open(os.path.join(ROOT, 'src', 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
used = {os.path.basename(x['img']) for x in items if x['img'].startswith('thumbs/')}
for f in set(os.listdir(THUMBS)) - used:
    os.remove(os.path.join(THUMBS, f))
print(len(items), 'wallpapers;', len(os.listdir(THUMBS)), 'thumbnails')
