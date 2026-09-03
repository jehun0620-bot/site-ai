# -*- coding: utf-8 -*-
"""S130: recover the sole no-PDF HWP exception (pstSn 29286) with the existing HWP5 parser.

The locked current manifest partitions this row as Gazette 11132, but the attachment filename says
'제1113호발행분07.02(월)발행분.hwp'. This stage therefore treats the gazette-number mismatch as a
metadata/parser anomaly, downloads only this HWP, extracts text with the already validated internal
HWP5/HWP3 routing, and scans candidate terms. It does not rewrite the immutable manifest, infer the
historical 1338-row corpus, authorize negative evidence, or promote legal/SITE state.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from law_data import development_density_management_area_municipal_gazette_hwp3_uqq700_bounded_batch_search_test as hwp3
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as sigbase

BASE = Path(__file__).resolve().parent.parent
S128 = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_exception_coverage_forensic.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwp_exception_recovery.json'

PST = '29286'
PARSED_GAZETTE = '11132'
FILENAME_GAZETTE = '1113'
BBS_CRT_SN = '16002'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
MAX_FILE_BYTES = 64 * 1024 * 1024
TIMEOUT = 45
CONTEXT_RADIUS = 260
DIRECT = [('TARGET_NAME', re.compile(r'개발\s*밀도\s*관리\s*구역')), ('STANDARD_CODE', re.compile(r'UQQ\s*700', re.I))]
RELATED = [('DEVELOPMENT_DENSITY_MANAGEMENT', re.compile(r'개발\s*밀도\s*관리')), ('DEVELOPMENT_DENSITY', re.compile(r'개발\s*밀도'))]


def compact_context(text, start, end):
    lo, hi = max(0, start-CONTEXT_RADIUS), min(len(text), end+CONTEXT_RADIUS)
    return re.sub(r'\s+', ' ', text[lo:hi]).strip()


def collect(text, patterns):
    out = []
    for label, pat in patterns:
        ms = list(pat.finditer(text))
        if ms:
            out.append({'term': label, 'occurrence_count': len(ms), 'contexts': [compact_context(text, m.start(), m.end()) for m in ms[:8]]})
    return out


def parse_attachment_gazette(filename):
    m = re.search(r'제\s*(\d+)\s*호', str(filename or ''))
    return m.group(1) if m else ''


def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWP EXCEPTION RECOVERY - S130')
    print('='*60)
    print('OCR: DISABLED')
    print('Negative evidence: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    src = json.loads(S128.read_text(encoding='utf-8'))
    rows = [r for r in (src.get('no_pdf_exceptions') or []) if str(r.get('pstSn')) == PST]
    if len(rows) != 1:
        raise AssertionError('S128 HWP exception identity mismatch')
    row = rows[0]
    atts = row.get('attachments') or []
    hwp_atts = [a for a in atts if str(a.get('extension') or '').lower() == 'hwp']
    if len(hwp_atts) != 1:
        raise AssertionError('expected exactly one HWP attachment')
    att = hwp_atts[0]
    filename = str(att.get('filename') or '')
    filename_gazette = parse_attachment_gazette(filename)
    parser_anomaly_confirmed = str(row.get('gazette_number')) == PARSED_GAZETTE and filename_gazette == FILENAME_GAZETTE

    session = requests.Session()
    session.headers.update({'User-Agent': hwp5.USER_AGENT, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    resp = session.get(DOWNLOAD, params={'bbsCrtSn': BBS_CRT_SN, 'pstSn': PST, 'fileNo': str(att.get('fileNo'))}, timeout=TIMEOUT, stream=True)
    data = bytearray()
    overflow = False
    try:
        for chunk in resp.iter_content(65536):
            if not chunk:
                continue
            if len(data)+len(chunk) > MAX_FILE_BYTES:
                overflow = True
                break
            data.extend(chunk)
    finally:
        resp.close()
    raw = bytes(data)
    signature = sigbase.classify_signature(raw) if resp.status_code == 200 and not overflow else 'UNKNOWN'

    original_parser = hwp5.parse_records_text
    def high_limit(data_bytes):
        offset=records=para_count=0; paragraphs=[]; error=''
        while offset < len(data_bytes):
            try:
                rec, nxt = hwp5.parse_record_header(data_bytes, offset)
            except Exception as exc:
                error=repr(exc); break
            if rec['tag_id'] == hwp5.PARA_TEXT_TAG:
                para_count += 1
                t = hwp5.sanitize_para_text(data_bytes[rec['payload_offset']:rec['end']])
                if t: paragraphs.append(t)
            records += 1; offset = nxt
            if records > 2_000_000:
                error='record safety limit exceeded (2000000)'; break
        return {'record_count':records,'para_text_record_count':para_count,'fully_consumed':offset==len(data_bytes),'parse_error':error,'text':'\n'.join(paragraphs)}

    try:
        hwp5.parse_records_text = high_limit
        if signature == 'HWP5':
            ext = hwp5.extract_hwp5(raw); parser_used = 'HWP5_INTERNAL_HIGH_LIMIT_2000000'
        elif signature == 'HWP3':
            ext = hwp3.extract_hwp3(raw); parser_used = 'HWP3_INTERNAL'
        else:
            ext = {'ok':False,'error':'unsupported or failed HWP signature','text':''}; parser_used=''
    finally:
        hwp5.parse_records_text = original_parser

    text = str(ext.get('text') or '')
    direct = collect(text, DIRECT) if ext.get('ok') else []
    related = collect(text, RELATED) if ext.get('ok') else []
    if not ext.get('ok'):
        status='EXTRACTION_OR_REQUEST_UNKNOWN'
    elif direct:
        status='DIRECT_CANDIDATE'
    elif related:
        status='RELATED_CANDIDATE'
    else:
        status='NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT'

    print('PST:', PST, '| PARSED_GAZETTE:', row.get('gazette_number'), '| FILENAME:', filename, '| FILENAME_GAZETTE:', filename_gazette)
    print('PARSER_ANOMALY_CONFIRMED:', parser_anomaly_confirmed)
    print('HTTP:', resp.status_code, '| BYTES:', len(raw), '| SIGNATURE:', signature, '| PARSER:', parser_used)
    print('EXTRACT_OK:', bool(ext.get('ok')), '| TEXT_LEN:', len(text), '| ERROR:', ext.get('error'))
    print('STATUS:', status)
    for hit in direct + related:
        print('TERM:', hit['term'], '| COUNT:', hit['occurrence_count'])
        for ctx in hit['contexts'][:4]: print(' CONTEXT:', ctx)

    out = {
        'step':'STEP 17-21-C-16-8-T-35-S130','target_name':'개발밀도관리구역','standard_code':'UQQ700',
        'record':{'pstSn':PST,'manifest_parsed_gazette_number':row.get('gazette_number'),'attachment_filename':filename,'attachment_filename_gazette_number':filename_gazette,'parser_anomaly_confirmed':parser_anomaly_confirmed,'http_status':resp.status_code,'downloaded_bytes':len(raw),'signature_class':signature,'parser_used':parser_used,'extract_ok':bool(ext.get('ok')),'extract_error':ext.get('error'),'text_length':len(text),'status':status,'direct_hits':direct,'related_hits':related},
        'summary':{'recovered_row_count':1 if ext.get('ok') else 0,'technical_unknown_count':0 if ext.get('ok') else 1,'direct_candidate_row_count':1 if status=='DIRECT_CANDIDATE' else 0,'related_candidate_row_count':1 if status=='RELATED_CANDIDATE' else 0,'no_candidate_term_row_count':1 if status=='NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT' else 0,'metadata_parser_anomaly_count':1 if parser_anomaly_confirmed else 0,'semantic_state':'POST_HWP5_HWP_EXCEPTION_RECOVERY_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},
        'immutable_manifest_rewrite_allowed':False,'historical_era_reconstruction_allowed':False,'ocr_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'S128 HWP identity exact':str(row.get('pstSn'))==PST,'single HWP attachment':len(hwp_atts)==1,'download bounded':len(raw)<=MAX_FILE_BYTES,'internal parser restored':hwp5.parse_records_text is original_parser,'immutable manifest rewrite disabled':not out['immutable_manifest_rewrite_allowed'],'historical reconstruction disabled':not out['historical_era_reconstruction_allowed'],'ocr disabled':not out['ocr_executed'],'candidate promotion disabled':not out['candidate_promotion_allowed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S130 HWP exception recovery failed')

if __name__=='__main__': main()
