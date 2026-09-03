# -*- coding: utf-8 -*-
"""S117: forensic ZIP structure for HWPX/HWTX extraction recovery.

S116 showed both HWPX and HWTX download correctly but the generic XML itertext extractor
returned NO_XML_TEXT. This stage downloads one deterministic HWPX and one deterministic HWTX
sample from the validated S113 registry and inventories ZIP members, XML parseability,
namespace/tag frequencies, and text-bearing element diagnostics.

No target-term search. No legal inference. OCR disabled. Binary bytes are not retained.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwpx_hwtx_zip_structure_forensic.json'

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


def norm(v):
    return str(v or '').strip()


def select_samples(attachments):
    picked = []
    for ext in FORMATS:
        xs = [a for a in attachments if norm(a.get('extension')).lower() == ext]
        xs.sort(key=lambda a: (str(a.get('date') or ''), int(a.get('gazette_number') or 0), int(a.get('pstSn') or 0), int(a.get('position') or 0)))
        if not xs:
            raise AssertionError(f'no {ext} attachment in registry')
        picked.append(xs[0])
    return picked


def local_name(tag):
    s = str(tag or '')
    return s.split('}', 1)[-1] if '}' in s else s


def namespace_of(tag):
    s = str(tag or '')
    if s.startswith('{') and '}' in s:
        return s[1:].split('}', 1)[0]
    return ''


def clean(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def analyze_zip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        xmlish = [n for n in names if n.lower().endswith(('.xml', '.xhtml', '.html'))]
        member_records = []
        aggregate_tags = Counter()
        aggregate_namespaces = Counter()
        text_candidate_tags = Counter()
        parse_error_count = 0
        for name in xmlish:
            raw = zf.read(name)
            rec = {'name': name, 'byte_size': len(raw)}
            try:
                root = ET.fromstring(raw)
                tags = Counter()
                namespaces = Counter()
                text_tags = Counter()
                text_chars = 0
                text_samples = []
                for el in root.iter():
                    ln = local_name(el.tag)
                    ns = namespace_of(el.tag)
                    tags[ln] += 1
                    if ns:
                        namespaces[ns] += 1
                    txt = clean(el.text)
                    if txt:
                        text_chars += len(txt)
                        text_tags[ln] += 1
                        if len(text_samples) < 20:
                            text_samples.append({'tag': ln, 'text': txt[:300]})
                aggregate_tags.update(tags)
                aggregate_namespaces.update(namespaces)
                text_candidate_tags.update(text_tags)
                rec.update({
                    'parse_ok': True,
                    'root_tag': str(root.tag),
                    'element_count': sum(tags.values()),
                    'text_char_count_from_element_text': text_chars,
                    'top_tags': tags.most_common(30),
                    'text_bearing_tags': text_tags.most_common(30),
                    'text_samples': text_samples,
                })
            except Exception as exc:
                parse_error_count += 1
                rec.update({'parse_ok': False, 'error': repr(exc)[:500], 'raw_prefix': raw[:500].decode('utf-8', errors='replace')})
            member_records.append(rec)
        return {
            'zip_member_count': len(names),
            'zip_members': names,
            'xmlish_member_count': len(xmlish),
            'xmlish_members': member_records,
            'aggregate_top_tags': aggregate_tags.most_common(50),
            'aggregate_namespaces': aggregate_namespaces.most_common(30),
            'aggregate_text_bearing_tags': text_candidate_tags.most_common(50),
            'parse_error_count': parse_error_count,
        }


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWPX/HWTX ZIP STRUCTURE FORENSIC - S117')
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
    request_count = 0
    total_bytes = 0
    records = []
    technical_unknown = 0

    for idx, a in enumerate(samples, 1):
        ext = norm(a.get('extension')).lower()
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
            analysis = analyze_zip(bytes(buf))
            state = 'ZIP_STRUCTURE_CAPTURED'
        except Exception as exc:
            technical_unknown += 1
            analysis = {'error': repr(exc)[:500]}
            state = 'ZIP_STRUCTURE_UNKNOWN'
        records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'downloaded_byte_count': len(buf), 'analysis': analysis, 'technical_state': state})
        print('SAMPLE:', idx, '/', len(samples), 'EXT:', ext, 'GAZETTE:', a.get('gazette_number'), 'pstSn:', a.get('pstSn'), 'MEMBERS:', analysis.get('zip_member_count'), 'XMLISH:', analysis.get('xmlish_member_count'), 'PARSE_ERRORS:', analysis.get('parse_error_count'))
        print('TEXT_BEARING_TAGS:', analysis.get('aggregate_text_bearing_tags'))

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S117',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'summary': {
            'sample_format_count': len(samples),
            'request_count': request_count,
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'semantic_state': 'POST_HWP5_HWPX_HWTX_ZIP_STRUCTURE_FORENSIC_CAPTURED',
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
        raise AssertionError('S117 HWPX/HWTX ZIP structure forensic failed')


if __name__ == '__main__':
    main()
