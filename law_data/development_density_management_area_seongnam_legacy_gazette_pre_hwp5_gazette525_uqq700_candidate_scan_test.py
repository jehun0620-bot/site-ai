# -*- coding: utf-8 -*-
"""S139: single-row UQQ700 candidate scan for PRE-HWP5 Gazette 525.

S135 qualified Gazette 525 (pstSn 28674) as ordinary HWP5 with extractable text. This stage re-downloads
that exact official attachment once, extracts text with the already-qualified S135 HWP5 parser, and
scans only for UQQ700 direct/related lexical candidates. Search hits are candidates only, never legal
facts. No OCR, no negative evidence, no SITE/runtime promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from law_data.development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification_test import (
    BBS_CRT_SN,
    HOST,
    MAX_BYTES,
    UA,
    bounded_download,
    classify_signature,
    extract_hwp5,
    host,
    norm,
)

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
S135 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification.json'
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_gazette525_uqq700_candidate_scan.json'

TARGET_PST = '28674'
TARGET_GAZETTE = 525
DIRECT_TERMS = ['개발밀도관리구역', '개발밀도 관리구역', 'UQQ700']
RELATED_TERMS = ['개발밀도']
CONTEXT_RADIUS = 220


def contexts(text, term):
    out=[]
    for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
        a=max(0,m.start()-CONTEXT_RADIUS); b=min(len(text),m.end()+CONTEXT_RADIUS)
        out.append({'term':term,'start':m.start(),'end':m.end(),'context':re.sub(r'\s+',' ',text[a:b]).strip()})
    return out


def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 GAZETTE 525 UQQ700 CANDIDATE SCAN - S139')
    print('='*60)
    print('Scope: Gazette 525 / pstSn 28674 only')
    print('OCR: DISABLED')
    print('Negative evidence: DISABLED')
    print('Legal absence inference: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    src=json.loads(S135.read_text(encoding='utf-8'))
    matches=[r for r in (src.get('results') or []) if norm(r.get('pstSn'))==TARGET_PST]
    if len(matches)!=1: raise AssertionError(f'expected exactly one S135 row for pstSn {TARGET_PST}, got {len(matches)}')
    row=matches[0]
    if row.get('gazette_number')!=TARGET_GAZETTE or row.get('signature')!='HWP5' or row.get('state')!='HWP_TEXT_EXTRACTION_QUALIFIED':
        raise AssertionError('S135 Gazette 525 qualification mismatch')

    session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    hs,hu,data,overflow,ct=bounded_download(session,{'bbsCrtSn':BBS_CRT_SN,'pstSn':TARGET_PST,'fileNo':norm(row.get('fileNo'))})
    if hs!=200 or overflow or host(hu)!=HOST: raise AssertionError(f'official bounded download failed: HTTP={hs} overflow={overflow} host={host(hu)}')
    sig=classify_signature(data)
    if sig!='HWP5': raise AssertionError(f'expected HWP5 signature, got {sig}')
    ok,text,sections,records,flags,error=extract_hwp5(data)
    if not ok or not text: raise AssertionError(f'HWP5 extraction failed: {error}')

    direct=[]; related=[]
    direct_counts={}
    related_counts={}
    for term in DIRECT_TERMS:
        c=contexts(text,term); direct_counts[term]=len(c); direct.extend(c)
    for term in RELATED_TERMS:
        c=contexts(text,term); related_counts[term]=len(c); related.extend(c)

    # Avoid double-classifying generic related hits that occur inside a direct phrase.
    direct_spans=[(x['start'],x['end']) for x in direct]
    related_only=[]
    for x in related:
        if any(x['start']>=a and x['end']<=b for a,b in direct_spans): continue
        related_only.append(x)

    if direct:
        status='DIRECT_CANDIDATE'
    elif related_only:
        status='RELATED_CANDIDATE'
    else:
        status='NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT'

    out={
        'step':'STEP 17-21-C-16-8-T-36-S139',
        'target_name':'개발밀도관리구역','standard_code':'UQQ700',
        'row':{'pstSn':TARGET_PST,'gazette_number':TARGET_GAZETTE,'date':row.get('date'),'filename':row.get('filename'),'fileNo':row.get('fileNo')},
        'download':{'http':hs,'official_host':host(hu)==HOST,'bytes':len(data),'overflow':overflow,'content_type':ct,'signature':sig},
        'extraction':{'parser':'HWP5_ORDINARY_INTERNAL_NO_CRYPTO_HIGH_LIMIT_2000000','section_count':sections,'record_count':records,'flags':flags,'text_length':len(text),'extract_ok':ok},
        'scan':{'direct_terms':DIRECT_TERMS,'related_terms':RELATED_TERMS,'direct_counts':direct_counts,'related_counts':related_counts,'direct_occurrence_count':len(direct),'related_only_occurrence_count':len(related_only),'status':status,'direct_contexts':direct,'related_contexts':related_only},
        'summary':{'input_row_count':1,'request_count':1,'direct_candidate_count':1 if status=='DIRECT_CANDIDATE' else 0,'related_candidate_count':1 if status=='RELATED_CANDIDATE' else 0,'no_candidate_term_count':1 if status=='NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT' else 0,'semantic_state':'PRE_HWP5_GAZETTE525_UQQ700_CANDIDATE_SCAN_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},
        'ocr_executed':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')

    print('GAZETTE:',TARGET_GAZETTE,'| pstSn:',TARGET_PST,'| TEXT_LEN:',len(text),'| STATUS:',status)
    print('DIRECT_COUNTS:',direct_counts)
    print('RELATED_COUNTS:',related_counts)
    for x in direct: print('DIRECT_CONTEXT:',x['context'])
    for x in related_only: print('RELATED_CONTEXT:',x['context'])
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)

    vals={
        'single exact input row':out['summary']['input_row_count']==1,
        'single exact request':out['summary']['request_count']==1,
        'official host only':out['download']['official_host'],
        'download ceiling respected':not out['download']['overflow'] and out['download']['bytes']<=MAX_BYTES,
        'HWP5 extraction qualified':out['extraction']['extract_ok'] and out['extraction']['text_length']>0,
        'OCR disabled':not out['ocr_executed'],
        'negative evidence disabled':not out['negative_evidence_allowed'],
        'legal absence inference disabled':not out['legal_absence_inference_allowed'],
        'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),
        'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN',
        'output written':OUT.exists() and OUT.stat().st_size>0,
    }
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S139 Gazette 525 UQQ700 candidate scan failed')

if __name__=='__main__': main()
