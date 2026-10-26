# Turns the "macOS Wallpapers" Google Photos album (cache/album, from fetch_album.py)
# into page entries. The album runs newest macOS first, so versions come from index ranges.
import json, os, re, time

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'album')
items = json.load(open(os.path.join(HERE, 'items.json')))
info = json.load(open(os.path.join(HERE, 'info.json')))

RANGES = [(1, 1, '14'), (2, 10, '13'), (11, 25, '12'), (26, 46, '11'), (47, 50, '13'), (51, 130, '11'),
          (131, 141, '10.15'), (142, 214, '10.14'), (215, 221, '10.13'), (222, 227, '10.12'), (228, 229, '10.11'),
          (230, 235, '10.10'), (236, 245, '10.9'), (246, 301, '10.8'), (302, 321, '10.7'), (322, 357, '10.6'),
          (358, 404, '10.5'), (405, 422, '10.4'), (423, 424, '10.3'), (425, 426, '10.2'), (427, 428, '10.0'), (429, 461, '9'),  # the album files Mac OS 9's pictures under 10.0
          (462, 535, 'classic'), (536, 537, 'other'), (538, 540, '10.12'), (541, 547, '12'), (548, 548, 'other'),
          (549, 549, '10.10'), (550, 555, 'other'), (556, 556, '10.0'), (557, 557, '10.2'), (558, 558, '10.3'),
          (559, 559, '10.4'), (560, 560, '10.5'), (561, 561, '10.6'), (562, 562, '10.7'), (563, 563, '10.8'),
          (564, 589, 'other')]
# Not Apple wallpapers: the owner's donation notice (0), a fan-made "M2 MacBook Pro" render (11–12),
# third-party art (Vortex 536–537, an Imgur upload 548), Apple Watch product photos (551–555),
# plus duplicates: a low-res MacBook Air 2018 (142), low-res Color Bursts (538–540), a second Isles (312)
SKIP = {0, 11, 12, 142, 312, 536, 537, 538, 539, 540, 548, 551, 552, 553, 554, 555}
# Pictures the album files under the wrong release
VFIX = {235: '10.9', 259: '10.7', 550: 'other'}
# Copies of wallpapers already on the page: (album index, page wallpaper, label) -> extra download on it
COPIES = {6: ('grid magenta', 'Space Gray (PNG)'), 7: ('grid green', 'Silver (PNG)'), 8: ('ventura graphic', 'HEIC'),
          53: ('big sur', 'Setup Assistant (HEIC)')}

NAMES = {
    'black_unity_22_wallpaper_mac': 'Unity Lights (Black Unity 2022)', 'Appearance': 'Appearance (Big Sur)',
    'Mac': 'MacBook Pro 13-inch (2020)', 'MBA2020': 'MacBook Air (2020)', 'Desktop': 'MacBook Pro 16-inch (2019)',
    'Mac-Pro-macOS-Catalina-Wallpaper': 'Mac Pro (2019)',
    'macbook-air-2560x1440-abstract-blue-20843': 'MacBook Air 2018 Abstract', '20870': 'MacBook Air 2018 Silver',
    'macbook-air-4156x1920-abstract': 'MacBook Air 2018 Space Gray', 'macbook-air-201810-gallery4': 'MacBook Air 2018 Gold',
    'mbp-mac': 'MacBook Pro 2018', 'display_screen_large_2x': 'Threads (2018)', 'endframe-landscape': 'WWDC18',
    'IMG_7347': 'iMac Pro', '35238390255_b7955451bd_o': 'High Sierra', 'osx_hero_2x': 'Wave (Mavericks Hero)',
    '1382492466739': 'Wave', 'Wave': 'Wave (Black & White)', 'DefaultDesktop': 'Snow Leopard Aurora', 'DefaultDesktop2': 'Snow Leopard Aurora 2',
    'Aurora (Server)': 'Aurora (Server)', '1': 'MacBook Pro 2016 Burst 1', '2': 'MacBook Pro 2016 Burst 2',
    '3': 'MacBook Pro 2016 Burst 3', '12-inch-retina-macbook-Bubble-Wallpaper-iMac5K': 'MacBook 12-inch Bubbles',
    'wallpaper': 'iPad Circles Blue (2022)',
    '10-0_10.1': 'Cheetah & Puma Default', '10-2': 'Jaguar Default', '10-3': 'Panther Default', '10-4': 'Tiger Default',
    '10-5': 'Leopard Default', '10-6': 'Snow Leopard Default', '10-7': 'Lion Default', '10-8': 'Mountain Lion Default',
}


def clean(stem, pattern=False):
    if stem in NAMES:
        return NAMES[stem]
    m = re.match(r'MacBook-Pro-Event-Wallpaper-ari-weinkle-Spiral_(\w+)', stem)
    if m:
        return f'Spiral {m[1]}'
    m = re.match(r'Dh9bhs.*', stem)
    if m:
        return 'MacBook Pro 2018 (Leak)'
    m = re.match(r'Safari[-_]Background_(?:\dNE45_)?(.*?)(?:\.\d+)?$', stem)
    if m:
        return 'Safari ' + m[1].replace('Emoji_', 'Emoji ').replace('-', ' ')
    m = re.match(r'(Aerial|NatGeo|NaturePatterns|Cosmos|iMacPro)0?(\d+)$', stem)
    if m:
        label = {'NatGeo': 'National Geographic', 'NaturePatterns': 'Nature Patterns', 'iMacPro': 'iMac Pro'}.get(m[1], m[1])
        return f'{label} {m[2]}'
    stem = re.sub(r'(?<=[a-z.])(\d)$', r' \1', stem)  # "Lion2" -> "Lion 2"
    s = re.sub(r'[-_]+', ' ', stem).strip()
    return s.title() if stem.islower() else s


def norm(s):
    return re.sub(r'[\s_-]+', ' ', s.lower()).strip()


VNAME = {'14': 'Sonoma', '13': 'Ventura', '12': 'Monterey', '11': 'Big Sur', '10.15': 'Catalina', '10.14': 'Mojave',
         '10.13': 'High Sierra', '10.12': 'Sierra', '10.11': 'El Capitan', '10.10': 'Yosemite', '10.9': 'Mavericks',
         '10.8': 'Mountain Lion', '10.7': 'Lion', '10.6': 'Snow Leopard', '10.5': 'Leopard', '10.4': 'Tiger',
         '10.3': 'Panther', '10.2': 'Jaguar', '10.0': 'Cheetah', '9': 'Mac OS 9', 'classic': 'Classic', 'other': 'Other'}


def version(k, t):
    if k in VFIX:
        return VFIX[k]
    # Tiger introduced the Nature, Plants and Black & White pictures; the album lists them with Leopard,
    # whose own additions (Golden Palace, Grass Blades, …) still carry their 2007 file dates
    if 360 <= k <= 396 and time.gmtime(t / 1000).tm_year != 2007:
        return '10.4'
    return next(v for a, b, v in RANGES if a <= k <= b)


def entries(existing):
    """existing: list of page items (stills); returns new items, attaching variants/frames as alts."""
    by_name = {norm(x['n']): x for x in existing if x.get('kind') == 'still'}
    out, by_new = [], {}
    frames = {}

    def attach(parent, label, link):
        parent.setdefault('alts', []).append(dict(l=label, u=link['u'], size=link['size']))

    for k, it in enumerate(items):
        if k in SKIP:
            continue
        meta = info[it[0]]
        base = it[1][0]
        stem, ext = os.path.splitext(meta['file'])
        link = dict(u=base + '=d', size=meta['bytes'])
        if k in COPIES:
            frames.setdefault('variant:' + COPIES[k][0], []).append((COPIES[k][1], link))
            continue
        w, h = meta['w'], meta['h']
        pattern = max(w, h) <= 512

        # Frames and light/dark variants of a wallpaper become extra downloads on it
        m = (re.match(r'(.+?)-(\d+)-dragged$', stem) or re.match(r'(Appearance Dynamic)_(\d+)$', stem)
             or re.match(r'(Solar gradients) (\d+)$', stem) or re.match(r'(Mojave \(Dynamic\)) (\d+)$', stem))
        if m:
            frames.setdefault(norm(m[1].replace('-', ' ')), []).append((int(m[2]), link, k, base, w, h))
            continue
        m = re.match(r'(.+?)[ _-](light|dark)(?: mode)?$', stem, re.I) or re.match(r'(Chroma-\w+)-(Dark)$', stem)
        if m and norm(m[1].replace('-', ' ')) not in ('lines', 'solid gray'):
            parent_name = norm(m[1].replace('-', ' '))
            frames.setdefault('variant:' + parent_name, []).append((m[2].title() + ' (' + ext[1:].upper() + ')', link))
            continue
        if stem in ('Light mode JPEG', 'Dark Mode JPEG', 'Dynamic'):
            frames.setdefault('variant:catalina', []).append((stem.replace(' JPEG', '').replace('mode', 'Mode') + ' (' + ext[1:].upper() + ')', link))
            continue
        if stem.startswith('Chroma-') and ext.lower() in ('.jpeg', '.jpg'):
            frames.setdefault('variant:' + norm(stem.replace('-', ' ')), []).append(('Light (JPEG)', link))
            continue

        name = clean(stem, pattern)
        if pattern and re.fullmatch(r'\d+', stem):  # classic Mac OS desktop patterns are just numbered files
            npat = sum(1 for e in out if e.get('pattern') and e['v'] == 'classic') + 1
            name = f'Pattern {npat}'
        key = norm(name)
        ex = by_name.get(key)
        if ex and (ex['c'] != 'colors' or pattern):
            if ext.lower() not in ('.heic',) and not ex['url'].endswith(ext):
                attach(ex, ext[1:].upper() + ' version', link)
            continue  # already on the page
        if key in by_new and (by_new[key]['w'], by_new[key]['h']) == (w, h):  # same picture, another format
            attach(by_new[key], ext[1:].upper() + ' version', link)
            continue
        v = version(k, meta['t'])
        if key in by_new:  # same name in another release, e.g. Abstract 1 in Leopard and Mojave
            name = f'{name} ({VNAME[v]})'
            key = norm(name)
        e = dict(n=name, img=base + ('=s0' if pattern else '=w440'), url=link['u'], size=link['size'], c='archive',
                 s=v, v=v, kind='still', anim=False, how='link', pattern=pattern, alts=[], w=w, h=h,
                 note='From the “macOS Wallpapers” Google Photos album')
        if k >= 564:  # the album ends with macOS's solid colours
            e.update(c='colors', s='', v='other')
        if ext.lower() == '.heic' and 'dynamic' in name.lower():
            e['dyn'] = True
        out.append(e)
        by_new[key] = e
        by_new.setdefault(norm(stem), e)  # findable by its file name too ("Appearance_Light")

    def find(key):
        return by_new.get(key) or by_name.get(key)

    for key, lst in frames.items():
        if key.startswith('variant:'):
            parent = find(key[8:]) or find(key[8:] + ' graphic')
            for label, link in lst:
                if parent:
                    attach(parent, label, link)
            continue
        parent = find({'appearance dynamic': 'big sur'}.get(key, key))  # the Setup Assistant copy of Big Sur
        lst.sort(key=lambda f: f[0])
        if not parent and key == norm('Mojave (Dynamic)'):  # the album only has Mojave's 16 frames
            n, link, k, base, w, h = lst[0]
            parent = dict(n='Mojave Dynamic', img=base + '=w440', url=link['u'], size=link['size'], c='archive', s='10.14',
                          v='10.14', kind='still', anim=False, how='link', dyn=True, alts=[], w=w, h=h,
                          note='Mojave’s dynamic wallpaper as its 16 time-of-day frames (HEIC)')
            out.append(parent)
            by_new[norm('Mojave Dynamic')] = parent
            lst = lst[1:]
            for n, link, *_ in lst:
                attach(parent, f'Frame {n}', link)
            continue
        if not parent:
            parent = by_name.get(norm('Solar Gradients')) if 'solar' in key else None
        for n, link, *_ in lst:
            if parent:
                attach(parent, f'Frame {n}', link)
    return out
