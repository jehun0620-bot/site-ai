# -*- coding: utf-8 -*-
"""S136: bounded forensic probe for the 47 HWP3 PRE-HWP5 attachments.

Purpose: determine whether HWP3 body text is recoverable through a conservative local byte-structure
inspection before implementing a full parser. This stage samples exactly three HWP3 rows (first,
median, last among S135 HWP3 rows), downloads one attachment each, and inventories signatures,
header strings, Hangul-like decoded runs, and candidate plain-text encodings. No target-term scan,
OCR, decryption, negative evidence, or SITE/runtime promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
S135 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification.json'
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp3_parser_forensic.json'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
HOST = 'www.seongnam.go.kr'
BBS_CRT_SN = '16002'
TIMEOUT = 45
MAX_BYTES = 64 * 1024 * 1024
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v): return re.sub(r'\s+', ' ', str(v or '')).strip()

def host(url):
    try: return (urlparse(url).hostname or '').lower()
    except Exception: return ''

def download(session, pst, file_no):
    r=session.get(DOWNLOAD,params={'bbsCrtSn':BBS_CRT_SN,'pstSn':pst,'fileNo':file_no},timeout=TIMEOUT,stream=True,allow_redirects=True)
    buf=bytearray(); overflow=False
    try:
        for chunk in r.iter_content(65536):
            if not chunk: continue
            if len(buf)+len(chunk)>MAX_BYTES: overflow=True; break
            buf.extend(chunk)
    finally: r.close()
    return r.status_code,str(r.url),bytes(buf),overflow,r.headers.get('Content-Type','')

def hangul_count(s): return sum(1 for ch in s if '\uac00' <= ch <= '\ud7a3')

def printable_ratio(s):
    if not s: return 0.0
    ok=sum(1 for ch in s if ch.isprintable() or ch in '\r\n\t')
    return ok/len(s)

def decode_probe(data, enc):
    try: s=data.decode(enc,errors='ignore')
    except Exception: return {'encoding':enc,'length':0,'hangul_count':0,'printable_ratio':0.0,'sample':''}
    # retain only human-readable runs for forensic summary
    runs=re.findall(r'[가-힣A-Za-z0-9\s.,:;()\[\]{}<>/%+-]{12,}',s)
    runs=sorted(runs,key=lambda x:(hangul_count(x),len(x)),reverse=True)
    sample=norm(runs[0])[:300] if runs else ''
    return {'encoding':enc,'length':len(s),'hangul_count':hangul_count(s),'printable_ratio':round(printable_ratio(s),4),'sample':sample}

def ascii_runs(data):
    vals=[]
    for m in re.finditer(rb'[\x20-\x7e]{8,}',data):
        try: vals.append(m.group().decode('ascii'))
        except Exception: pass
    return vals[:40]

def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 HWP3 PARSER FORENSIC - S136')
    print('='*60)
    print('Scope: 3 bounded HWP3 samples')
    print('Target-term scan: DISABLED')
    print('OCR: DISABLED')
    print('Decryption: DISABLED')
    print('Negative evidence: DISABLED')

    src=json.loads(S135.read_text(encoding='utf-8'))
    rows=[r for r in (src.get('results') or []) if r.get('signature')=='HWP3']
    if len(rows)!=47: raise AssertionError(f'expected 47 HWP3 rows, got {len(rows)}')
    picks=[rows[0],rows[len(rows)//2],rows[-1]]
    session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    results=[]
    for r in picks:
        pst=norm(r.get('pstSn')); no=norm(r.get('fileNo'))
        hs,hu,data,overflow,ct=download(session,pst,no)
        probes=[decode_probe(data,e) for e in ['utf-16le','euc-kr','cp949','utf-8']]
        rec={'pstSn':pst,'gazette_number':r.get('gazette_number'),'filename':r.get('filename'),'http':hs,'official_host':host(hu)==HOST,'bytes':len(data),'overflow':overflow,'content_type':ct,'signature_prefix_hex':data[:32].hex(),'signature_prefix_ascii':data[:64].decode('latin1',errors='replace'),'ascii_runs':ascii_runs(data),'decode_probes':probes,'state':'HWP3_FORENSIC_CAPTURED' if hs==200 and not overflow else 'TECHNICAL_FORENSIC_UNKNOWN'}
        results.append(rec)
        print('GAZETTE:',rec['gazette_number'],'| pstSn:',pst,'| HTTP:',hs,'| BYTES:',len(data),'| STATE:',rec['state'])
        for p in probes: print(' ',p['encoding'],'HANGUL:',p['hangul_count'],'PRINTABLE:',p['printable_ratio'],'SAMPLE:',p['sample'][:120])

    out={'step':'STEP 17-21-C-16-8-T-36-S136','target_name':'개발밀도관리구역','standard_code':'UQQ700','summary':{'hwp3_input_count':47,'sample_count':len(results),'forensic_success_count':sum(r['state']=='HWP3_FORENSIC_CAPTURED' for r in results),'technical_unknown_count':sum(r['state']!='HWP3_FORENSIC_CAPTURED' for r in results),'semantic_state':'PRE_HWP5_HWP3_PARSER_FORENSIC_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'results':results,'target_term_scan_executed':False,'ocr_executed':False,'decryption_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'47 HWP3 source rows':len(rows)==47,'sample count exact':len(results)==3,'official hosts only':all(r['official_host'] for r in results),'download ceilings respected':all(not r['overflow'] for r in results),'target-term scan disabled':not out['target_term_scan_executed'],'OCR disabled':not out['ocr_executed'],'decryption disabled':not out['decryption_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S136 HWP3 parser forensic failed')

if __name__=='__main__': main()
