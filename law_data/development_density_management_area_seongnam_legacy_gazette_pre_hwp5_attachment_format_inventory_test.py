# -*- coding: utf-8 -*-
"""S134: inventory attachment formats for the current-snapshot PRE-HWP5 gazette partition.

This stage reads the locked current manifest and scopes exactly rows with gazette_number < 526.
For each row it fetches only the official detail page and attachment metadata endpoint, then inventories
attachment cardinality and filename extensions. No attachment binary is downloaded, no OCR is used,
and no target-term scan or legal/SITE promotion is allowed.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
MANIFEST_DIR = BASE / 'law_data' / 'manifests'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_attachment_format_inventory.json'

EXPECTED_PRE_COUNT = 48
DETAIL_BASE = 'https://www.seongnam.go.kr/bbs010308/'
META = 'https://www.seongnam.go.kr/bbs010308/atchFileDetail'
HOST = 'www.seongnam.go.kr'
TIMEOUT = 30
MAX_HTML_BYTES = 4 * 1024 * 1024
MAX_META_BYTES = 4 * 1024 * 1024
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def host(url):
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def bounded_get(session, url, limit, **kwargs):
    r = session.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True, **kwargs)
    buf = bytearray(); overflow = False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            if len(buf) + len(chunk) > limit:
                overflow = True
                break
            buf.extend(chunk)
    finally:
        r.close()
    return r.status_code, str(r.url), bytes(buf), overflow, r.headers.get('Content-Type', '')


def flatten_items(obj):
    found=[]
    def walk(x):
        if isinstance(x, dict):
            keys={str(k).lower() for k in x}
            if any(k in keys for k in ['fileno','file_no','orginlfilenm','orignlfilenm','strefilenm']):
                found.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(obj)
    return found


def field(d, *names):
    low={str(k).lower(): v for k,v in d.items()}
    for name in names:
        if name.lower() in low:
            return low[name.lower()]
    return None


def extension(name):
    s=norm(name).lower()
    return s.rsplit('.',1)[-1] if '.' in s else 'unknown'


def parse_gazette(v):
    try:
        return int(v)
    except Exception:
        return None


def find_manifest():
    matches=sorted(MANIFEST_DIR.glob('seongnam_legacy_gazette_snapshot_20260903_*.json'))
    if len(matches) != 1:
        raise AssertionError(f'expected exactly one locked manifest, found {len(matches)}')
    return matches[0]


def manifest_rows(obj):
    for key in ['rows','canonical_gazette_rows','records']:
        rows=obj.get(key)
        if isinstance(rows,list) and rows:
            return rows
    raise AssertionError('locked manifest row collection not found')


def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 ATTACHMENT FORMAT INVENTORY - S134')
    print('='*60)
    print('Attachment binary download: DISABLED')
    print('OCR: DISABLED')
    print('Target-term scan: DISABLED')
    print('Negative evidence: DISABLED')

    manifest=find_manifest()
    obj=json.loads(manifest.read_text(encoding='utf-8'))
    rows=manifest_rows(obj)
    pre=[r for r in rows if (parse_gazette(r.get('gazette_number')) is not None and parse_gazette(r.get('gazette_number')) < 526)]
    if len(pre) != EXPECTED_PRE_COUNT:
        raise AssertionError(f'PRE-HWP5 row count mismatch: {len(pre)}')

    session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]; request_count=0
    for row in sorted(pre,key=lambda r:(norm(r.get('date')),parse_gazette(r.get('gazette_number')) or 0,norm(r.get('pstSn')))):
        pst=norm(row.get('pstSn'))
        hs,hu,hraw,hov,hct=bounded_get(session,DETAIL_BASE+pst,MAX_HTML_BYTES); request_count+=1
        ms,mu,mraw,mov,mct=bounded_get(session,META,MAX_META_BYTES,params={'pstSn':pst}); request_count+=1
        items=[]; meta_error=''
        if ms==200 and not mov:
            try:
                meta=json.loads(mraw.decode('utf-8',errors='strict'))
                seen=set()
                for item in flatten_items(meta):
                    fn=norm(field(item,'orginlFileNm','orignlFileNm','streFileNm','fileNm'))
                    no=norm(field(item,'fileNo','file_no','atchFileNo'))
                    ident=(no,fn)
                    if ident in seen: continue
                    seen.add(ident)
                    items.append({'fileNo':no,'filename':fn,'extension':extension(fn)})
            except Exception as exc:
                meta_error=repr(exc)
        state='ATTACHMENT_METADATA_CAPTURED' if hs==200 and ms==200 and not hov and not mov and not meta_error else 'TECHNICAL_INVENTORY_UNKNOWN'
        rec={'pstSn':pst,'gazette_number':parse_gazette(row.get('gazette_number')),'date':row.get('date'),'title':row.get('title'),'detail_http':hs,'detail_official_host':host(hu)==HOST,'detail_overflow':hov,'detail_content_type':hct,'metadata_http':ms,'metadata_official_host':host(mu)==HOST,'metadata_overflow':mov,'metadata_content_type':mct,'metadata_error':meta_error,'attachment_count':len(items),'attachments':items,'state':state}
        results.append(rec)
        print('GAZETTE:',rec['gazette_number'],'| pstSn:',pst,'| ATTACHMENTS:',[(x['fileNo'],x['filename'],x['extension']) for x in items],'| STATE:',state)

    ext_counts=Counter()
    cardinality=Counter()
    states=Counter()
    no_attachment=[]
    for r in results:
        states[r['state']]+=1
        cardinality[str(r['attachment_count'])]+=1
        if not r['attachments']:
            no_attachment.append(r['pstSn'])
        for a in r['attachments']:
            ext_counts[a['extension']]+=1

    out={'step':'STEP 17-21-C-16-8-T-36-S134','target_name':'개발밀도관리구역','standard_code':'UQQ700','manifest_path':str(manifest),'summary':{'pre_hwp5_row_count':len(results),'request_count':request_count,'state_counts':dict(states),'attachment_cardinality_counts':dict(cardinality),'extension_counts':dict(ext_counts),'no_attachment_row_count':len(no_attachment),'technical_inventory_unknown_count':states.get('TECHNICAL_INVENTORY_UNKNOWN',0),'semantic_state':'PRE_HWP5_ATTACHMENT_FORMAT_INVENTORY_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'no_attachment_pstSn':no_attachment,'results':results,'attachment_binary_download_executed':False,'ocr_executed':False,'target_term_scan_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')

    vals={'PRE-HWP5 row count exact':len(results)==EXPECTED_PRE_COUNT,'request budget exact':request_count==EXPECTED_PRE_COUNT*2,'official hosts only':all(r['detail_official_host'] and r['metadata_official_host'] for r in results),'attachment binary download disabled':not out['attachment_binary_download_executed'],'ocr disabled':not out['ocr_executed'],'target-term scan disabled':not out['target_term_scan_executed'],'candidate promotion disabled':not out['candidate_promotion_allowed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('no_attachment_pstSn:',no_attachment)
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S134 PRE-HWP5 attachment inventory failed')

if __name__=='__main__': main()
