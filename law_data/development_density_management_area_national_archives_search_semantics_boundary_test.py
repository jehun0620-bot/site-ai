# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_search_semantics_boundary.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'; MAX=16*1024*1024
CASES=[
    {'label':'KNOWN_MULTIWORD_POSITIVE','query':'성남시 도로명주소 안내도','expect_title_contains':'성남시 도로명주소 안내도'},
    {'label':'KNOWN_PHRASE_VARIANT','query':'도로명주소 안내도','expect_title_contains':'성남시 도로명주소 안내도'},
    {'label':'KNOWN_DEVELOPMENT_DENSITY','query':'청주시 개발밀도 관리방안','expect_title_contains':'청주시 개발밀도 관리방안'},
    {'label':'TARGET_DIRECT','query':'개발밀도관리구역','expect_title_contains':None},
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
        return r.status_code,str(r.url),bytes(b),ov,None
    except requests.RequestException as e:return None,URL,b'',False,f'{type(e).__name__}: {e}'
def rows(text):
    out=[]
    for rm in ROW_RE.finditer(text):
        frag=rm.group(1);cm=CALL_RE.search(frag)
        if not cm:continue
        tm=re.search(r'<div\s+class=["\']title["\'][^>]*>\s*<a[^>]*>([\s\S]*?)</a>',frag,re.I)
        title=clean(tm.group(1)) if tm else ''
        ym=re.search(r'생산연도\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        year=clean(ym.group(1)) if ym else ''
        im=re.search(r'생산기관\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        inst=clean(im.group(1)) if im else ''
        out.append({'rc_code':cm.group(1),'rc_rfile_no':cm.group(2),'rc_ritem_no':cm.group(3),'title':title,'year':year,'institution':inst})
    return out

def main():
    print('='*60);print('NATIONAL ARCHIVES SEARCH SEMANTICS BOUNDARY - S196');print('='*60)
    print('Negative evidence: DISABLED');print('Legal absence inference: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];tech=0;positive_ok=0
    for c in CASES:
        http,url,body,ov,err=fetch(s,c['query']);text,enc=dec(body);parsed=rows(text)
        if err or ov or http!=200:tech+=1
        expected=c['expect_title_contains'];matched=[r for r in parsed if expected and expected in r['title']]
        if expected and matched:positive_ok+=1
        results.append({'label':c['label'],'query':c['query'],'http':http,'final_url':url,'byte_length':len(body),'encoding':enc,'overflow':ov,'error':err,'row_count':len(parsed),'rows':parsed[:25],'expected_title':expected,'expected_match_count':len(matched)})
        print('CASE:',c['label'],'| QUERY:',c['query'],'| HTTP:',http,'| BYTES:',len(body),'| ROWS:',len(parsed),'| EXPECTED_MATCH:',len(matched))
        for r in parsed[:10]:print('  ROW:',r)
    target=next(x for x in results if x['label']=='TARGET_DIRECT')
    out={'step':'STEP 17-21-C-16-8-T-92-S196','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'summary':{'case_count':len(results),'positive_control_case_count':3,'positive_control_resolved_count':positive_ok,'target_direct_row_count':target['row_count'],'technical_unknown_count':tech,'semantic_state':'NATIONAL_ARCHIVES_SEARCH_SEMANTICS_BOUNDARY_QUALIFIED' if positive_ok==3 and tech==0 else 'NATIONAL_ARCHIVES_SEARCH_SEMANTICS_BOUNDARY_PARTIAL','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'case exact':len(results)==4,'positive controls all resolved':positive_ok==3,'technical unknown zero':tech==0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S196 National Archives search semantics boundary failed')
if __name__=='__main__':main()
