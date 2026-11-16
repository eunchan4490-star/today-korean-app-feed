import base64, datetime, html, json, os, re, sys, urllib.request
from pathlib import Path

URL = 'https://github.com/trending?since=weekly'
if len(sys.argv) > 1:
    page = Path(sys.argv[1]).read_text(encoding='utf-8')
else:
    req = urllib.request.Request(URL, headers={'User-Agent': 'WeeklyDiscoveryFeed/1.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        page = response.read().decode('utf-8')

def clean(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()

repos = []
for card in re.findall(r'<article\b[^>]*class="[^"]*Box-row[^"]*"[^>]*>.*?</article>', page, re.S):
    heading = re.search(r'<h2\b[^>]*>(.*?)</h2>', card, re.S)
    link = re.search(r'href="(/[^"/\s]+/[^"/\s]+)"', heading.group(1)) if heading else None
    if not link:
        continue
    path = html.unescape(link.group(1))
    if not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path):
        continue
    desc = re.search(r'<p\b[^>]*>(.*?)</p>', card, re.S)
    lang = re.search(r'<span\b[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>', card, re.S)
    stars = re.search(r'([\d,]+)\s+stars\s+this\s+week', card, re.I)
    repos.append({'name':path[1:], 'url':'https://github.com'+path,
                  'description':clean(desc.group(1)) if desc else '',
                  'language':clean(lang.group(1)) if lang else '',
                  'weekly_stars':int(stars.group(1).replace(',','')) if stars else None})

if len(repos) < 3:
    raise RuntimeError('GitHub trending page could not be parsed; existing feed retained')

def readme_excerpt(name):
    headers = {'User-Agent':'WeeklyDiscoveryFeed/1.0', 'Accept':'application/vnd.github+json'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    req = urllib.request.Request('https://api.github.com/repos/'+name+'/readme', headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.load(response)
    if data.get('encoding') != 'base64' or data.get('size', 0) > 1000000:
        return ''
    markdown = base64.b64decode(data.get('content','')).decode('utf-8', errors='replace')
    markdown = re.sub(r'```.*?```', '\n', markdown, flags=re.S)
    markdown = re.sub(r'<(script|style|details)\b[^>]*>.*?</\1>', '\n', markdown, flags=re.I|re.S)
    paragraphs = []
    for block in re.split(r'\n\s*\n', markdown):
        block = block.strip()
        if not block or re.match(r'^(#{1,6}\s|[|>]|[-*]\s|<)', block):
            continue
        block = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', block)
        block = re.sub(r'<[^>]*>', '', block)
        block = re.sub(r'[`*_#]', '', block)
        block = re.sub(r'\s+', ' ', html.unescape(block)).strip()
        if len(block) >= 45 and re.search(r'[A-Za-z가-힣]', block):
            paragraphs.append(block)
        if len(' '.join(paragraphs)) >= 350:
            break
    excerpt = '\n\n'.join(paragraphs)
    return (excerpt[:600].rsplit(' ',1)[0]+'…') if len(excerpt)>600 else excerpt

for repo in repos:
    try:
        repo['readme_excerpt'] = readme_excerpt(repo['name'])
    except Exception as error:
        print('README unavailable:', repo['name'], type(error).__name__)
        repo['readme_excerpt'] = ''
out = {'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'source':URL,'repos':repos}
temp=Path('trending.tmp')
temp.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
temp.replace('trending.json')
print('Wrote', len(repos), 'weekly trending repositories')
