import datetime, html, json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

KEY = os.environ['PLAY_API_KEY']
BASE = 'https://playapi.info/api/v1/'
OUT = Path('feed.json')
now = datetime.datetime.now(datetime.timezone.utc)
since = (now.date() - datetime.timedelta(days=7)).isoformat()

def request(path, params):
    url = BASE + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'X-API-Key': KEY, 'User-Agent': 'TodayAppsFeed/1.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if not result.get('ok'):
        raise RuntimeError('Provider returned an error')
    return result

previous = {}
if OUT.exists():
    for item in json.loads(OUT.read_text(encoding='utf-8')).get('apps', []):
        previous[item['id']] = item

items = []
for page in range(1, 6):
    result = request('new', {'lang':'ko', 'since':since, 'per':100, 'page':page})
    for a in result.get('results', []):
        if not re.search(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', a.get('title', '')):
            continue
        item = {k: a.get(k) for k in ('id','title','released','icon')}
        item['developer'] = (a.get('developer') or {}).get('name', '')
        old = previous.get(item['id'], {})
        item['description'] = old.get('description', '')
        item['screenshots'] = old.get('screenshots', [])
        item['details_version'] = old.get('details_version', 0)
        items.append(item)
    if page >= result.get('pages', 1):
        break
    time.sleep(2)

# Spend at most 20 detail tokens per scheduled update; unchanged details are cached.
limit = min(int(os.environ.get('DETAIL_LIMIT', '20')), 100)
for item in [x for x in items if x['details_version'] < 2][:limit]:
    detail = request('app', {'id':item['id']}).get('app') or {}
    raw = detail.get('description') or ''
    raw = re.split(r'개발자\s*(?:연락처|정보)|developer\s*(?:contact|information)', raw, flags=re.I)[0]
    raw = re.sub(r'<br\s*/?>', '\n', raw, flags=re.I)
    clean = html.unescape(re.sub(r'<[^>]*>', '', raw))
    clean = re.sub(r'[^\S\n]+', ' ', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    item['description'] = clean
    media = detail.get('media') or {}
    item['screenshots'] = [u for u in (media.get('screenshots') or []) if isinstance(u, str) and u.startswith('https://play-lh.googleusercontent.com/')][:6]
    item['details_version'] = 2
    time.sleep(2)

data = {'updated_at':now.isoformat(), 'source':'Play API', 'apps':items}
temp=OUT.with_suffix('.tmp')
temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
temp.replace(OUT)
print('Wrote', len(items), 'apps')

