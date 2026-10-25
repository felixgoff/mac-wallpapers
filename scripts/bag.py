# Collects Apple's official wallpapers that Basic Apple Guy republishes, into cache/bag/extras.json.
# Resolves basicappleguy.com/s/... links to their final static1.squarespace.com address
# (which allows in-page fetches) and caches a small source image per wallpaper for thumbnails.
import json, os, re, time, urllib.request, urllib.parse

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'bag')
ORIG = os.path.join(HERE, 'orig')
os.makedirs(ORIG, exist_ok=True)
SITE = 'https://basicappleguy.com'
UA = {'User-Agent': 'Mozilla/5.0'}
POSTS = os.path.join(HERE, 'posts.json')
if not os.path.exists(POSTS):  # every post in the Wallpaper category, via Squarespace's JSON view
    allp, url = [], '/?category=Wallpaper'
    while url:
        page = json.load(urllib.request.urlopen(urllib.request.Request(SITE + url + '&format=json', headers=UA), timeout=60))
        allp += [{k: x.get(k) for k in ('title', 'urlId', 'fullUrl', 'tags', 'publishOn', 'excerpt', 'assetUrl', 'body')}
                 for x in page['items']]
        p = page.get('pagination') or {}
        url = p.get('nextPageUrl') if p.get('nextPage') else None
        time.sleep(0.4)
    json.dump(allp, open(POSTS, 'w'))
posts = {p['title']: p for p in json.load(open(POSTS))}


def resolve(href):
    """Final URL and size for a download link."""
    url = urllib.parse.urljoin(SITE, href)
    req = urllib.request.Request(url, method='HEAD', headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.url, int(r.headers.get('Content-Length') or 0)


def fetch(url, name):
    """Cache a file locally (for making thumbnails)."""
    out = os.path.join(ORIG, name)
    if not os.path.exists(out):
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(out, 'wb') as f:
            f.write(r.read())
    return out


def links(title):
    return [(re.sub('<[^>]+>', '', t).strip(), h) for h, t in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', posts[title]['body'], re.S)
            if h.startswith('/s/') or 'drive.google.com' in h]


def imgs(title):
    return list(dict.fromkeys(re.findall(r'data-src="([^"]+)"', posts[title]['body'])))


def post_url(title):
    return SITE + posts[title]['fullUrl']


out = []


def add(n, s, url, size, thumb_src, title, note, alts=(), dyn=False):
    out.append(dict(n=n, s=s, url=url, size=size, thumb=thumb_src, alts=list(alts), dyn=dyn, note=note, post=post_url(title)))


def dl(label, href):
    u, size = resolve(href)
    return dict(l=label, u=u, size=size)


# WWDC26 — Apple's own set, from developer.apple.com/wwdc26/wallpaper
T = 'WWDC26 Wallpaper'
L = dict(links(T))
mac = dl('Mac', L['Mac'])
add('WWDC26', 'WWDC26', mac['u'], mac['size'], fetch(mac['u'], 'WWDC26_Mac.png'), T,
    'Apple’s official WWDC26 wallpaper (developer.apple.com)', [dl('iPad', L['iPad']), dl('iPhone', L['iPhone'])])

# Apple Park — FaceTime backgrounds bundled with macOS Sequoia; the images are the downloads
T = 'Apple Park Wallpapers'
NAMES = {'Stairwell': 'Stairwell', 'AP': 'Apple Park', 'Shadow': 'Shadows', 'Fountain 2': 'Courtyard Fountain',
         'Arch 2': 'Rainbow Arch', 'Lobby 2': 'Lobby', 'Fitness': 'Fitness Center', 'Pathway': 'Pathway', 'Campus': 'Campus'}
for src in imgs(T):
    key = urllib.parse.unquote_plus(src.rsplit('/', 1)[1]).rsplit('.', 1)[0]
    if key not in NAMES:
        continue
    _, size = resolve(src)
    add(NAMES[key], 'Apple Park', src, size, fetch(src + '?format=500w', 'AP_' + key + '.png'), T,
        'Camera background bundled with macOS Sequoia · Image: Apple')

# macOS Tahoe aerials — stills from Apple's aerial videos (upscaled by Basic Apple Guy)
T = 'Tahoe Aerial wallpapers'
PLACES = [('Goa_A', 'Goa Beaches'), ('Goa_B', 'Goa Coast'), ('Through_Him', 'Through Himalayas'), ('Him_Day', 'Himalayas Day'),
          ('Ganges', 'The Ganges'), ('Ghansali', 'Ghansali from Above'), ('Him_Peaks', 'Himalayan Peaks'),
          ('Tea_Above', 'Tea Gardens from Above'), ('Tea_Day', 'Tea Gardens Day'), ('Reservoir', 'Reservoir Day'),
          ('Tea_Mist', 'Tea Gardens Mist')]
previews = [i for i in imgs(T) if 'Tahoe_Wallpapers1x1' not in i]
L = links(T)
for (key, name), prev in zip(PLACES, previews):
    mine = [(l, h) for l, h in L if h.split('/s/')[1].startswith(key + '_')]
    ds = [dl(l.replace('V.', 'Version '), h) for l, h in mine]
    main, rest = ds[0], ds[1:]
    add(name, 'macOS Tahoe Aerials', main['u'], main['size'], fetch(prev + '?format=500w', 'TA_' + key + '.png'), T,
        'Still from Apple’s macOS Tahoe aerial video, upscaled by Basic Apple Guy', rest)

# Tahoe lakeside — Apple's Tahoe wallpaper at four times of day (frames from Apple's videos)
T = 'Dynamic Tahoe Wallpapers'
L = links(T)
by = {}
for l, h in L:
    by.setdefault(l, []).append(h)
thumbs = {}
for tod in ('Dawn', 'Day', 'Dusk', 'Night'):
    mac, phone, pad = by[tod]
    m = dl('Mac', mac)
    thumbs[tod] = fetch(m['u'], f'Tahoe{tod}.png')
    add(f'Tahoe {tod}', 'macOS Tahoe Lakeside', m['u'], m['size'], thumbs[tod], T,
        'Frame from Apple’s macOS Tahoe wallpaper video, upscaled by Basic Apple Guy', [dl('iPhone', phone), dl('iPad', pad)])
m = dl('Mac', by['Dynamic Day/Night'][0])
add('Tahoe Day/Night (Dynamic)', 'macOS Tahoe Lakeside', m['u'], m['size'], thumbs['Day'], T,
    'Apple’s Tahoe frames combined into a light/dark dynamic wallpaper by Basic Apple Guy', dyn=True)
drive = by['Dynamic Time-of-Day Version'][0]
add('Tahoe Time of Day (Dynamic)', 'macOS Tahoe Lakeside', drive, 0, thumbs['Dawn'], T,
    'Apple’s Tahoe frames combined into a time-of-day dynamic wallpaper by Basic Apple Guy (Google Drive)', dyn=True)

# Golden Gate adventure — frames from Apple's WWDC26 keynote animation
T = 'macOS Golden Gate Adventure'
SCENES = {'ThumbValley': 'Thumb Valley', 'Space': 'Asteroid', 'GoldenGate': 'Golden Gate', 'ApplePark': 'Apple Park Arrival'}
for l, h in links(T):
    f = h.split('/s/')[1]
    scene = SCENES[f.split('_')[0]]
    num = re.search(r'_(\d)', f)[1]
    d = dl('', h)
    add(f'{scene} {num}', 'Golden Gate Adventure', d['u'], d['size'], fetch(d['u'], 'GGA_' + f), T,
        'Frame from Apple’s WWDC26 keynote animation, upscaled by Basic Apple Guy')

# Mt. Hood — Apple's Vision Pro environment (upscaled composite by Basic Apple Guy)
T = 'Mt. Hood Vision Pro Wallpaper'
L = dict(links(T))
pad = dl('iPad', L['iPad'])
mac = dl('Mac', L['Mac'])
add('Mount Hood', 'Vision Pro', mac['u'], mac['size'], fetch(pad['u'], 'MtHoodiPad.png'), T,
    'Apple’s Vision Pro Mount Hood environment, upscaled by Basic Apple Guy', [pad, dl('iPhone', L['iPhone'])])

json.dump(out, open(os.path.join(HERE, 'extras.json'), 'w'), indent=1)
print(len(out), 'wallpapers;', sum(1 + len(x['alts']) for x in out), 'files')
for x in out:
    print(f"{x['s']:24} {x['n']:30} {x['size'] / 1e6:6.1f} MB  +{len(x['alts'])} alts")
