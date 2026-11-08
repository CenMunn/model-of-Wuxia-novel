"""Fetch a small, cached set of public-domain chapter witnesses, serially."""
from pathlib import Path
import requests,json,hashlib,time
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent
DEST=HERE/'witnesses';DEST.mkdir(exist_ok=True)
session=requests.Session();session.headers['User-Agent']='WuxiaCourseCorpusReview/1.0 (educational chapter verification; serial cached requests)'
targets=[('sanxiawuyi',n,f'https://zh.wikisource.org/zh-hans/三俠五義/第{n:03d}回') for n in [3,6,7,10,45]]
nums={34:'三十四',35:'三十五',36:'三十六',37:'三十七',38:'三十八',39:'三十九',40:'四十'}
targets += [('ernvyingxiongzhuan',n,f'https://zh.wikisource.org/zh-hans/兒女英雄傳/第{nums[n]}回') for n in range(34,41)]
manifest=[]
for book,n,url in targets:
    stem=f'{book}_{n:03d}';html=DEST/(stem+'.html')
    try:
        if not html.exists():
            response=session.get(url,timeout=18);response.raise_for_status()
            html.write_bytes(response.content);time.sleep(.6)
        data=html.read_bytes();soup=BeautifulSoup(data,'html.parser')
        node=soup.select_one('#mw-content-text .mw-parser-output')
        if node is None:raise ValueError('No article body')
        paragraphs=[p.get_text('',strip=False).strip() for p in node.find_all('p') if not p.find_parent('table')]
        paragraphs=[p for p in paragraphs if p and '本作品' not in p[:12] and '公有领域' not in p and 'Public domain' not in p]
        text='\n\n'.join(paragraphs)
        (DEST/(stem+'.txt')).write_bytes(text.encode('utf-8'))
        oldid=soup.select_one('#t-permalink a')
        entry={'book_id':book,'chapter':n,'url':url,'html_sha256':hashlib.sha256(data).hexdigest(),
               'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'text_file':stem+'.txt',
               'revision_url':oldid.get('href') if oldid else None,'characters':len(text),'paragraphs':len(paragraphs)}
        manifest.append(entry);print(book,n,len(text),len(paragraphs),flush=True)
    except Exception as e:manifest.append({'book_id':book,'chapter':n,'url':url,'error':str(e)});print('FAILED',book,n,str(e),flush=True)
    (DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
