"""Publish public source excerpts. No AI output, account credentials, or demand claims."""
import datetime, html, json, os, re, urllib.parse, urllib.request
from pathlib import Path

def text(value):
    value = re.sub(r'```.*?```', ' ', value or '', flags=re.S)
    value = html.unescape(re.sub(r'<[^>]*>', ' ', value))
    value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email removed]', value)
    return re.sub(r'\s+', ' ', value).strip()[:2500]

def github_row(item, observed):
    if 'pull_request' in item or not item.get('body') or not item.get('id'):
        return None
    url = item.get('html_url', '')
    if not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+/issues/\d+', url):
        return None
    return {'_kind':'pain', 'source_kind':'github_issue', 'source_id':str(item['id']),
            'title':text(item.get('title')), 'description':text(item['body']), 'url':url,
            'source_name':'GitHub Issues', 'created_at':item.get('created_at'),
            'updated_at':item.get('updated_at'), 'comments_count':item.get('comments',0), 'collected_at':observed}

def hn_row(item, observed):
    if not item or item.get('deleted') or item.get('dead') or item.get('type') != 'story':
        return None
    title = item.get('title','')
    if not title.lower().startswith('ask hn:') or re.search(r'who.*(hiring|hired)',title,re.I):
        return None
    body=text(item.get('text',''))
    if not body or not re.search(r'how |what |wish|tool|recommend|alternative|problem|manual|manage|workflow|track|help|pain',title+' '+body,re.I):
        return None
    return {'_kind':'pain','source_kind':'ask_hn','source_id':str(item['id']), 'title':text(title),
            'description':body, 'url':'https://news.ycombinator.com/item?id='+str(item['id']),
            'source_name':'Ask HN', 'created_at':datetime.datetime.fromtimestamp(item['time'],datetime.timezone.utc).isoformat(),
            'comments_count':item.get('descendants',0), 'collected_at':observed}

def fetch(url, github=False):
    headers={'User-Agent':'OpportunityExplorer-Discovery/1.0','Accept':'application/json'}
    if github and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=25) as response:
        return json.load(response)

def collect():
    now=datetime.datetime.now(datetime.timezone.utc); observed=now.isoformat(); rows=[]; statuses={}
    try:
        since=(now-datetime.timedelta(days=30)).date().isoformat()
        query='is:issue is:open archived:false label:enhancement comments:>=2 updated:>='+since
        data=fetch('https://api.github.com/search/issues?'+urllib.parse.urlencode({'q':query,'sort':'updated','order':'desc','per_page':15}),True)
        rows.extend(row for item in data['items'] if (row:=github_row(item,observed)))
        statuses['github_issues']='ok'
    except Exception as error:
        statuses['github_issues']=type(error).__name__
    try:
        ids=fetch('https://hacker-news.firebaseio.com/v0/askstories.json')[:30]
        count=0
        for ident in ids:
            try:
                row=hn_row(fetch('https://hacker-news.firebaseio.com/v0/item/'+str(ident)+'.json'),observed)
                if row: rows.append(row);count+=1
                if count>=15:break
            except Exception:continue
        statuses['ask_hn']='ok' if count else 'no_matching_posts'
    except Exception as error:
        statuses['ask_hn']=type(error).__name__
    if not rows:raise RuntimeError('No source posts collected; existing feed retained')
    unique={r['source_kind']+':'+r['source_id']:r for r in rows}
    return {'updated_at':observed,'sources':statuses,'items':list(unique.values())}

if __name__=='__main__':
    result=collect();temp=Path('pain.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace('pain.json');print('Collected',len(result['items']),'public source posts; source status:',result['sources'])
