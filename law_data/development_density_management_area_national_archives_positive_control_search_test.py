# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urlencode, urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_positive_control_search.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'
QUERIES=['성남시','성남시 고시','성남시보']
MAX=16*1024*1024


def fetch(s,query):
    params={'query_type':'keyword','is_detail':'yes','upside_query':query,'keyword':query,'beforeKeyword':'','afterKeyword':'','doc_type':'','srchinit':'ritem'}
    try:
        r=s.get(URL,params=params,timeout=30,stream=True,allow_redirects=True)
        b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c:continue
                if len(b)+len(c)>MAX:ov=True;break
                b.extend(c)
        finally:r.close()
        return {'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'body':bytes(b),'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:return {'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':URL,'body':b'','error':f'{type(e).__name__}: {e}'}

def dec(b):
    for enc in ('utf-8','euc-kr','cp949'):
        try:return b.decode(enc),enc
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def parse(text,base_url,query):
    anchors=[]
    for m in re.finditer(r'<a\b([^>]*)>([\s\S]*?)</a>',text,re.I):
        attrs=m.group(1); label=clean(m.group(2))
        hm=re.search(r'href=["\']([^"\']+)',attrs,re.I)
        href=html.unescape(hm.group(1)) if hm else ''
        low=(label+' '+href).lower()
        if label and (query in label or 'detail' in low or 'view' in low or 'record' in low or 'search' in low):
            anchors.append({'label':label[:500],'href_raw':href,'href_resolved':urljoin(base_url,href) if href and not href.lower().startswith('javascript:') else href})
        if len(anchors)>=100:break
    text_plain=clean(text)
    query_echo=query in text_plain or query in text
    no_result=bool(re.search(r'검색\s*결과가\s*없|검색결과\s*없|조회된\s*자료가\s*없',text,re.I))
    result_count_candidates=[]
    for pat in [r'검색결과[^0-9]{0,30}([0-9][0-9,]*)\s*건',r'총\s*([0-9][0-9,]*)\s*건',r'전체\s*([0-9][0-9,]*)\s*건']:
        result_count_candidates.extend(re.findall(pat,text,re.I))
    return {'query_echo':query_echo,'no_result_marker':no_result,'result_count_candidates':result_count_candidates[:20],'anchor_candidates':anchors[:50],'title_occurrence_count':text.count(query)}

def main():
    print('='*60);print('NATIONAL ARCHIVES POSITIVE CONTROL SEARCH - S190');print('='*60)
    print('Queries:',QUERIES);print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]
    for q in QUERIES:
        r=fetch(s,q);text,encoding=dec(r['body']);p=parse(text,r['url'],q)
        state='POSITIVE_CONTROL_RESOLVED' if r['http']==200 and p['query_echo'] and not p['no_result_marker'] else ('TECHNICAL_REQUEST_UNKNOWN' if r['state']=='TECHNICAL_REQUEST_UNKNOWN' else 'POSITIVE_CONTROL_NOT_RESOLVED')
        row={'query':q,'state':state,'http':r['http'],'final_url':r['url'],'byte_length':len(r['body']),'encoding':encoding,'query_echo':p['query_echo'],'no_result_marker':p['no_result_marker'],'result_count_candidates':p['result_count_candidates'],'title_occurrence_count':p['title_occurrence_count'],'anchor_candidates':p['anchor_candidates'],'error':r['error']};results.append(row)
        print('QUERY:',q,'| STATE:',state,'| HTTP:',r['http'],'| BYTES:',len(r['body']),'| ECHO:',p['query_echo'],'| NO_RESULT:',p['no_result_marker'],'| COUNTS:',p['result_count_candidates'][:5],'| ANCHORS:',len(p['anchor_candidates']))
        for a in p['anchor_candidates'][:10]:print('  ANCHOR:',a)
    resolved=sum(x['state']=='POSITIVE_CONTROL_RESOLVED' for x in results);tech=sum(x['state']=='TECHNICAL_REQUEST_UNKNOWN' for x in results)
    out={'step':'STEP 17-21-C-16-8-T-86-S190','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','results':results,'summary':{'query_count':len(results),'resolved_count':resolved,'technical_unknown_count':tech,'semantic_state':'NATIONAL_ARCHIVES_POSITIVE_CONTROL_SEARCH_QUALIFIED' if resolved==len(results) else 'NATIONAL_ARCHIVES_POSITIVE_CONTROL_SEARCH_PARTIAL','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'query exact':len(results)==len(QUERIES),'technical unknown zero':tech==0,'at least one positive control resolved':resolved>=1,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S190 National Archives positive-control search failed')
if __name__=='__main__':main()
