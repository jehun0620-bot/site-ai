# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_search_contract_replay_positive_control.json'
URL='https://www.archives.go.kr/next/srch/uniDetailSearch.do'
UA='Mozilla/5.0'; MAX=16*1024*1024
CASES=[
    {'label':'FTR_BASELINE_SEONGNAM','query_type':'ftr','keyword':'성남시','orgName':'','expect_title_contains':'성남시'},
    {'label':'KEYWORD_BASELINE_SEONGNAM_DIAGNOSTIC','query_type':'keyword','keyword':'성남시','orgName':'','expect_title_contains':None},
    {'label':'FTR_ORG_FILTER_POSITIVE','query_type':'ftr','keyword':'도로명주소','orgName':'경기도 성남시','expect_title_contains':'성남시 도로명주소 안내도'},
    {'label':'FTR_ORG_FILTER_DENSITY_DIAGNOSTIC','query_type':'ftr','keyword':'개발밀도','orgName':'경기도 성남시','expect_title_contains':None},
]
CALL_RE=re.compile(r"showItemDetailWithQuery\('([^']+)','([^']+)','([^']+)'(?:,'([^']*)','([^']*)')?\)",re.I)
ROW_RE=re.compile(r'<div\s+class=["\']result-row["\']>([\s\S]*?)(?=<div\s+class=["\']result-row["\']>|\Z)',re.I)

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def parse_rows(text):
    out=[]
    for rm in ROW_RE.finditer(text):
        frag=rm.group(1);cm=CALL_RE.search(frag)
        if not cm:continue
        tm=re.search(r'<div\s+class=["\']title["\'][^>]*>\s*<a[^>]*>([\s\S]*?)</a>',frag,re.I)
        title=clean(tm.group(1)) if tm else ''
        im=re.search(r'생산기관\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        inst=clean(im.group(1)) if im else ''
        ym=re.search(r'생산연도\s*:\s*</span>\s*<span[^>]*>([\s\S]*?)</span>',frag,re.I)
        year=clean(ym.group(1)) if ym else ''
        out.append({'rc_code':cm.group(1),'rc_rfile_no':cm.group(2),'rc_ritem_no':cm.group(3),'title':title,'institution':inst,'year':year})
    return out

def post_case(s,c):
    organ=c['orgName']; encoded_org=organ.replace(',', '^')
    data={
        'is_detail':'yes','srchinit':'ritem','afterKeyword':'','size':'10','from':'1','sort':'SCORE','order':'DESC',
        'kikwancode':'','kikwanname':'','query_type':c['query_type'],'keyword':c['keyword'],
        'detailOneKeyword':'','detailMatchKeyword':'','detailExceptKeyword':'',
        'org_nm':encoded_org,'org_nm_fst':encoded_org,'orgName':organ,
        'prod_yr_start':'','prod_yr_end':'','opn_yn':'','opn_yn_fst':'','arch_down':'','arch_down_fst':'',
        'record_type':'','doc_type':'','doc_type_fst':'','type':'','is_elect':'',
        'mng_no_start':'','mng_no_end':'','prod_dt_start':'','prod_dt_end':'','sihang_dt_start':'','sihang_dt_end':''
    }
    try:
        r=s.post(URL,data=data,timeout=30,stream=True,allow_redirects=True);b=bytearray();ov=False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:continue
                if len(b)+len(chunk)>MAX:ov=True;break
                b.extend(chunk)
        finally:r.close()
        text,enc=dec(bytes(b));return {'http':r.status_code,'final_url':str(r.url),'body':bytes(b),'text':text,'encoding':enc,'overflow':ov,'error':None}
    except requests.RequestException as e:return {'http':None,'final_url':URL,'body':b'','text':'','encoding':None,'overflow':False,'error':f'{type(e).__name__}: {e}'}

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL SEARCH CONTRACT REPLAY POSITIVE CONTROL - S200');print('='*60)
    print('Browser contract replay: query_type=ftr default + orgName -> org_nm/org_nm_fst')
    print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];tech=0
    for c in CASES:
        r=post_case(s,c);rows=parse_rows(r['text'])
        if r['error'] or r['overflow'] or r['http']!=200:tech+=1
        expected=c['expect_title_contains'];matches=[x for x in rows if expected and expected in x['title']]
        seongnam_org=[x for x in rows if '성남시' in x['institution']]
        results.append({'label':c['label'],'query_type':c['query_type'],'keyword':c['keyword'],'orgName':c['orgName'],'http':r['http'],'final_url':r['final_url'],'byte_length':len(r['body']),'encoding':r['encoding'],'overflow':r['overflow'],'error':r['error'],'row_count':len(rows),'expected_title':expected,'expected_match_count':len(matches),'seongnam_institution_row_count':len(seongnam_org),'rows':rows[:30]})
        print('CASE:',c['label'],'| TYPE:',c['query_type'],'| KEYWORD:',c['keyword'],'| ORG:',c['orgName'] or '-','| HTTP:',r['http'],'| ROWS:',len(rows),'| EXPECTED:',len(matches),'| SEONGNAM_ORG_ROWS:',len(seongnam_org))
        for x in rows[:10]:print('  ROW:',x)
    by={x['label']:x for x in results}
    ftr_baseline=by['FTR_BASELINE_SEONGNAM']['row_count']>0
    org_positive=by['FTR_ORG_FILTER_POSITIVE']['expected_match_count']>0 and by['FTR_ORG_FILTER_POSITIVE']['seongnam_institution_row_count']>0
    density_rows=by['FTR_ORG_FILTER_DENSITY_DIAGNOSTIC']['row_count']
    semantic='NATIONAL_ARCHIVES_DETAIL_SEARCH_BROWSER_CONTRACT_QUALIFIED' if ftr_baseline and org_positive and tech==0 else 'NATIONAL_ARCHIVES_DETAIL_SEARCH_BROWSER_CONTRACT_PARTIAL'
    out={'step':'STEP 17-21-C-16-8-T-96-S200','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'summary':{'case_count':len(results),'ftr_baseline_resolved':ftr_baseline,'org_filter_positive_control_resolved':org_positive,'org_filtered_development_density_row_count':density_rows,'technical_unknown_count':tech,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'case exact':len(results)==4,'ftr baseline resolved':ftr_baseline,'org filter positive resolved':org_positive,'technical unknown zero':tech==0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S200 National Archives detail-search contract replay positive control failed')
if __name__=='__main__':main()
