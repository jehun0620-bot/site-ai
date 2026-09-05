# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import quote_plus
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_seongnam_full_metadata_crawl.json'
URL='https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp'
UA='Mozilla/5.0'
MAX_PAGES=73
GYEONGGI='4100000000'; SEONGNAM='4113000000'
TERMS_DIRECT=['개발밀도관리구역','개발밀도 관리구역','UQQ700']
TERMS_RELATED=['개발밀도']
ROW_RE=re.compile(r"<tr[^>]*>\s*<td[^>]*>(?P<date>[\s\S]*?)</td>\s*<td[^>]*title=[\"'](?P<notice>[^\"']*)[\"'][^>]*>[\s\S]*?</td>\s*<td[^>]*>[\s\S]*?<a\s+href=[\"'](?P<href>[^\"']*gvGosiDet\.jsp[^\"']*)[\"'][^>]*title=[\"'](?P<title>[^\"']*)[\"']",re.I)
SEQ_RE=re.compile(r'(?:\?|&)seq=(\d+)')

def enc(v:str)->str:return quote_plus(v.encode('euc-kr'),safe='')
def body(page:int)->bytes:
    pairs=[('pageNo',str(page)),('mode',''),('zonenm_t',''),('area',''),('chrgorg_t',''),('selSggCd',SEONGNAM),('mobile_yn',''),('select2',GYEONGGI),('select3',SEONGNAM),('startdt',''),('enddt',''),('chrgorg',''),('gosichrg',''),('gosino',''),('prj_nm',''),('prj_cat_cd',''),('listSize','50'),('zonenm','')]
    return '&'.join(f'{k}={enc(v)}' for k,v in pairs).encode('ascii')
def decode(b:bytes)->str:
    for e in ('euc-kr','cp949','utf-8'):
        try:return b.decode(e)
        except:pass
    return b.decode('euc-kr','ignore')
def clean(s:str)->str:return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def fetch(s:requests.Session,page:int):
    r=s.post(URL,data=body(page),headers={'Content-Type':'application/x-www-form-urlencoded','Referer':URL,'Origin':'https://www.eum.go.kr'},timeout=25)
    return r.status_code,decode(r.content)
def rows(text:str,page:int):
    out=[]
    for m in ROW_RE.finditer(text):
        seq=SEQ_RE.search(html.unescape(m.group('href')))
        if not seq:continue
        notice=clean(m.group('notice')); title=clean(m.group('title')); date=clean(m.group('date'))
        if '성남시' not in notice:continue
        out.append({'page':page,'seq':seq.group(1),'date':date,'notice':notice,'title':title})
    return out

def main():
    print('='*60);print('EUM GOSI SEONGNAM FULL METADATA CRAWL - S176');print('='*60)
    print('Pages: 1..73 | Search query: NONE | Negative evidence: DISABLED | UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    pre=s.get(URL,timeout=25)
    tech=0; all_rows=[]; page_stats=[]; candidates=[]
    if pre.status_code!=200: raise AssertionError('preflight failed')
    for p in range(1,MAX_PAGES+1):
        try: status,text=fetch(s,p)
        except requests.RequestException as e:
            tech+=1; page_stats.append({'page':p,'state':'TECHNICAL_REQUEST_UNKNOWN','error':str(e)}); print('PAGE',p,'TECHNICAL_REQUEST_UNKNOWN'); break
        rs=rows(text,p); ok=status==200 and SEONGNAM in text and GYEONGGI in text
        if not ok:
            tech+=1; page_stats.append({'page':p,'state':'TECHNICAL_REQUEST_UNKNOWN','http':status}); print('PAGE',p,'TECHNICAL_REQUEST_UNKNOWN'); break
        page_stats.append({'page':p,'state':'QUALIFIED','http':status,'row_count':len(rs)})
        all_rows.extend(rs)
        for r in rs:
            if any(t in r['title'] for t in TERMS_DIRECT): candidates.append({**r,'candidate_state':'DIRECT_CANDIDATE'})
            elif any(t in r['title'] for t in TERMS_RELATED): candidates.append({**r,'candidate_state':'RELATED_CANDIDATE'})
        print('PAGE',p,'ROWS',len(rs),'CANDIDATES_SO_FAR',len(candidates))
        if candidates: break
    uniq={r['seq']:r for r in all_rows}; all_rows=list(uniq.values())
    cuniq={r['seq']:r for r in candidates}; candidates=list(cuniq.values())
    direct=sum(r['candidate_state']=='DIRECT_CANDIDATE' for r in candidates); related=len(candidates)-direct
    semantic='EUM_SEONGNAM_FULL_METADATA_CANDIDATE_FOUND_REQUIRE_DETAIL_CONTEXT' if candidates else ('EUM_SEONGNAM_FULL_METADATA_TECHNICAL_UNKNOWN' if tech else 'EUM_SEONGNAM_FULL_METADATA_CRAWL_NO_TITLE_CANDIDATE')
    out={'step':'STEP 17-21-C-16-8-T-72-S176','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAND_USE_PORTAL','page_ceiling':MAX_PAGES,'pages':page_stats,'rows':all_rows,'candidates':candidates,'summary':{'pages_completed':sum(x.get('state')=='QUALIFIED' for x in page_stats),'row_count':len(all_rows),'candidate_count':len(candidates),'direct_candidate_count':direct,'related_candidate_count':related,'technical_unknown_count':tech,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nCANDIDATES'); print('NONE' if not candidates else candidates)
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in out['summary'].items()]; print('Output:',OUT)
    checks={'technical unknown zero':tech==0,'candidate stop policy respected':(not candidates) or out['summary']['pages_completed']<MAX_PAGES,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in checks.items()]; print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S176 EUM Seongnam full metadata crawl failed')
if __name__=='__main__': main()
