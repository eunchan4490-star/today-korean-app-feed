"""Recent public Show HN introductions, not claimed product release dates."""
import concurrent.futures, datetime, html, ipaddress, json, re, socket, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from pain import fetch,text
ROOT='https://hacker-news.firebaseio.com/v0/'
WINDOW=7*24*60*60
class Metadata(HTMLParser):
 def __init__(self):super().__init__();self.description=''
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag.lower()=='meta' and (a.get('name','').lower()=='description' or a.get('property','').lower()=='og:description'):
   value=text(a.get('content',''))
   if len(value)>len(self.description):self.description=value[:700]
def canonical_url(value):
 try:
  u=urllib.parse.urlsplit(value)
  if u.scheme!='https' or u.username or u.password or u.port not in (None,443) or not u.hostname or '.' not in u.hostname:return None
  host=u.hostname.lower()
  try:
   if not ipaddress.ip_address(host).is_global:return None
  except ValueError:
   if host.endswith(('.local','.localhost','.internal')):return None
  path=re.sub(r'/+','/',u.path).rstrip('/') or '/'
  if host=='github.com':
   parts=path.strip('/').split('/')
   if len(parts)>=2:path='/'+parts[0].lower()+'/'+re.sub(r'\.git$','',parts[1],flags=re.I).lower()
  # Query strings and fragments identify campaigns, not a new product.
  return urllib.parse.urlunsplit(('https',host,path,'',''))
 except (ValueError,TypeError):return None
def public_target(url):
 if not canonical_url(url):raise ValueError('Invalid product URL')
 host=urllib.parse.urlsplit(url).hostname
 addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
 if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Non-public target')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None
def metadata(url):
 # Follow at most three redirects, validating every target; no cookies or credentials.
 for attempt in range(4):
  public_target(url)
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'OpportunityExplorer-Discovery/1.0','Accept':'text/html'})
   with urllib.request.build_opener(NoRedirect()).open(req,timeout=12) as response:
    if 'text/html' not in response.headers.get('Content-Type',''):return ''
    charset=response.headers.get_content_charset() or 'utf-8';parser=Metadata();parser.feed(response.read(180_000).decode(charset,errors='replace'));return parser.description
  except urllib.error.HTTPError as e:
   if e.code not in (301,302,303,307,308) or attempt==3:raise
   url=urllib.parse.urljoin(url,e.headers.get('Location',''))
 return ''
def row(item,now):
 if not item or item.get('deleted') or item.get('dead') or item.get('type')!='story':return None
 title=text(item.get('title',''));stamp=item.get('time');ident=item.get('id');url=item.get('url','');canonical=canonical_url(url)
 if not title.lower().startswith('show hn:') or not isinstance(stamp,int) or not isinstance(ident,int) or not now-WINDOW<=stamp<=now or not canonical:return None
 return {'_kind':'pain','problem_category':'services','source_kind':'show_hn','source_id':str(ident),
  'title':title,'description':text(item.get('text','')),'product_url':url,'product_key':canonical,
  'url':'https://news.ycombinator.com/item?id='+str(ident),'source_name':'Show HN',
  'introduced_at_ms':stamp*1000,'introduced_at':datetime.datetime.fromtimestamp(stamp,datetime.timezone.utc).isoformat(),
  'date_basis':'public_introduction','release_date':None,'pricing_status':'unverified',
  'collected_at':datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat()}
def collect():
 now=int(datetime.datetime.now(datetime.timezone.utc).timestamp());ids=fetch(ROOT+'showstories.json')[:200]
 def load(ident):
  try:return row(fetch(ROOT+'item/'+str(ident)+'.json'),now),False
  except Exception:return None,True
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:loaded=list(pool.map(load,ids))
 failures=sum(failed for _,failed in loaded)
 if ids and failures==len(ids):raise RuntimeError('All introduction requests failed; previous feed retained')
 rows=[r for r,_ in loaded if r]
 rows.sort(key=lambda r:r['introduced_at_ms'],reverse=True);unique={}
 for r in rows:
  unique.setdefault(r['product_key'],r)
  if len(unique)>=40:break
 rows=list(unique.values())
 def enrich(r):
  try:r['product_description']=metadata(r['product_url']);r['metadata_status']='ok'
  except Exception as error:r['product_description']='';r['metadata_status']=type(error).__name__
  # Source-labelled excerpts, no screenshots, full pages, or inferred pricing.
  r['description']='Show HN: '+r['description']+('\nWebsite metadata: '+r['product_description'] if r['product_description'] else '')
  return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(enrich,rows))
 # A successful empty window replaces stale data; network failure fetching the list does not.
 return {'updated_at':datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat(),'window_days':7,'sources':{'show_hn':'partial' if failures else 'ok','failed_item_requests':failures},'items':rows}
if __name__=='__main__':
 result=collect();tmp=Path('services.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace('services.json');print('Collected',len(result['items']),'recent introductions; metadata:',sum(bool(r['product_description']) for r in result['items']))
