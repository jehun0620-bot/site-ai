# -*- coding: utf-8 -*-
"""S118: forensic parse errors in HWPX/HWTX XML-like ZIP members.

S117 established that the ZIP containers are valid, but strict ElementTree parsing fails for most
XML-like members. This stage downloads the same deterministic HWPX/HWTX samples and records,
for each XML-like member, its name, BOM/encoding declaration, safe textual prefix, parse error,
and lightweight text-token diagnostics using tolerant byte decoding only.

No target-term search, OCR, legal inference, or binary retention.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwpx_hwtx_xml_parse_error_forensic.json'

HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
FORMATS = ['hwpx', 'hwtx']
MAX_REQUESTS = 2
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 40 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
XML_DECL_RE = re.compile(br'<\?xml\s+[^>]*encoding=["\']([^"\']+)["\']', re.I)
TAG_TEXT_RE = re.compile(r'>([^<>]{2,})<', re.S)


def norm(v):
    return str(v or '').strip()


def select_samples(attachments):
    out = []
    for ext in FORMATS:
        xs = [a for a in attachments if norm(a.get('extension')).lower() == ext]
        xs.sort(key=lambda a: (str(a.get('date') or ''), int(a.get('gazette_number') or 0), int(a.get('pstSn') or 0), int(a.get('position') or 0)))
        if not xs:
            raise AssertionError(f'no {ext} attachment')
        out.append(xs[0])
    return out


def decode_raw(raw):
    bom = 'NONE'
    if raw.startswith(b'\xef\xbb\xbf'):
        bom = 'UTF8_BOM'
    elif raw.startswith(b'\xff\xfe'):
        bom = 'UTF16_LE_BOM'
    elif raw.startswith(b'\xfe\xff'):
        bom = 'UTF16_BE_BOM'
    decl = ''
    m = XML_DECL_RE.search(raw[:500])
    if m:
        decl = m.group(1).decode('ascii', errors='replace')
    candidates = []
    if decl:
        candidates.append(decl)
    candidates.extend(['utf-8-sig', 'utf-16', 'cp949', 'euc-kr'])
    seen = set()
    for enc in candidates:
        key = enc.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return raw.decode(enc), enc, bom, decl
        except Exception:
            continue
    return raw.decode('utf-8', errors='replace'), 'utf-8-replace', bom, decl


def safe_tokens(text):
    vals = []
    for m in TAG_TEXT_RE.finditer(text or ''):
        v = re.sub(r'\s+', ' ', m.group(1)).strip()
        if v and not v.startswith('&'):
            vals.append(v[:250])
        if len(vals) >= 30:
            break
    return vals


def analyze(data):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        recs = []
        for name in zf.namelist():
            if not name.lower().endswith(('.xml', '.xhtml', '.html')):
                continue
            raw = zf.read(name)
            text, encoding_used, bom, decl = decode_raw(raw)
            parse_ok = True
            parse_error = ''
            try:
                ET.fromstring(raw)
            except Exception as exc:
                parse_ok = False
                parse_error = repr(exc)[:500]
            recs.append({
                'name': name,
                'byte_size': len(raw),
                'parse_ok': parse_ok,
                'parse_error': parse_error,
                'bom': bom,
                'xml_declared_encoding': decl,
                'decoded_with': encoding_used,
                'decoded_prefix': re.sub(r'\s+', ' ', text[:1500]).strip(),
                'tolerant_text_tokens': safe_tokens(text),
            })
        return recs


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWPX/HWTX XML PARSE ERROR FORENSIC - S118')
    print('=' * 60)
    print('OCR: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    summary = reg.get('summary') or {}
    if summary.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('registry identity mismatch')
    samples = select_samples(reg.get('attachments') or [])

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    records = []
    request_count = 0
    total_bytes = 0
    technical_unknown = 0

    for idx, a in enumerate(samples, 1):
        params = {'bbsCrtSn': BBS_CRT_SN, 'pstSn': str(a.get('pstSn')), 'fileNo': str(a.get('fileNo'))}
        request_count += 1
        try:
            resp = session.get(DOWNLOAD, params=params, timeout=TIMEOUT, allow_redirects=True, stream=True)
        except Exception as exc:
            technical_unknown += 1
            records.append({**a, 'technical_state': 'TRANSPORT_ERROR', 'error': repr(exc)[:500]})
            continue
        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        buf = bytearray()
        overflow = False
        try:
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > PER_FILE_BYTE_LIMIT or total_bytes + len(chunk) > TOTAL_BYTE_LIMIT:
                    overflow = True
                    break
                buf.extend(chunk)
                total_bytes += len(chunk)
        finally:
            resp.close()
        if resp.status_code != 200 or not official or overflow:
            technical_unknown += 1
            records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'byte_limit_overflow': overflow, 'technical_state': 'DOWNLOAD_UNKNOWN'})
            continue
        try:
            members = analyze(bytes(buf))
            state = 'XML_PARSE_ERROR_FORENSIC_CAPTURED'
        except Exception as exc:
            technical_unknown += 1
            members = []
            state = 'ZIP_ANALYSIS_UNKNOWN'
            err = repr(exc)[:500]
        else:
            err = ''
        parse_fail = [m for m in members if not m['parse_ok']]
        parse_ok = [m for m in members if m['parse_ok']]
        records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'downloaded_byte_count': len(buf), 'xmlish_member_count': len(members), 'parse_ok_count': len(parse_ok), 'parse_fail_count': len(parse_fail), 'members': members, 'technical_state': state, 'error': err})
        print('SAMPLE:', idx, '/', len(samples), 'EXT:', a.get('extension'), 'XMLISH:', len(members), 'PARSE_OK:', len(parse_ok), 'PARSE_FAIL:', len(parse_fail))
        for m in parse_fail[:12]:
            print('FAIL_MEMBER:', m['name'], '|', m['parse_error'], '| ENC:', m['xml_declared_encoding'] or m['decoded_with'], '| TOKENS:', m['tolerant_text_tokens'][:3])

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S118',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'summary': {
            'sample_format_count': len(samples),
            'request_count': request_count,
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'semantic_state': 'POST_HWP5_HWPX_HWTX_XML_PARSE_ERROR_FORENSIC_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'downloaded_binary_retained': False,
        'ocr_executed': False,
        'target_term_search_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'registry identity exact': summary.get('registry_identity_sha256') == EXPECTED_REGISTRY_SHA,
        'sample count exact': len(samples) == MAX_REQUESTS,
        'request budget exact': request_count == MAX_REQUESTS,
        'all samples accounted': len(records) == MAX_REQUESTS,
        'total byte budget respected': total_bytes <= TOTAL_BYTE_LIMIT,
        'downloaded binary not retained': not out['downloaded_binary_retained'],
        'ocr disabled': not out['ocr_executed'],
        'target-term search disabled': not out['target_term_search_executed'],
        'candidate promotion disabled': not out['candidate_promotion_allowed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('\nSUMMARY')
    for k, v in out['summary'].items():
        print(f'{k}: {v}')
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S118 XML parse error forensic failed')


if __name__ == '__main__':
    main()
