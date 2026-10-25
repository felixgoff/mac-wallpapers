# Downloads the "macOS Wallpapers" Google Photos album listing into cache/album:
# album.html (first page), items.json (every photo) and info.json (filenames and sizes).
import json, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'album')
os.makedirs(S, exist_ok=True)
SHARE = ('https://photos.google.com/share/AF1QipNNQyeVrqxBdNmBkq9ILswizuj-RYJFNt5GlxJZ90Y6hx0okrVSLKSnmFFbX7j5Mg'
         '?key=RV8tSXVJVGdfS1RIQUI0Q3RZZVhlTmw0WmhFZ2V3')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
if not os.path.exists(os.path.join(S, 'album.html')):
    req = urllib.request.Request(SHARE, headers={'User-Agent': UA})
    open(os.path.join(S, 'album.html'), 'w').write(urllib.request.urlopen(req, timeout=60).read().decode())
h = open(os.path.join(S, 'album.html')).read()
ALBUM = 'AF1QipNNQyeVrqxBdNmBkq9ILswizuj-RYJFNt5GlxJZ90Y6hx0okrVSLKSnmFFbX7j5Mg'
KEY = 'RV8tSXVJVGdfS1RIQUI0Q3RZZVhlTmw0WmhFZ2V3'
fsid = re.findall(r'"FdrFJe":"([^"]+)"', h)[0]
bl = re.findall(r'"cfb2h":"([^"]+)"', h)[0]


def rpc(rid, args, reqid=123456):
    freq = json.dumps([[[rid, json.dumps(args), None, "generic"]]])
    url = 'https://photos.google.com/_/PhotosUi/data/batchexecute?' + urllib.parse.urlencode(
        {'rpcids': rid, 'source-path': f'/share/{ALBUM}', 'f.sid': fsid, 'bl': bl, 'hl': 'en', '_reqid': reqid, 'rt': 'c'})
    req = urllib.request.Request(url, data=urllib.parse.urlencode({'f.req': freq}).encode(),
                                 headers={'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    for line in raw.splitlines():
        if not line.startswith('[['):
            continue
        for e in json.loads(line):
            if e[:2] == ['wrb.fr', rid]:
                return (json.loads(e[2]), None) if e[2] else (None, str(e)[:200])
    return None, raw[:300]


# Every photo: the first page is in the HTML, the rest come from the album's "load more" call
first = json.loads(dict(re.findall(r"AF_initDataCallback\(\{key: '(ds:\d+)'.*?data:(.*?), sideChannel: \{\}\}\);</script>", h, re.S))['ds:1'])
items, token, n = first[1], first[2], 0
while token:
    n += 1
    page, err = rpc('snAcKc', [ALBUM, token, None, KEY], 100000 + n)
    assert page, err
    items += page[1]
    token = page[2] if len(page) > 2 else None
    time.sleep(0.5)
json.dump(items, open(os.path.join(S, 'items.json'), 'w'))

# Filename, caption and size for each photo
info_p = os.path.join(S, 'info.json')
info = json.load(open(info_p)) if os.path.exists(info_p) else {}


def get(pid):
    for attempt in range(3):
        try:
            r, _ = rpc('fDcn4b', [pid, 1, KEY])
            if r:
                e = r[0]
                return pid, dict(file=e[2], desc=e[1], bytes=e[5], w=e[6], h=e[7], t=e[3])
        except Exception:
            pass
        time.sleep(1 + attempt)
    return pid, None


with ThreadPoolExecutor(4) as ex:
    for pid, v in ex.map(get, [x[0] for x in items if x[0] not in info]):
        if v:
            info[pid] = v
json.dump(info, open(info_p, 'w'))
print(len(items), 'photos,', len(info), 'with details')
