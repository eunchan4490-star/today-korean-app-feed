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
    markdown = re.sub(r'```.*?```|~~~.*?~~~', '\n', markdown, flags=re.S)
    markdown = re.sub(r'<(script|style|details)\b[^>]*>.*?</\1>', '\n', markdown, flags=re.I|re.S)
    markdown = re.sub(r'<!--.*?-->', '\n', markdown, flags=re.S)
    # Remove images and badge links before ordinary links, including nested badges.
    markdown = re.sub(r'\[!\[[^\]]*\]\([^\n)]*\)\]\([^\n)]*\)', '', markdown)
    markdown = re.sub(r'!\[[^\]]*\]\([^\n)]*\)', '', markdown)
    markdown = re.sub(r'<(?:img|svg)\b[^>]*>', '', markdown, flags=re.I)
    paragraphs = []
    for block in re.split(r'\n\s*\n', markdown):
        block = block.strip()
        if not block or re.match(r'^(#{1,6}\s|[|>]|<)', block):
            continue
        block = re.sub(r'\[([^\]]+)\]\([^\n)]*\)', r'\1', block)
        block = re.sub(r'<[^>]*>', '', block)
        block = re.sub(r'https?://\S+', '', block)
        block = re.sub(r'[`*_#]', '', block)
        block = re.sub(r'\s+', ' ', html.unescape(block)).strip(' -|:')
        if re.search(r'\b(npm version|license|pull requests welcome|build status)\b', block, re.I) and len(block) < 200:
            continue
        if len(block) >= 45 and re.search(r'[A-Za-z가-힣]', block):
            paragraphs.append(block)
        if len(' '.join(paragraphs)) >= 1400:
            break
    excerpt = '\n\n'.join(paragraphs)
    return (excerpt[:1800].rsplit(' ',1)[0]+'…') if len(excerpt)>1800 else excerpt

for repo in repos:
    # Manually verified project-specific articles; never treat search hits as exact matches.
    related = {'meta/astryx': 'https://news.hada.io/topic?id=31190',
               'anthropics/skills': 'https://news.hada.io/topic?id=23713'}
    repo['korean_article'] = related.get(repo['name'].lower(), '')
    summaries = {
        'meta/astryx': '메타가 만든 웹 화면 디자인 도구 모음이에요. 버튼, 메뉴처럼 자주 쓰는 화면 요소를 제공해서 앱이나 웹사이트를 일관된 디자인으로 더 쉽게 만들 수 있어요. 색상과 스타일을 바꿀 수 있고 AI 코딩 도구와 함께 쓰는 기능도 제공해요.',
        'anthropics/skills': 'AI가 특정 일을 더 잘하도록 작업 방법을 담아 둔 스킬 예제 모음이에요. 문서 만들기나 웹 앱 테스트처럼 반복되는 작업에 필요한 지침과 도구를 살펴보고, 자신에게 맞는 스킬을 만드는 데 참고할 수 있어요.'
    }
    repo['korean_summary'] = summaries.get(repo['name'].lower(), '')
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
