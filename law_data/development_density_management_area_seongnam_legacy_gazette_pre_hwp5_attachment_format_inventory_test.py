# -*- coding: utf-8 -*-
"""S134-R1: PRE-HWP5 attachment-format inventory using an existing local current-snapshot row source.

The committed S103 lockfile is identity-only and does not contain all 1,611 row objects. Therefore this
stage must NOT reconstruct PRE rows from that manifest and must NOT recrawl the live list. Instead it
searches existing local JSON outputs produced by the S100-S106 current-snapshot chain, finds a unique
row collection whose full set has 1,611 unique pstSn and whose gazette_number<526 partition has exactly
48 rows, then inventories only official detail/attachment metadata for those 48 identities.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_attachment_format_inventory.json'

EXPECTED_CURRENT_COUNT = 1611
EXPECTED_PRE_COUNT = 48
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
META = 'https://www.seongnam.go.kr/bbs010308/atchFileDetail'
HOST = 'www.seongnam.go.kr'
TIMEOUT = 30
MAX_HTML_BYTES = 4 * 1024 * 1024
MAX_META_BYTES = 4 * 1024 * 1024
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v): return re.sub(r'\s+', ' ', str(v or '')).strip()

def host(url):
    try: return (urlparse(url).hostname or '').lower()
    except Exception: return ''

def bounded_get(session, url, limit, **kwargs):
    r=session.get(url,timeout=TIMEOUT,stream=True,allow_redirects=True,**kwargs)
    buf=bytearray(); overflow=False
    try:
        for chunk in r.iter_content(65536):
            if not chunk: continue
            if len(buf)+len(chunk)>limit: overflow=True; break
            buf.extend(chunk)
    finally: r.close()
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
    for name in names:
        if name.lower() in low: return low[name.lower()]
    return None

def extension(name):
    s=norm(name).lower(); return s.rsplit('.',1)[-1] if '.' in s else 'unknown'

def parse_gazette(v):
    try: return int(v)
    except Exception: return None

def looks_like_row(x):
    return isinstance(x,dict) and norm(x.get('pstSn')) and parse_gazette(x.get('gazette_number')) is not None

def candidate_row_lists(obj):
    found=[]
    def walk(x,path='$'):
        if isinstance(x,dict):
            for k,v in x.items(): walk(v,f'{path}.{k}')
        elif isinstance(x,list):
            if x and sum(1 for y in x if looks_like_row(y)) >= min(10,len(x)):
                rows=[y for y in x if looks_like_row(y)]
                found.append((path,rows))
            # do not recurse into large row arrays; nested fields are irrelevant
            elif len(x)<100:
                for i,v in enumerate(x): walk(v,f'{path}[{i}]')
    walk(obj)
    return found

def discover_current_snapshot_rows():
    candidates=[]
    for path in sorted(OUT_DIR.glob('development_density_management_area_seongnam_legacy_gazette*.json')):
        if path == OUT: continue
        try: obj=json.loads(path.read_text(encoding='utf-8'))
        except Exception: continue
        for jpath,rows in candidate_row_lists(obj):
            pst=[norm(r.get('pstSn')) for r in rows]
            uniq=set(pst)
            pre=[r for r in rows if parse_gazette(r.get('gazette_number')) < 526]
            if len(rows)==EXPECTED_CURRENT_COUNT and len(uniq)==EXPECTED_CURRENT_COUNT and len(pre)==EXPECTED_PRE_COUNT:
                candidates.append((path,jpath,rows))
    if not candidates:
        raise AssertionError('no existing local S100-S106 current-snapshot 1611-row source with PRE=48 found; live recrawl forbidden')
    identities={(str(p),j) for p,j,_ in candidates}
    # Multiple containers are acceptable only if their exact pstSn->gazette identity set is identical.
    sigs={tuple(sorted((norm(r.get('pstSn')),parse_gazette(r.get('gazette_number')),norm(r.get('date'))) for r in rows)) for _,_,rows in candidates}
    if len(sigs)!=1:
        raise AssertionError(f'ambiguous current-snapshot row sources: {sorted(identities)}')
    path,jpath,rows=candidates[0]
    return path,jpath,rows,len(candidates)

def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 ATTACHMENT FORMAT INVENTORY - S134-R1')
    print('='*60)
    print('Live list recrawl: DISABLED')
    print('Attachment binary download: DISABLED')
    print('OCR: DISABLED')
    print('Target-term scan: DISABLED')
    print('Negative evidence: DISABLED')

    source_path,source_json_path,rows,source_match_count=discover_current_snapshot_rows()
    pre=[r for r in rows if parse_gazette(r.get('gazette_number')) < 526]
    print('ROW_SOURCE:',source_path)
    print('ROW_SOURCE_JSON_PATH:',source_json_path)
    print('ROW_SOURCE_MATCH_COUNT:',source_match_count)
    print('CURRENT_ROWS:',len(rows),'PRE_ROWS:',len(pre))

    session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]; request_count=0
    for row in sorted(pre,key=lambda r:(norm(r.get('date')),parse_gazette(r.get('gazette_number')) or 0,norm(r.get('pstSn')))):
        pst=norm(row.get('pstSn'))
        hs,hu,hraw,hov,hct=bounded_get(session,DETAIL_BASE+pst,MAX_HTML_BYTES); request_count+=1
        ms,mu,mraw,mov,mct=bounded_get(session,META,MAX_META_BYTES,params={'pstSn':pst}); request_count+=1
        items=[]; meta_error=''
        if ms==200 and not mov:
            try:
                meta=json.loads(mraw.decode('utf-8',errors='strict')); seen=set()
                for item in flatten_items(meta):
                    fn=norm(field(item,'orginlFileNm','orignlFileNm','streFileNm','fileNm')); no=norm(field(item,'fileNo','file_no','atchFileNo'))
                    ident=(no,fn)
                    if ident in seen: continue
                    seen.add(ident); items.append({'fileNo':no,'filename':fn,'extension':extension(fn)})
            except Exception as exc: meta_error=repr(exc)
        state='ATTACHMENT_METADATA_CAPTURED' if hs==200 and ms==200 and not hov and not mov and not meta_error else 'TECHNICAL_INVENTORY_UNKNOWN'
        rec={'pstSn':pst,'gazette_number':parse_gazette(row.get('gazette_number')),'date':row.get('date'),'title':row.get('title'),'detail_http':hs,'detail_official_host':host(hu)==HOST,'detail_overflow':hov,'detail_content_type':hct,'metadata_http':ms,'metadata_official_host':host(mu)==HOST,'metadata_overflow':mov,'metadata_content_type':mct,'metadata_error':meta_error,'attachment_count':len(items),'attachments':items,'state':state}
        results.append(rec)
        print('GAZETTE:',rec['gazette_number'],'| pstSn:',pst,'| ATTACHMENTS:',[(x['fileNo'],x['filename'],x['extension']) for x in items],'| STATE:',state)

    ext_counts=Counter(); cardinality=Counter(); states=Counter(); no_attachment=[]
    for r in results:
        states[r['state']]+=1; cardinality[str(r['attachment_count'])]+=1
        if not r['attachments']: no_attachment.append(r['pstSn'])
        for a in r['attachments']: ext_counts[a['extension']]+=1

    out={'step':'STEP 17-21-C-16-8-T-36-S134-R1','target_name':'개발밀도관리구역','standard_code':'UQQ700','row_source_path':str(source_path),'row_source_json_path':source_json_path,'row_source_match_count':source_match_count,'summary':{'current_snapshot_row_count':len(rows),'pre_hwp5_row_count':len(results),'request_count':request_count,'state_counts':dict(states),'attachment_cardinality_counts':dict(cardinality),'extension_counts':dict(ext_counts),'no_attachment_row_count':len(no_attachment),'technical_inventory_unknown_count':states.get('TECHNICAL_INVENTORY_UNKNOWN',0),'semantic_state':'PRE_HWP5_ATTACHMENT_FORMAT_INVENTORY_CAPTURED_FROM_EXISTING_CURRENT_SNAPSHOT','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'no_attachment_pstSn':no_attachment,'results':results,'live_list_recrawl_executed':False,'attachment_binary_download_executed':False,'ocr_executed':False,'target_term_scan_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'current snapshot row count exact':len(rows)==EXPECTED_CURRENT_COUNT,'PRE-HWP5 row count exact':len(results)==EXPECTED_PRE_COUNT,'PRE identities unique':len({r['pstSn'] for r in results})==EXPECTED_PRE_COUNT,'request budget exact':request_count==EXPECTED_PRE_COUNT*2,'official hosts only':all(r['detail_official_host'] and r['metadata_official_host'] for r in results),'live list recrawl disabled':not out['live_list_recrawl_executed'],'attachment binary download disabled':not out['attachment_binary_download_executed'],'ocr disabled':not out['ocr_executed'],'target-term scan disabled':not out['target_term_scan_executed'],'candidate promotion disabled':not out['candidate_promotion_allowed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('no_attachment_pstSn:',no_attachment)
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S134-R1 PRE-HWP5 attachment inventory failed')

if __name__=='__main__': main()
