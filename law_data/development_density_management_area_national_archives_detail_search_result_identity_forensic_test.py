# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_search_result_identity_forensic.json'
GET_URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
POST_URL='https://www.archives.go.kr/next/srch/uniDetailSearch.do'
UA='Mozilla/5.0'; MAX=16*1024*1024

CALLS=[
    ('showDetailWithQuery', re.compile(r"showDetailWithQuery\('([^']+)','([^']+)'(?:,'([^']*)')?\)", re.I)),
    ('showItemDetailWithQuery', re.compile(r"showItemDetailWithQuery\('([^']+)','([^']+)','([^']+)'(?:,'([^']*)','([^']*)')?\)", re.I)),
]

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
        t,e=dec(bytes(b));return {'http':r.status_code,'url':str(r.url),'body':bytes(b),'text':t,'encoding':e,'overflow':ov,'error':None}
    except requests.RequestException as ex:return {'http':None,'url':url,'body':b'','text':'','encoding':None,'overflow':False,'error':f'{type(ex).__name__}: {ex}'}

def nearby(text,start,end,radius=1400):
    return text[max(0,start-radius):min(len(text),end+radius)]

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL SEARCH RESULT IDENTITY FORENSIC - S202');print('='*60)
    print('Purpose: recover POST-result DOM/identity contract; no UQQ700 bulk search')
    print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    pre=fetch('GET',GET_URL,s,params={'query_type':'keyword','is_detail':'yes','upside_query':'성남시','keyword':'성남시','srchinit':'ritem'})
    data={'is_detail':'yes','srchinit':'ritem','afterKeyword':'','size':'10','from':'1','sort':'SCORE','order':'DESC','kikwancode':'','kikwanname':'','query_type':'ftr','keyword':'성남시','detailOneKeyword':'','detailMatchKeyword':'','detailExceptKeyword':'','org_nm':'','org_nm_fst':'','orgName':'','prod_yr_start':'','prod_yr_end':'','opn_yn':'','opn_yn_fst':'','arch_down':'','arch_down_fst':'','record_type':'','doc_type':'','doc_type_fst':'','type':'','is_elect':'','mng_no_start':'','mng_no_end':'','prod_dt_start':'','prod_dt_end':'','sihang_dt_start':'','sihang_dt_end':''}
    post=fetch('POST',POST_URL,s,data=data,headers={'Referer':pre['url'],'Origin':'https://www.archives.go.kr'})
    text=post['text']; calls=[]
    for fn,pat in CALLS:
        for m in pat.finditer(text):
            frag=nearby(text,m.start(),m.end())
            plain=clean(frag)
            titles=[]
            for tp in [r'class=["\']file-title["\'][^>]*>([\s\S]{0,700}?)</a>',r'<a[^>]*onclick=["\'][^"\']*'+fn+r'[^"\']*["\'][^>]*>([\s\S]{0,700}?)</a>',r'<strong[^>]*>([\s\S]{0,500}?)</strong>']:
                tm=re.search(tp,frag,re.I)
                if tm:
                    t=clean(tm.group(1))
                    if t and t not in titles:titles.append(t)
            calls.append({'function':fn,'args':list(m.groups()),'titles':titles[:5],'context':plain[:2500]})
    unique=[];seen=set()
    for c in calls:
        key=(c['function'],tuple(c['args']))
        if key in seen:continue
        seen.add(key);unique.append(c)
    class_counts={}
    for m in re.finditer(r'class=["\']([^"\']+)["\']',text,re.I):
        for cls in m.group(1).split():class_counts[cls]=class_counts.get(cls,0)+1
    interesting_classes=sorted(class_counts.items(),key=lambda x:(-x[1],x[0]))[:100]
    onclick_functions={}
    for m in re.finditer(r'onclick=["\']([^"\']+)["\']',text,re.I):
        body=html.unescape(m.group(1)); fm=re.match(r'\s*(?:javascript:)?\s*([A-Za-z_$][\w$]*)\s*\(',body)
        if fm:onclick_functions[fm.group(1)]=onclick_functions.get(fm.group(1),0)+1
    resultish=[]
    for pat in [r'<li\b[^>]*class=["\'][^"\']*(?:search|result|record|file)[^"\']*["\'][^>]*>[\s\S]{0,5000}?</li>',r'<div\b[^>]*class=["\'][^"\']*(?:search|result|record|file)[^"\']*["\'][^>]*>[\s\S]{0,5000}?</div>']:
        for m in re.finditer(pat,text,re.I):
            p=clean(m.group(0))
            if '성남' in p or 'showDetailWithQuery' in m.group(0) or 'showItemDetailWithQuery' in m.group(0):
                if p not in resultish:resultish.append(p[:3000])
            if len(resultish)>=20:break
        if len(resultish)>=20:break
    print('POST HTTP:',post['http'],'| BYTES:',len(post['body']),'| ENCODING:',post['encoding'],'| OVERFLOW:',post['overflow'])
    print('UNIQUE CALL COUNT:',len(unique))
    for c in unique[:30]:print('CALL:',c)
    print('ONCLICK FUNCTIONS:',onclick_functions)
    print('INTERESTING CLASSES:',interesting_classes)
    print('RESULTISH BLOCKS:')
    for x in resultish[:12]:print('  ',x)
    out={'step':'STEP 17-21-C-16-8-T-98-S202','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','post_http':post['http'],'post_final_url':post['url'],'post_byte_length':len(post['body']),'encoding':post['encoding'],'overflow':post['overflow'],'identity_calls':unique,'onclick_functions':onclick_functions,'class_counts_top':interesting_classes,'resultish_blocks':resultish,'summary':{'identity_call_count':len(unique),'show_detail_with_query_count':sum(c['function']=='showDetailWithQuery' for c in unique),'show_item_detail_with_query_count':sum(c['function']=='showItemDetailWithQuery' for c in unique),'resultish_block_count':len(resultish),'semantic_state':'NATIONAL_ARCHIVES_DETAIL_SEARCH_RESULT_IDENTITY_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'post 200':post['http']==200,'overflow false':not post['overflow'],'identity calls observed':len(unique)>0,'showDetailWithQuery observed':out['summary']['show_detail_with_query_count']>0,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S202 National Archives detail-search result identity forensic failed')
if __name__=='__main__':main()
