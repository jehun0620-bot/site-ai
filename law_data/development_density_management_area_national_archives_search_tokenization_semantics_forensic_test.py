# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_search_tokenization_semantics_forensic.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'; MAX=16*1024*1024
CASES=[
    ('PC_SEONGNAM','성남시'),
    ('PC_ROAD_NAME','도로명주소'),
    ('PC_GUIDE_MAP','안내도'),
    ('PC_SEONGNAM_ROAD','성남시 도로명주소'),
    ('PC_ROAD_GUIDE','도로명주소 안내도'),
    ('PC_FULL_TITLE','성남시 도로명주소 안내도'),
    ('UQQ_TOKEN_A','개발밀도'),
    ('UQQ_TOKEN_B','관리구역'),
    ('UQQ_TOKEN_C','개발밀도 관리구역'),
    ('UQQ_TOKEN_D','개발 밀도 관리 구역'),
    ('UQQ_TOKEN_E','개발밀도관리구역'),
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
def parse_rows(text):
    out=[]
    for rm in ROW_RE.finditer(text):
        frag=rm.group(1);cm=CALL_RE.search(frag)
        if not cm:continue
        tm=re.search(r'<div\s+class=["\']title["\'][^>]*>\s*<a[^>]*>([\s\S]*?)</a>',frag,re.I)
        title=clean(tm.group(1)) if tm else ''
        im=re.search(r'생산기관\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        institution=clean(im.group(1)) if im else ''
        ym=re.search(r'생산연도\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        year=clean(ym.group(1)) if ym else ''
        out.append({'rc_code':cm.group(1),'rc_rfile_no':cm.group(2),'rc_ritem_no':cm.group(3),'title':title,'institution':institution,'year':year})
    return out

def main():
    print('='*60);print('NATIONAL ARCHIVES SEARCH TOKENIZATION SEMANTICS FORENSIC - S197');print('='*60)
    print('Purpose: explain S196 partial semantics, not infer legal absence')
    print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];tech=0
    for label,q in CASES:
        http,url,body,ov,err=fetch(s,q);text,enc=dec(body);rows=parse_rows(text)
        if err or ov or http!=200:tech+=1
        target_pc=sum('성남시 도로명주소 안내도' in r['title'] for r in rows)
        uqq_exact=sum(('개발밀도관리구역' in r['title'] or '개발밀도 관리구역' in r['title']) for r in rows)
        seongnam=sum('성남' in r['title'] or '성남' in r['institution'] for r in rows)
        density=sum('개발밀도' in r['title'] for r in rows)
        results.append({'label':label,'query':q,'http':http,'final_url':url,'byte_length':len(body),'encoding':enc,'overflow':ov,'error':err,'row_count':len(rows),'positive_control_title_match_count':target_pc,'uqq700_title_match_count':uqq_exact,'seongnam_related_row_count':seongnam,'development_density_title_count':density,'rows':rows[:30]})
        print('CASE:',label,'| QUERY:',q,'| HTTP:',http,'| ROWS:',len(rows),'| PC_TITLE:',target_pc,'| UQQ_TITLE:',uqq_exact,'| SEONGNAM:',seongnam,'| DENSITY:',density)
        for r in rows[:8]:print('  ROW:',r)
    by={x['label']:x for x in results}
    observations={
        'single_seongnam_returns_rows':by['PC_SEONGNAM']['row_count']>0,
        'road_guide_returns_rows':by['PC_ROAD_GUIDE']['row_count']>0,
        'full_known_title_returns_zero':by['PC_FULL_TITLE']['row_count']==0,
        'development_density_returns_rows':by['UQQ_TOKEN_A']['row_count']>0,
        'compact_uqq_target_returns_zero':by['UQQ_TOKEN_E']['row_count']==0,
        'tokenized_uqq_variant_returns_rows':by['UQQ_TOKEN_C']['row_count']>0 or by['UQQ_TOKEN_D']['row_count']>0,
    }
    semantic='NATIONAL_ARCHIVES_SEARCH_TOKENIZATION_SEMANTICS_CAPTURED' if tech==0 else 'NATIONAL_ARCHIVES_SEARCH_TOKENIZATION_SEMANTICS_TECHNICAL_UNKNOWN'
    out={'step':'STEP 17-21-C-16-8-T-93-S197','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'observations':observations,'summary':{'case_count':len(results),'technical_unknown_count':tech,'semantic_state':semantic,'search_semantics_terminally_qualified':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nOBSERVATIONS');[print(f'{k}: {v}') for k,v in observations.items()]
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'case exact':len(results)==len(CASES),'technical unknown zero':tech==0,'single seongnam positive':observations['single_seongnam_returns_rows'],'road guide positive':observations['road_guide_returns_rows'],'known full title zero reproduced':observations['full_known_title_returns_zero'],'development density positive':observations['development_density_returns_rows'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'search semantics not terminal':not out['summary']['search_semantics_terminally_qualified'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S197 National Archives search tokenization semantics forensic failed')
if __name__=='__main__':main()
