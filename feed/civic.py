"""Public complaint index only. Bodies and replies are read locally by the admin app."""
import datetime, html, json, re, urllib.parse, urllib.request, urllib.robotparser
from pathlib import Path
BASE='https://ceo.dobong.go.kr/'
AGENT='OpportunityExplorer-Discovery/1.0'
def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':AGENT}),timeout=25) as response:
  if response.geturl().split('/')[2]!='ceo.dobong.go.kr':raise ValueError('Unexpected redirect')
  return response.read(2_000_000).decode('utf-8')
def plain(value):
 return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',value))).strip()
def parse_list(document,observed):
 table=re.search(r'<table\b[^>]*class="boardList"[^>]*>(.*?)</table>',document,re.S|re.I)
 if not table:raise ValueError('Public board layout changed')
 rows=[]
 for part in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table[1],re.S|re.I):
  cells=re.findall(r'<td\b[^>]*>(.*?)</td>',part,re.S|re.I)
  if len(cells)!=6 or plain(cells[-1])!='공개':continue
  link=re.search(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',cells[1],re.S|re.I)
  if not link:continue
  query=urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(link[1])).query)
  ident=query.get('pcode',[''])[0]
  if query.get('code')!=['10000662'] or query.get('bmode')!=['D'] or not ident.isdigit():continue
  title=plain(link[2]);date=plain(cells[2]);status=plain(cells[4])
  if not title or len(title)>180 or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2}',date):continue
  # No resident names, attachments, complaint body, or reply text in this public index.
  rows.append({'_kind':'pain','problem_category':'civic','source_kind':'municipal_complaint',
   'source_id':'dobong:'+ident,'title':title,'description':title,
   'url':BASE+'bbs.asp?bmode=D&code=10000662&pcode='+ident,
   'source_name':'도봉구 · 공개 민원','municipality':'도봉구','processing_status':status,
   'created_at':date.replace('.','-'),'collected_at':observed,'index_only':True})
 return rows
def collect():
 observed=datetime.datetime.now(datetime.timezone.utc).isoformat();rows={}
 robots=urllib.robotparser.RobotFileParser();robots.parse(fetch(BASE+'robots.txt').splitlines())
 for page in range(1,9):
  url=BASE+'bbs.asp?code=10000662&intPage='+str(page)
  if not robots.can_fetch(AGENT,url):raise RuntimeError('Board collection disallowed by robots')
  for row in parse_list(fetch(url),observed):rows[row['source_id']]=row
 if not rows:raise RuntimeError('No public complaint index; previous index retained')
 return {'updated_at':observed,'sources':{'dobong':'ok'},'index_only':True,'items':list(rows.values())}
if __name__=='__main__':
 result=collect();temp=Path('civic.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace('civic.json');print('Indexed',len(result['items']),'public complaints; bodies not published')
