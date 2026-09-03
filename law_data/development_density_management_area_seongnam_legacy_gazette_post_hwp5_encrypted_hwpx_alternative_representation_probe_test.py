# -*- coding: utf-8 -*-
"""S132: bounded official alternative-representation probe for the four encrypted HWPX exceptions.

For exactly four pstSn values left technical-unknown by S131, fetch only the official detail page and
attachment metadata endpoint. Inventory any PDF/HTML/plain-text or additional official attachment
representation that could avoid HWPX decryption. Do not download encrypted HWPX, guess passwords,
OCR, infer legal absence, or promote SITE/runtime state.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
S131 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_terminal_reconciliation.json'
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_encrypted_hwpx_alternative_representation_probe.json'

EXPECTED = {'363790', '370638', '372500', '374744'}
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
            if not chunk: continue
            if len(buf) + len(chunk) > limit:
                overflow = True; break
            buf.extend(chunk)
    finally:
        r.close()
    return r.status_code, str(r.url), bytes(buf), overflow, r.headers.get('Content-Type', '')


def flatten_items(obj):
    found=[]
    def walk(x):
        if isinstance(x, dict):
            keys={str(k).lower() for k in x}
            if any(k in keys for k in ['fileno','file_no','orginlfilenm','orignlfilenm','strefilenm']): found.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(obj); return found


def field(d, *names):
    low={str(k).lower(): v for k,v in d.items()}
    for name in names:
        if name.lower() in low: return low[name.lower()]
    return None


def extension(name):
    s=norm(name).lower()
    return s.rsplit('.',1)[-1] if '.' in s else ''


def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE ENCRYPTED HWPX ALTERNATIVE REPRESENTATION PROBE - S132')
    print('='*60)
    print('Encrypted HWPX download: DISABLED')
    print('Decryption/password guessing: DISABLED')
    print('OCR: DISABLED')
    print('Negative evidence: DISABLED')

    s131=json.loads(S131.read_text(encoding='utf-8'))
    psts=set(map(str,s131.get('technical_unknown_pstSn') or []))
    if psts != EXPECTED: raise AssertionError(f'S131 unresolved identity mismatch: {psts}')

    session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]; requests_count=0
    for pst in sorted(psts):
        detail_url=urljoin(DETAIL_BASE,pst)
        hs,hu,hraw,hov,hct=bounded_get(session,detail_url,MAX_HTML_BYTES); requests_count+=1
        html=hraw.decode('utf-8',errors='replace') if hs==200 and not hov else ''
        text=re.sub(r'<[^>]+>',' ',html)
        text=norm(text)
        html_target_terms={t:text.count(t) for t in ['개발밀도관리구역','개발밀도 관리구역','UQQ700','개발밀도']}

        ms,mu,mraw,mov,mct=bounded_get(session,META,MAX_META_BYTES,params={'pstSn':pst}); requests_count+=1
        items=[]; meta_error=''
        if ms==200 and not mov:
            try:
                obj=json.loads(mraw.decode('utf-8',errors='strict'))
                for item in flatten_items(obj):
                    fn=norm(field(item,'orginlFileNm','orignlFileNm','streFileNm','fileNm'))
                    no=norm(field(item,'fileNo','file_no','atchFileNo'))
                    items.append({'fileNo':no,'filename':fn,'extension':extension(fn)})
            except Exception as exc:
                meta_error=repr(exc)

        alternatives=[x for x in items if x['extension'] in {'pdf','htm','html','txt'}]
        additional_non_hwpx=[x for x in items if x['extension'] and x['extension']!='hwpx']
        if alternatives:
            state='OFFICIAL_ALTERNATIVE_REPRESENTATION_FOUND'
        elif any(html_target_terms.values()):
            state='DETAIL_HTML_TARGET_TERM_CANDIDATE'
        elif additional_non_hwpx:
            state='OFFICIAL_NON_HWPX_REPRESENTATION_REVIEW_REQUIRED'
        elif hs==200 and ms==200 and not hov and not mov and not meta_error:
            state='NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE'
        else:
            state='TECHNICAL_PROBE_UNKNOWN'

        rec={'pstSn':pst,'detail_http':hs,'detail_url':hu,'detail_official_host':host(hu)==HOST,'detail_overflow':hov,'detail_content_type':hct,'detail_text_length':len(text),'detail_target_term_counts':html_target_terms,'metadata_http':ms,'metadata_url':mu,'metadata_official_host':host(mu)==HOST,'metadata_overflow':mov,'metadata_content_type':mct,'metadata_error':meta_error,'attachments':items,'alternative_representations':alternatives,'additional_non_hwpx_representations':additional_non_hwpx,'state':state}
        results.append(rec)
        print('PST:',pst,'| STATE:',state,'| DETAIL_HTTP:',hs,'| META_HTTP:',ms)
        print(' ATTACHMENTS:',[(x['fileNo'],x['filename'],x['extension']) for x in items])
        print(' HTML_TARGET_TERMS:',html_target_terms)

    states={}
    for r in results: states[r['state']]=states.get(r['state'],0)+1
    out={'step':'STEP 17-21-C-16-8-T-35-S132','target_name':'개발밀도관리구역','standard_code':'UQQ700','summary':{'input_technical_unknown_count':len(results),'request_count':requests_count,'state_counts':states,'alternative_representation_found_count':states.get('OFFICIAL_ALTERNATIVE_REPRESENTATION_FOUND',0),'detail_html_target_candidate_count':states.get('DETAIL_HTML_TARGET_TERM_CANDIDATE',0),'no_alternative_current_surface_count':states.get('NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE',0),'technical_probe_unknown_count':states.get('TECHNICAL_PROBE_UNKNOWN',0),'semantic_state':'POST_HWP5_ENCRYPTED_HWPX_ALTERNATIVE_REPRESENTATION_PROBED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'results':results,'encrypted_hwpx_download_executed':False,'decryption_or_password_guessing_executed':False,'ocr_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'input identities exact':{r['pstSn'] for r in results}==EXPECTED,'request budget exact':requests_count==8,'official hosts only':all(r['detail_official_host'] and r['metadata_official_host'] for r in results),'encrypted HWPX download disabled':not out['encrypted_hwpx_download_executed'],'decryption/password guessing disabled':not out['decryption_or_password_guessing_executed'],'ocr disabled':not out['ocr_executed'],'candidate promotion disabled':not out['candidate_promotion_allowed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S132 alternative representation probe failed')

if __name__=='__main__': main()
