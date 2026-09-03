# -*- coding: utf-8 -*-
"""S130: recover the sole no-PDF HWP exception (pstSn 29286) without Crypto dependency.

The locked current manifest partitions this row as Gazette 11132, while its attachment filename says
'제1113호발행분07.02(월)발행분.hwp'. This stage treats that as a metadata/parser anomaly candidate,
downloads only this HWP, and directly parses ordinary OLE HWP5 BodyText. Distribution HWP5 is left
technical-unknown because decrypting ViewText requires the optional Crypto dependency. No OCR,
negative evidence, manifest rewrite, historical-era reconstruction, or SITE/runtime promotion.
"""
from __future__ import annotations

import io
import json
import re
import struct
import zlib
from pathlib import Path

import olefile
import requests

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
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
OLE_SIG = bytes.fromhex('D0CF11E0A1B11AE1')
PARA_TEXT_TAG = 67
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


def parse_record_header(data, offset):
    if offset + 4 > len(data):
        raise ValueError('truncated record header')
    value = struct.unpack_from('<I', data, offset)[0]
    tag_id = value & 0x3FF
    size = (value >> 20) & 0xFFF
    header_bytes = 4
    if size == 0xFFF:
        if offset + 8 > len(data):
            raise ValueError('truncated extended record header')
        size = struct.unpack_from('<I', data, offset + 4)[0]
        header_bytes = 8
    payload_offset = offset + header_bytes
    end = payload_offset + size
    if end > len(data):
        raise ValueError('record payload exceeds stream')
    return {'tag_id': tag_id, 'payload_offset': payload_offset, 'end': end}, end


def sanitize_para_text(payload):
    if len(payload) % 2:
        payload = payload[:-1]
    text = payload.decode('utf-16le', errors='ignore')
    chars = []
    for ch in text:
        code = ord(ch)
        if ch in '\r\n\t':
            chars.append(' ')
        elif code >= 0x20 and code not in range(0x7F, 0xA0):
            chars.append(ch)
        else:
            chars.append(' ')
    return re.sub(r'\s+', ' ', ''.join(chars)).strip()


def parse_records_text(data):
    offset = records = para_count = 0
    paragraphs = []
    error = ''
    while offset < len(data):
        try:
            rec, nxt = parse_record_header(data, offset)
        except Exception as exc:
            error = repr(exc)
            break
        if rec['tag_id'] == PARA_TEXT_TAG:
            para_count += 1
            t = sanitize_para_text(data[rec['payload_offset']:rec['end']])
            if t:
                paragraphs.append(t)
        records += 1
        offset = nxt
        if records > 2_000_000:
            error = 'record safety limit exceeded (2000000)'
            break
    return {'record_count': records, 'para_text_record_count': para_count, 'fully_consumed': offset == len(data), 'parse_error': error, 'text': '\n'.join(paragraphs)}


def file_header_flags(ole):
    raw = ole.openstream('FileHeader').read()
    if len(raw) < 40 or not raw.startswith(b'HWP Document File'):
        raise ValueError('invalid HWP5 FileHeader')
    flags = struct.unpack_from('<I', raw, 36)[0]
    return {'compressed': bool(flags & 0x1), 'password': bool(flags & 0x2), 'distribution': bool(flags & 0x4), 'flags': flags}


def bodytext_names(ole):
    names = []
    for parts in ole.listdir(streams=True, storages=False):
        name = '/'.join(parts)
        if name.startswith('BodyText/Section'):
            names.append(name)
    def key(name):
        m = re.search(r'Section(\d+)$', name)
        return int(m.group(1)) if m else 10**9
    return sorted(names, key=key)


def extract_ordinary_hwp5(raw):
    if not raw.startswith(OLE_SIG):
        return {'ok': False, 'error': 'not OLE HWP5', 'text': '', 'flags': {}, 'sections': []}
    try:
        ole = olefile.OleFileIO(io.BytesIO(raw))
        try:
            flags = file_header_flags(ole)
            if flags['password']:
                return {'ok': False, 'error': 'password-protected HWP5 unsupported', 'text': '', 'flags': flags, 'sections': []}
            if flags['distribution']:
                return {'ok': False, 'error': 'distribution HWP5 requires optional Crypto dependency', 'text': '', 'flags': flags, 'sections': []}
            names = bodytext_names(ole)
            if not names:
                return {'ok': False, 'error': 'ordinary HWP5 has no BodyText sections', 'text': '', 'flags': flags, 'sections': []}
            all_text, sections = [], []
            for name in names:
                stored = ole.openstream(name).read()
                plain = zlib.decompress(stored, -zlib.MAX_WBITS) if flags['compressed'] else stored
                parsed = parse_records_text(plain)
                sections.append({'stream': name, 'stored_bytes': len(stored), 'plain_bytes': len(plain), 'records': parsed['record_count'], 'para_text_records': parsed['para_text_record_count'], 'fully_consumed': parsed['fully_consumed'], 'parse_error': parsed['parse_error'], 'text_chars': len(parsed['text'])})
                if parsed['text']:
                    all_text.append(parsed['text'])
            merged = '\n'.join(all_text)
            ok = bool(merged) and all(not s['parse_error'] for s in sections)
            return {'ok': ok, 'error': '' if ok else 'HWP5 section parse incomplete', 'text': merged, 'flags': flags, 'sections': sections}
        finally:
            ole.close()
    except Exception as exc:
        return {'ok': False, 'error': repr(exc), 'text': '', 'flags': {}, 'sections': []}


def classify_signature(raw):
    if raw.startswith(OLE_SIG):
        return 'HWP5'
    if raw[:16].startswith(b'HWP Document File'):
        return 'HWP3'
    return 'UNKNOWN'


def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWP EXCEPTION RECOVERY - S130-R1')
    print('='*60)
    print('Crypto dependency: NOT REQUIRED FOR ORDINARY HWP5')
    print('Distribution HWP5 decryption: DISABLED')
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
    session.headers.update({'User-Agent': USER_AGENT, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    resp = session.get(DOWNLOAD, params={'bbsCrtSn': BBS_CRT_SN, 'pstSn': PST, 'fileNo': str(att.get('fileNo'))}, timeout=TIMEOUT, stream=True)
    data = bytearray(); overflow = False
    try:
        for chunk in resp.iter_content(65536):
            if not chunk: continue
            if len(data)+len(chunk) > MAX_FILE_BYTES:
                overflow = True; break
            data.extend(chunk)
    finally:
        resp.close()
    raw = bytes(data)
    signature = classify_signature(raw) if resp.status_code == 200 and not overflow else 'UNKNOWN'

    if signature == 'HWP5':
        ext = extract_ordinary_hwp5(raw); parser_used = 'HWP5_ORDINARY_INTERNAL_NO_CRYPTO_HIGH_LIMIT_2000000'
    elif signature == 'HWP3':
        ext = {'ok': False, 'error': 'HWP3 fallback not enabled in S130-R1', 'text': '', 'flags': {}, 'sections': []}; parser_used = ''
    else:
        ext = {'ok': False, 'error': 'unsupported or failed HWP signature', 'text': '', 'flags': {}, 'sections': []}; parser_used = ''

    text = str(ext.get('text') or '')
    direct = collect(text, DIRECT) if ext.get('ok') else []
    related = collect(text, RELATED) if ext.get('ok') else []
    if not ext.get('ok'):
        status = 'EXTRACTION_OR_REQUEST_UNKNOWN'
    elif direct:
        status = 'DIRECT_CANDIDATE'
    elif related:
        status = 'RELATED_CANDIDATE'
    else:
        status = 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT'

    print('PST:', PST, '| PARSED_GAZETTE:', row.get('gazette_number'), '| FILENAME:', filename, '| FILENAME_GAZETTE:', filename_gazette)
    print('PARSER_ANOMALY_CONFIRMED:', parser_anomaly_confirmed)
    print('HTTP:', resp.status_code, '| BYTES:', len(raw), '| SIGNATURE:', signature, '| PARSER:', parser_used)
    print('FLAGS:', ext.get('flags'))
    print('SECTION_COUNT:', len(ext.get('sections') or []))
    print('EXTRACT_OK:', bool(ext.get('ok')), '| TEXT_LEN:', len(text), '| ERROR:', ext.get('error'))
    print('STATUS:', status)
    for hit in direct + related:
        print('TERM:', hit['term'], '| COUNT:', hit['occurrence_count'])
        for ctx in hit['contexts'][:4]: print(' CONTEXT:', ctx)

    out = {
        'step':'STEP 17-21-C-16-8-T-35-S130-R1','target_name':'개발밀도관리구역','standard_code':'UQQ700',
        'record':{'pstSn':PST,'manifest_parsed_gazette_number':row.get('gazette_number'),'attachment_filename':filename,'attachment_filename_gazette_number':filename_gazette,'parser_anomaly_confirmed':parser_anomaly_confirmed,'http_status':resp.status_code,'downloaded_bytes':len(raw),'signature_class':signature,'parser_used':parser_used,'hwp_flags':ext.get('flags') or {},'section_count':len(ext.get('sections') or []),'extract_ok':bool(ext.get('ok')),'extract_error':ext.get('error'),'text_length':len(text),'status':status,'direct_hits':direct,'related_hits':related},
        'summary':{'recovered_row_count':1 if ext.get('ok') else 0,'technical_unknown_count':0 if ext.get('ok') else 1,'direct_candidate_row_count':1 if status=='DIRECT_CANDIDATE' else 0,'related_candidate_row_count':1 if status=='RELATED_CANDIDATE' else 0,'no_candidate_term_row_count':1 if status=='NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT' else 0,'metadata_parser_anomaly_count':1 if parser_anomaly_confirmed else 0,'semantic_state':'POST_HWP5_HWP_EXCEPTION_RECOVERY_CAPTURED','negative_evidence_allowed':False,'uqq700_final_resolution':'UNKNOWN'},
        'crypto_dependency_required':False,'distribution_hwp5_decryption_executed':False,'immutable_manifest_rewrite_allowed':False,'historical_era_reconstruction_allowed':False,'ocr_executed':False,'candidate_promotion_allowed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'S128 HWP identity exact':str(row.get('pstSn'))==PST,'single HWP attachment':len(hwp_atts)==1,'download bounded':len(raw)<=MAX_FILE_BYTES,'Crypto dependency not required':not out['crypto_dependency_required'],'distribution decryption disabled':not out['distribution_hwp5_decryption_executed'],'immutable manifest rewrite disabled':not out['immutable_manifest_rewrite_allowed'],'historical reconstruction disabled':not out['historical_era_reconstruction_allowed'],'ocr disabled':not out['ocr_executed'],'candidate promotion disabled':not out['candidate_promotion_allowed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S130-R1 HWP exception recovery failed')

if __name__=='__main__': main()
