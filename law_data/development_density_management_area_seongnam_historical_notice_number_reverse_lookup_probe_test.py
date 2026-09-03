# -*- coding: utf-8 -*-
"""S141: bounded Seongnam historical notice-number/title reverse lookup probe for UQQ700.

This stage deliberately leaves the already-closed legacy gazette current-snapshot corpus and probes a
separate official source family: Seongnam municipal notice/public-notice search. It uses the known
/pm010301 search contract with title/content modes and a small target/legal-identity query matrix.
Search hits are discovery candidates only. No document hit, search miss, or empty result may produce
legal TRUE/FALSE. No runtime/SITE promotion.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'
OUT=OUT_DIR/'development_density_management_area_seongnam_historical_notice_number_reverse_lookup_probe.json'

SEARCH='https://www.seongnam.go.kr/pm010301'
HOST='www.seongnam.go.kr'
TIMEOUT=30
MAX_BYTES=8*1024*1024
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'

QUERIES=[
    '개발밀도관리구역',
    '개발밀도 관리구역',
    '개발밀도관리구역 지정',
    '개발밀도관리구역 고시',
    '개발밀도관리구역 결정',
    '개발밀도관리구역 변경',
    '도시관리계획 개발밀도관리구역',
    '개발밀도',
]
SEARCH_KEYS=['sj','cn']
EXPECTED_REQUESTS=len(QUERIES)*len(SEARCH_KEYS)
ROW_RE=re.compile(r"f_view\(['\"]?(\d+)['\"]?\)",re.I)
TAG_RE=re.compile(r'<[^>]+>')
TR_RE=re.compile(r'<tr\b[^>]*>(.*?)</tr>',re.I|re.S)
DIRECT_RE=re.compile(r'개발\s*밀도\s*관리\s*구역|UQQ700',re.I)
RELATED_RE=re.compile(r'개발\s*밀도',re.I)
NOTICE_NO_RE=re.compile(r'(?:성남시\s*)?(?:고시|공고)\s*제?\s*(\d{4})\s*[-－]\s*(\d+)\s*호?',re.I)


def norm(v): return re.sub(r'\s+',' ',str(v or '')).strip()

def host(url):
    try:return (urlparse(url).hostname or '').lower()
    except Exception:return ''

def get(session,params):
    r=session.get(SEARCH,params=params,timeout=TIMEOUT,stream=True,allow_redirects=True)
    buf=bytearray();overflow=False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:continue
            if len(buf)+len(chunk)>MAX_BYTES:overflow=True;break
            buf.extend(chunk)
    finally:r.close()
    return r.status_code,str(r.url),bytes(buf),overflow,r.headers.get('Content-Type','')

def strip_markup(s):
    return norm(html.unescape(TAG_RE.sub(' ',s)))

def parse_rows(raw):
    text=raw.decode('utf-8',errors='ignore')
    found=[]
    for tr in TR_RE.findall(text):
        ids=ROW_RE.findall(tr)
        if not ids:continue
        row_text=strip_markup(tr)
        for doc_id in ids:
            found.append({'document_id':doc_id,'row_text':row_text,'detail_url':urljoin(SEARCH+'/',doc_id)})
    # fallback if table structure changes: capture identity with nearby text window
    if not found:
        for m in ROW_RE.finditer(text):
            a=max(0,m.start()-600);b=min(len(text),m.end()+600)
            found.append({'document_id':m.group(1),'row_text':strip_markup(text[a:b]),'detail_url':urljoin(SEARCH+'/',m.group(1))})
    dedup={}
    for x in found:
        prev=dedup.get(x['document_id'])
        if prev is None or len(x['row_text'])>len(prev['row_text']):dedup[x['document_id']]=x
    return list(dedup.values())

def classify(text):
    direct=bool(DIRECT_RE.search(text)); related=bool(RELATED_RE.search(text)); nums=NOTICE_NO_RE.findall(text)
    if direct:return 'DIRECT_CANDIDATE',nums
    if related:return 'RELATED_CANDIDATE',nums
    return 'NON_TARGET_RESULT',nums

def main():
    print('='*60)
    print('SEONGNAM HISTORICAL NOTICE-NUMBER REVERSE LOOKUP PROBE - S141')
    print('='*60)
    print('Source family: OFFICIAL MUNICIPAL NOTICE / pm010301')
    print('Legacy gazette recrawl: DISABLED')
    print('Negative evidence: DISABLED')
    print('Legal absence inference: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    session=requests.Session();session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    requests_log=[];candidates={};request_count=0
    for key in SEARCH_KEYS:
        for query in QUERIES:
            params={'cntPerPage':'100','curPage':'1','sortType':'DESC','srchKey':key,'srchText':query}
            hs,hu,raw,overflow,ct=get(session,params);request_count+=1
            rows=parse_rows(raw) if hs==200 and not overflow else []
            print('SEARCH_KEY:',key,'| QUERY:',query,'| HTTP:',hs,'| ROWS:',len(rows),'| OVERFLOW:',overflow)
            requests_log.append({'search_key':key,'query':query,'http':hs,'url':hu,'official_host':host(hu)==HOST,'overflow':overflow,'content_type':ct,'row_count':len(rows)})
            for row in rows:
                cls,nums=classify(row['row_text'])
                if cls=='NON_TARGET_RESULT':continue
                rec=candidates.setdefault(row['document_id'],{'document_id':row['document_id'],'detail_url':row['detail_url'],'classification':cls,'row_text':row['row_text'],'notice_numbers':[],'provenance':[]})
                if cls=='DIRECT_CANDIDATE':rec['classification']='DIRECT_CANDIDATE'
                rec['notice_numbers']=sorted(set(rec['notice_numbers']+[f'{y}-{n}' for y,n in nums]))
                rec['provenance'].append({'search_key':key,'query':query})

    vals=list(candidates.values())
    counts=Counter(x['classification'] for x in vals)
    out={'step':'STEP 17-21-C-16-8-T-37-S141','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'SEONGNAM_OFFICIAL_MUNICIPAL_NOTICE','source_url':SEARCH,'summary':{'request_count':request_count,'candidate_document_count':len(vals),'direct_candidate_count':counts.get('DIRECT_CANDIDATE',0),'related_candidate_count':counts.get('RELATED_CANDIDATE',0),'semantic_state':'SEONGNAM_HISTORICAL_NOTICE_NUMBER_REVERSE_LOOKUP_PROBED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'requests':requests_log,'candidates':vals,'legacy_gazette_recrawl_executed':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nCANDIDATES')
    for x in vals:
        print(x['classification'],'|',x['document_id'],'|',x['notice_numbers'],'|',x['row_text'][:300])
    print('\nSUMMARY')
    for k,v in out['summary'].items():print(f'{k}: {v}')
    print('Output:',OUT)
    checks={'request budget exact':request_count==EXPECTED_REQUESTS,'official hosts only':all(x['official_host'] for x in requests_log),'no overflow':all(not x['overflow'] for x in requests_log),'legacy gazette recrawl disabled':not out['legacy_gazette_recrawl_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'legal absence inference disabled':not out['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION')
    for k,v in checks.items():print(f'{k}: {v}')
    print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S141 notice reverse lookup probe failed')

if __name__=='__main__':main()
