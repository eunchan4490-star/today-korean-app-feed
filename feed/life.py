"""Small excerpts from public Korean App Store review RSS, not private support messages."""
import datetime,json,re,urllib.request
from pathlib import Path
from pain import text
APPS=['378084485','1018769995','839333328','454434967','311867728']
LIFE=re.compile(r'주문|배달|결제|환불|거래|중고|택배|일정|가족|예산|병원|이사|예약|수수료|운전|교통|버스|지하철|주소|쇼핑|구매|송금|배송|통장|주차|대출')
def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OpportunityExplorer/1.0'}),timeout=25) as r:return json.load(r)
def review_row(entry,app_id,name,observed):
 try:
  rating=int(entry['im:rating']['label']);ident=entry['id']['label'];title=text(entry['title']['label']);body=text(entry['content']['label'])
  body=re.sub(r'01[016789][- ]?\d{3,4}[- ]?\d{4}','[phone removed]',body)
  if rating>3 or rating<1 or len(body)<40 or not LIFE.search(title+' '+body):return None
  if not str(ident).isdigit() or not str(app_id).isdigit():return None
  return {'_kind':'pain','problem_category':'life','source_kind':'app_store_review','source_id':app_id+':'+str(ident),
          'app_id':app_id,'app_name':name,'title':title,'description':body,'rating':rating,
          'url':'https://apps.apple.com/kr/app/id'+app_id+'?see-all=reviews',
          'source_feed_url':'https://itunes.apple.com/kr/rss/customerreviews/id='+app_id+'/sortBy=mostRecent/json',
          'source_name':name+' · App Store 공개 리뷰','created_at':entry.get('updated',{}).get('label',''),
          'collected_at':observed}
 except (KeyError,TypeError,ValueError):return None

def collect():
 observed=datetime.datetime.now(datetime.timezone.utc).isoformat();rows=[];statuses={}
 for app_id in APPS:
  try:
   lookup=fetch('https://itunes.apple.com/lookup?id='+app_id+'&country=kr');name=lookup['results'][0]['trackName']
   data=fetch('https://itunes.apple.com/kr/rss/customerreviews/id='+app_id+'/sortBy=mostRecent/json');entries=data.get('feed',{}).get('entry',[])
   found=[]
   for entry in entries:
    row=review_row(entry,app_id,name,observed)
    if row:found.append(row)
    if len(found)>=6:break
   rows.extend(found);statuses[app_id]={'app_name':name,'status':'ok','count':len(found)}
  except Exception as error:statuses[app_id]={'status':type(error).__name__}
 if not rows:raise RuntimeError('No usable public life reviews; previous feed retained')
 return {'updated_at':observed,'sources':statuses,'items':list({r['source_id']:r for r in rows}.values())}
if __name__=='__main__':
 result=collect();temp=Path('life.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace('life.json');print('Collected',len(result['items']),'public everyday review excerpts')
