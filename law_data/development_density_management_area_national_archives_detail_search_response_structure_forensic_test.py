# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_search_response_structure_forensic.json'
GET_URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
POST_URL='https://www.archives.go.kr/next/srch/uniDetailSearch.do'
UA='Mozilla/5.0'; MAX=16*1024*1024


def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def fetch(method,url,s,**kwargs):
    try:
        r=s.request(method,url,timeout=30,stream=True,allow_redirects=True,**kwargs);b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        t,e=dec(bytes(b));return {'http':r.status_code,'url':str(r.url),'history':[{'status':x.status_code,'url':str(x.url),'location':x.headers.get('Location')} for x in r.history],'body':bytes(b),'text':t,'encoding':e,'overflow':ov,'headers':dict(r.headers),'error':None}
    except requests.RequestException as ex:return {'http':None,'url':url,'history':[],'body':b'','text':'','encoding':None,'overflow':False,'headers':{},'error':f'{type(ex).__name__}: {ex}'}

def markers(text):
    plain=clean(text)
    return {
        'result_row_count':len(re.findall(r'<div\s+class=["\']result-row["\']',text,re.I)),
        'show_item_calls':len(re.findall(r'showItemDetailWithQuery\s*\(',text,re.I)),
        'list_archive_endpoint_mentions':text.count('/next/newsearch/listArchiveSearchResult.do'),
        'list_sub_endpoint_mentions':text.count('/next/newsearch/listArchiveSubSearch.do'),
        'search_total_up_mentions':text.count('/next/newsearch/searchTotalUp.do'),
        'no_result_marker':bool(re.search(r'검색결과가\s*없|검색\s*결과가\s*없|검색\s*조건을\s*다시',plain)),
        'detail_search_form':bool(re.search(r'detailSearchForm',text,re.I)),
        'total_search_form':bool(re.search(r'totalSearchForm',text,re.I)),
        'query_echo_seongnam':'성남시' in plain,
        'title_positive':'성남시 도로명주소 안내도' in plain,
        'script_repage':bool(re.search(r'function\s+rePage\s*\(',text)),
        'script_list_resizing':bool(re.search(r'function\s+listResizing\s*\(',text)),
    }

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL SEARCH RESPONSE STRUCTURE FORENSIC - S201');print('='*60)
    print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    getr=fetch('GET',GET_URL,s,params={'query_type':'keyword','is_detail':'yes','upside_query':'성남시','keyword':'성남시','srchinit':'ritem'})
    data={'is_detail':'yes','srchinit':'ritem','afterKeyword':'','size':'10','from':'1','sort':'SCORE','order':'DESC','kikwancode':'','kikwanname':'','query_type':'ftr','keyword':'성남시','detailOneKeyword':'','detailMatchKeyword':'','detailExceptKeyword':'','org_nm':'','org_nm_fst':'','orgName':'','prod_yr_start':'','prod_yr_end':'','opn_yn':'','opn_yn_fst':'','arch_down':'','arch_down_fst':'','record_type':'','doc_type':'','doc_type_fst':'','type':'','is_elect':'','mng_no_start':'','mng_no_end':'','prod_dt_start':'','prod_dt_end':'','sihang_dt_start':'','sihang_dt_end':''}
    postr=fetch('POST',POST_URL,s,data=data,headers={'Referer':getr['url'],'Origin':'https://www.archives.go.kr'})
    gm=markers(getr['text']);pm=markers(postr['text'])
    print('GET  HTTP:',getr['http'],'| BYTES:',len(getr['body']),'| URL:',getr['url'],'| HISTORY:',getr['history'])
    print('GET  MARKERS:',gm)
    print('POST HTTP:',postr['http'],'| BYTES:',len(postr['body']),'| URL:',postr['url'],'| HISTORY:',postr['history'])
    print('POST MARKERS:',pm)
    endpoint_literals=sorted(set(re.findall(r'["\'](/next/[^"\']+\.(?:do|jsp)(?:\?[^"\']*)?)["\']',postr['text'],re.I)))
    script_snippets=[]
    for pat in ['listArchiveSearchResult.do','rePage','listResizing','uniDetailSearch.do','result-row']:
        for m in re.finditer(re.escape(pat),postr['text'],re.I):
            frag=clean(postr['text'][max(0,m.start()-700):min(len(postr['text']),m.end()+1200)])
            if frag not in script_snippets:script_snippets.append(frag)
            if len(script_snippets)>=12:break
        if len(script_snippets)>=12:break
    print('ENDPOINT_LITERALS:',endpoint_literals)
    print('POST STRUCTURE SNIPPETS:')
    for x in script_snippets:print('  ',x[:1800])
    semantic='NATIONAL_ARCHIVES_DETAIL_SEARCH_RESPONSE_STRUCTURE_CAPTURED'
    out={'step':'STEP 17-21-C-16-8-T-97-S201','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','get_positive_control':{'http':getr['http'],'final_url':getr['url'],'byte_length':len(getr['body']),'encoding':getr['encoding'],'history':getr['history'],'markers':gm},'post_detail_search':{'http':postr['http'],'final_url':postr['url'],'byte_length':len(postr['body']),'encoding':postr['encoding'],'history':postr['history'],'markers':pm},'endpoint_literals':endpoint_literals,'structure_snippets':script_snippets,'summary':{'semantic_state':semantic,'post_result_rows_rendered_inline':pm['result_row_count']>0,'post_mentions_result_ajax_endpoint':pm['list_archive_endpoint_mentions']>0,'post_is_intermediate_or_shell':pm['result_row_count']==0 and pm['list_archive_endpoint_mentions']>0,'technical_unknown_count':sum(1 for r in [getr,postr] if r['error'] or r['overflow'] or r['http']!=200),'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'get 200':getr['http']==200,'post 200':postr['http']==200,'overflow false':not getr['overflow'] and not postr['overflow'],'get positive rows observed':gm['result_row_count']>0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S201 National Archives detail-search response structure forensic failed')
if __name__=='__main__':main()
