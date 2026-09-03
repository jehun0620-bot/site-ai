# -*- coding: utf-8 -*-
"""S138: bounded official alternative-representation probe for the 47 PRE-HWP5 HWP3 rows.

HWP3 parsing heuristics were not qualified by S136/S137. This stage therefore does not parse HWP3.
For each exact S135 HWP3 identity, fetch only the official detail page and attachment metadata and
inventory whether any non-HWP representation (PDF/HTML/TXT/etc.) is available on the current official
surface. No HWP binary download, no OCR, no target-term scan, no decryption, no legal negative evidence,
and no SITE/runtime promotion.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'
S135=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification.json'
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp3_alternative_representation_probe.json'
DETAIL_BASE='https://www.seongnam.go.kr/bbs010308/'
META='https://www.seongnam.go.kr/bbs010308/atchFileDetail'
HOST='www.seongnam.go.kr'
TIMEOUT=30
MAX_HTML_BYTES=4*1024*1024
MAX_META_BYTES=4*1024*1024
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
EXPECTED=47


def norm(v): return re.sub(r'\s+',' ',str(v or '')).strip()

def host(url):
    try:return (urlparse(url).hostname or '').lower()
    except Exception:return ''

def bounded_get(session,url,limit,**kwargs):
    r=session.get(url,timeout=TIMEOUT,stream=True,allow_redirects=True,**kwargs)
    buf=bytearray(); overflow=False
    try:
        for chunk in r.iter_content(65536):
            if not chunk: continue
            if len(buf)+len(chunk)>limit: overflow=True; break
            buf.extend(chunk)
    finally:r.close()
    return r.status_code,str(r.url),bytes(buf),overflow,r.headers.get('Content-Type','')

def flatten_items(obj):
    found=[]
    def walk(x):
        if isinstance(x,dict):
            keys={str(k).lower() for k in x}
            if any(k in keys for k in ['fileno','file_no','orginlfilenm','orignlfilenm','strefilenm']): found.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj); return found

def field(d,*names):
    low={str(k).lower():v for k,v in d.items()}
    for n in names:
        if n.lower() in low:return low[n.lower()]
    return None

def ext(name):
    s=norm(name).lower(); return s.rsplit('.',1)[-1] if '.' in s else 'unknown'

def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 HWP3 ALTERNATIVE REPRESENTATION PROBE - S138')
    print('='*60)
    print('HWP binary download: DISABLED')
    print('HWP3 parsing: DISABLED')
    print('Target-term scan: DISABLED')
    print('OCR/decryption: DISABLED')
    print('Negative evidence: DISABLED')

    src=json.loads(S135.read_text(encoding='utf-8'))
    rows=[r for r in (src.get('results') or []) if r.get('signature')=='HWP3']
    if len(rows)!=EXPECTED: raise AssertionError(f'expected 47 HWP3 rows, got {len(rows)}')
    session=requests.Session();session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[];request_count=0
    for r in rows:
        pst=norm(r.get('pstSn'))
        hs,hu,hraw,hov,hct=bounded_get(session,DETAIL_BASE+pst,MAX_HTML_BYTES);request_count+=1
        ms,mu,mraw,mov,mct=bounded_get(session,META,MAX_META_BYTES,params={'pstSn':pst});request_count+=1
        items=[];err=''
        if ms==200 and not mov:
            try:
                obj=json.loads(mraw.decode('utf-8',errors='strict'));seen=set()
                for it in flatten_items(obj):
                    fn=norm(field(it,'orginlFileNm','orignlFileNm','streFileNm','fileNm'));no=norm(field(it,'fileNo','file_no','atchFileNo')); ident=(no,fn)
                    if ident in seen:continue
                    seen.add(ident);items.append({'fileNo':no,'filename':fn,'extension':ext(fn)})
            except Exception as exc:err=repr(exc)
        alt=[x for x in items if x['extension'] not in {'hwp','unknown'}]
        if alt:state='OFFICIAL_ALTERNATIVE_REPRESENTATION_FOUND'
        elif hs==200 and ms==200 and not hov and not mov and not err:state='NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE'
        else:state='TECHNICAL_PROBE_UNKNOWN'
        rec={'pstSn':pst,'gazette_number':r.get('gazette_number'),'date':r.get('date'),'original_filename':r.get('filename'),'detail_http':hs,'detail_official_host':host(hu)==HOST,'detail_overflow':hov,'detail_content_type':hct,'metadata_http':ms,'metadata_official_host':host(mu)==HOST,'metadata_overflow':mov,'metadata_content_type':mct,'metadata_error':err,'attachments':items,'alternative_representations':alt,'state':state}
        results.append(rec)
        print('GAZETTE:',rec['gazette_number'],'| pstSn:',pst,'| STATE:',state,'| ATTACHMENTS:',[(x['filename'],x['extension']) for x in items])

    states=Counter(r['state'] for r in results)
    out={'step':'STEP 17-21-C-16-8-T-36-S138','target_name':'개발밀도관리구역','standard_code':'UQQ700','summary':{'hwp3_input_count':len(results),'request_count':request_count,'state_counts':dict(states),'alternative_representation_found_count':states.get('OFFICIAL_ALTERNATIVE_REPRESENTATION_FOUND',0),'no_alternative_current_surface_count':states.get('NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE',0),'technical_probe_unknown_count':states.get('TECHNICAL_PROBE_UNKNOWN',0),'semantic_state':'PRE_HWP5_HWP3_ALTERNATIVE_REPRESENTATION_PROBED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'results':results,'hwp_binary_download_executed':False,'hwp3_parsing_executed':False,'target_term_scan_executed':False,'ocr_executed':False,'decryption_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'47 HWP3 identities exact':len(results)==EXPECTED,'request budget exact':request_count==EXPECTED*2,'official hosts only':all(r['detail_official_host'] and r['metadata_official_host'] for r in results),'HWP binary download disabled':not out['hwp_binary_download_executed'],'HWP3 parsing disabled':not out['hwp3_parsing_executed'],'target-term scan disabled':not out['target_term_scan_executed'],'OCR disabled':not out['ocr_executed'],'decryption disabled':not out['decryption_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items():print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items():print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()):raise AssertionError('S138 HWP3 alternative representation probe failed')

if __name__=='__main__':main()
