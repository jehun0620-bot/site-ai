# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_uqq700_bounded_candidate_search.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'
MAX=16*1024*1024
QUERIES=[
    ('개발밀도관리구역','DIRECT_CANDIDATE'),
    ('개발밀도 관리구역','DIRECT_CANDIDATE'),
    ('개발밀도관리구역 지정','DIRECT_CANDIDATE'),
    ('개발밀도관리구역 고시','DIRECT_CANDIDATE'),
    ('도시관리계획 개발밀도관리구역','DIRECT_CANDIDATE'),
    ('개발밀도','RELATED_CANDIDATE'),
    ('UQQ700','DIRECT_CANDIDATE'),
]
CALL_RE=re.compile(r"showItemDetailWithQuery\('([^']+)','([^']+)','([^']+)'(?:,'([^']*)','([^']*)')?\)",re.I)
ROW_RE=re.compile(r'<div\s+class=["\']result-row["\']>([\s\S]*?)(?=<div\s+class=["\']result-row["\']>|\Z)',re.I)

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def fetch(s,q):
    params={'query_type':'keyword','is_detail':'yes','upside_query':q,'keyword':q,'beforeKeyword':'','afterKeyword':'','doc_type':'','srchinit':'ritem'}
    try:
        r=s.get(URL,params=params,timeout=30,stream=True,allow_redirects=True);b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'body':bytes(b),'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':URL,'body':b'','error':f'{type(e).__name__}: {e}'}
def parse_rows(text,q,candidate_state):
    out=[]
    for rm in ROW_RE.finditer(text):
        frag=rm.group(1); cm=CALL_RE.search(frag)
        if not cm:continue
        title=''; tm=re.search(r'<div\s+class=["\']title["\'][^>]*>\s*<a[^>]*>([\s\S]*?)</a>',frag,re.I)
        if tm:title=clean(tm.group(1))
        institution=''; im=re.search(r'생산기관\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        if im:institution=clean(im.group(1))
        year=''; ym=re.search(r'생산연도\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        if ym:year=clean(ym.group(1))
        manage=''; mm=re.search(r'관리번호\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        if mm:manage=clean(mm.group(1))
        if q not in clean(frag) and candidate_state=='DIRECT_CANDIDATE':
            continue
        out.append({'query':q,'candidate_state':candidate_state,'rc_code':cm.group(1),'rc_rfile_no':cm.group(2),'rc_ritem_no':cm.group(3),'page':cm.group(4),'close_only':cm.group(5),'title':title,'institution':institution,'year':year,'manage_no':manage})
    return out

def main():
    print('='*60);print('NATIONAL ARCHIVES UQQ700 BOUNDED CANDIDATE SEARCH - S194');print('='*60)
    print('Candidate hit stop policy: ENABLED');print('Negative evidence: DISABLED');print('Legal absence inference: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];candidates=[];tech=0
    for q,state in QUERIES:
        r=fetch(s,q);text,encoding=dec(r['body']); rows=parse_rows(text,q,state)
        if r['state']=='TECHNICAL_REQUEST_UNKNOWN':tech+=1
        results.append({'query':q,'candidate_class':state,'state':r['state'],'http':r['http'],'final_url':r['url'],'byte_length':len(r['body']),'encoding':encoding,'row_count':len(rows),'rows':rows,'error':r['error']})
        print('QUERY:',q,'| CLASS:',state,'| HTTP:',r['http'],'| BYTES:',len(r['body']),'| ROWS:',len(rows))
        for x in rows[:10]:print('  ROW:',x)
        candidates.extend(rows)
        if rows:
            print('CANDIDATE HIT -> STOP FURTHER QUERIES')
            break
    uniq={f"{x['rc_code']}|{x['rc_rfile_no']}|{x['rc_ritem_no']}":x for x in candidates};candidates=list(uniq.values())
    direct=sum(x['candidate_state']=='DIRECT_CANDIDATE' for x in candidates);related=len(candidates)-direct
    semantic='NATIONAL_ARCHIVES_UQQ700_CANDIDATE_FOUND_REQUIRE_DETAIL_CONTEXT' if candidates else ('NATIONAL_ARCHIVES_UQQ700_TECHNICAL_UNKNOWN' if tech else 'NATIONAL_ARCHIVES_UQQ700_NO_CANDIDATE_IN_BOUNDED_SEARCH_SURFACE')
    out={'step':'STEP 17-21-C-16-8-T-90-S194','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','queries_planned':[q for q,_ in QUERIES],'results':results,'candidates':candidates,'summary':{'request_count':len(results),'candidate_count':len(candidates),'direct_candidate_count':direct,'related_candidate_count':related,'technical_unknown_count':tech,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nCANDIDATES');print('NONE' if not candidates else candidates)
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'request bounded':1<=len(results)<=len(QUERIES),'candidate stop policy respected':(not candidates) or len(results)<len(QUERIES) or len(results)==1,'technical unknown zero':tech==0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S194 National Archives bounded UQQ700 candidate search failed')
if __name__=='__main__':main()
