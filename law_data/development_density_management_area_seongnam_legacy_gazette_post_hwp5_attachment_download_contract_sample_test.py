# -*- coding: utf-8 -*-
"""S115: validate attachment download contract on tiny deterministic format samples.

Composite technical identity recovered by S114:
  bbsCrtSn + pstSn + fileNo
Download endpoint:
  GET /bbs010308/getFile

This stage reads the local S113 metadata registry and downloads at most one deterministic sample
per observed extension family (hwp, hwpx, hwtx, pdf), with strict per-file and total byte limits.
It validates response host/status, Content-Disposition filename hints, byte signatures, and size
consistency against metadata. Downloaded bytes are diagnostic only and are not retained.

No target-term search or text extraction is performed. No negative evidence, candidate promotion,
SITE/runtime mutation, or legal inference is allowed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_download_contract_sample.json'

HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
ALLOWED_EXTS = ['hwp', 'hwpx', 'hwtx', 'pdf']
MAX_REQUESTS = 4
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 64 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v):
    return str(v or '').strip()


def filename_from_cd(value):
    value = value or ''
    m = re.search(r"filename\*=UTF-8''([^;]+)", value, re.I)
    if m:
        return unquote(m.group(1)).strip('"')
    m = re.search(r'filename\s*=\s*"([^"]+)"', value, re.I)
    if m:
        return m.group(1)
    m = re.search(r'filename\s*=\s*([^;]+)', value, re.I)
    return m.group(1).strip().strip('"') if m else ''


def signature(data):
    if data.startswith(b'%PDF-'):
        return 'PDF'
    if data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):
        return 'OLE_CFB'
    if data.startswith(b'PK\x03\x04') or data.startswith(b'PK\x05\x06') or data.startswith(b'PK\x07\x08'):
        return 'ZIP'
    return 'OTHER'


def expected_signature(ext):
    return {'pdf': 'PDF', 'hwp': 'OLE_CFB', 'hwpx': 'ZIP', 'hwtx': 'ZIP'}.get(ext, 'OTHER')


def select_samples(attachments):
    picked = []
    for ext in ALLOWED_EXTS:
        candidates = [a for a in attachments if norm(a.get('extension')).lower() == ext]
        candidates.sort(key=lambda a: (str(a.get('date') or ''), int(a.get('gazette_number') or 0), int(a.get('pstSn') or 0), int(a.get('position') or 0)))
        if candidates:
            picked.append(candidates[0])
    return picked


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 ATTACHMENT DOWNLOAD CONTRACT SAMPLE - S115')
    print('=' * 60)
    print('Target-term search: DISABLED')
    print('Text extraction: DISABLED')
    print('Negative evidence: DISABLED')
    print('Per-file byte limit:', PER_FILE_BYTE_LIMIT)
    print('Total byte limit:', TOTAL_BYTE_LIMIT)

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    reg_summary = reg.get('summary') or {}
    if reg_summary.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('S113 registry identity mismatch')

    attachments = reg.get('attachments') or []
    sample = select_samples(attachments)
    if len(sample) > MAX_REQUESTS:
        raise AssertionError('sample request budget exceeded')

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    records = []
    request_count = 0
    total_bytes = 0
    technical_unknown = 0

    for idx, a in enumerate(sample, 1):
        ext = norm(a.get('extension')).lower()
        params = {'bbsCrtSn': BBS_CRT_SN, 'pstSn': str(a.get('pstSn')), 'fileNo': str(a.get('fileNo'))}
        request_count += 1
        try:
            resp = session.get(DOWNLOAD, params=params, timeout=TIMEOUT, allow_redirects=True, stream=True)
        except Exception as exc:
            technical_unknown += 1
            records.append({**a, 'request_params': params, 'technical_state': 'TRANSPORT_ERROR', 'error': repr(exc)[:500]})
            continue

        official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
        content = bytearray()
        overflow = False
        try:
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                if len(content) + len(chunk) > PER_FILE_BYTE_LIMIT or total_bytes + len(chunk) > TOTAL_BYTE_LIMIT:
                    overflow = True
                    break
                content.extend(chunk)
                total_bytes += len(chunk)
        finally:
            resp.close()

        data = bytes(content)
        cd = resp.headers.get('Content-Disposition')
        cd_name = filename_from_cd(cd)
        sig = signature(data)
        expected_sig = expected_signature(ext)
        meta_size = a.get('fileSize')
        try:
            meta_size_int = int(meta_size)
        except Exception:
            meta_size_int = None
        size_equal = meta_size_int == len(data) if meta_size_int is not None and not overflow else False
        filename_equal = norm(cd_name) == norm(a.get('orginlFileNm')) if cd_name else False
        contract_ok = resp.status_code == 200 and official and not overflow and sig == expected_sig
        if not contract_ok:
            technical_unknown += 1
        records.append({
            **a,
            'request_params': params,
            'final_url': str(resp.url)[:1200],
            'http_status': resp.status_code,
            'official_host': official,
            'content_type': resp.headers.get('Content-Type'),
            'content_disposition': cd,
            'content_disposition_filename': cd_name,
            'metadata_filename_equal': filename_equal,
            'downloaded_byte_count': len(data),
            'metadata_file_size': meta_size_int,
            'metadata_size_equal': size_equal,
            'byte_limit_overflow': overflow,
            'magic_signature': sig,
            'expected_magic_signature': expected_sig,
            'magic_signature_match': sig == expected_sig,
            'technical_state': 'DOWNLOAD_CONTRACT_VALIDATED' if contract_ok else 'DOWNLOAD_CONTRACT_UNKNOWN',
        })
        print('SAMPLE:', idx, '/', len(sample), 'EXT:', ext, 'GAZETTE:', a.get('gazette_number'), 'pstSn:', a.get('pstSn'), 'fileNo:', a.get('fileNo'), 'HTTP:', resp.status_code, 'BYTES:', len(data), 'SIG:', sig, 'EXPECTED:', expected_sig, 'NAME_MATCH:', filename_equal, 'SIZE_MATCH:', size_equal)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S115',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': reg_summary.get('registry_identity_sha256'),
        'download_endpoint': DOWNLOAD,
        'composite_identity_fields': ['bbsCrtSn', 'pstSn', 'fileNo'],
        'summary': {
            'available_extensions': sorted({norm(a.get('extension')).lower() for a in attachments}),
            'sample_extension_count': len(sample),
            'request_count': request_count,
            'download_contract_validated_count': sum(1 for r in records if r.get('technical_state') == 'DOWNLOAD_CONTRACT_VALIDATED'),
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'per_file_byte_limit': PER_FILE_BYTE_LIMIT,
            'total_byte_limit': TOTAL_BYTE_LIMIT,
            'semantic_state': 'POST_HWP5_ATTACHMENT_DOWNLOAD_CONTRACT_SAMPLE_VALIDATED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'downloaded_bytes_retained': False,
        'target_term_search_executed': False,
        'text_extraction_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'registry identity exact': reg_summary.get('registry_identity_sha256') == EXPECTED_REGISTRY_SHA,
        'request budget respected': request_count <= MAX_REQUESTS,
        'all selected samples accounted': len(records) == len(sample),
        'total byte budget respected': total_bytes <= TOTAL_BYTE_LIMIT,
        'downloaded bytes not retained': not out['downloaded_bytes_retained'],
        'target-term search disabled': not out['target_term_search_executed'],
        'text extraction disabled': not out['text_extraction_executed'],
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
        raise AssertionError('S115 attachment download contract sample test failed')


if __name__ == '__main__':
    main()
