# -*- coding: utf-8 -*-
"""S119: determine whether HWPX/HWTX XML-like members contain nested compression/binary payloads.

S118 showed that most *.xml members decode as binary garbage. This stage inventories ZIP entry
metadata (compression method, flags, sizes, CRC), captures post-zipfile-read byte signatures,
and safely probes common nested decompression transforms (zlib, raw DEFLATE, gzip) on only the
same deterministic HWPX/HWTX samples.

No target-term search, OCR, legal inference, candidate promotion, SITE/runtime mutation, or
binary retention is allowed.
"""
from __future__ import annotations

import gzip
import io
import json
import math
import zlib
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwpx_hwtx_nested_compression_forensic.json'

HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
FORMATS = ['hwpx', 'hwtx']
MAX_REQUESTS = 2
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 40 * 1024 * 1024
NESTED_OUTPUT_LIMIT = 16 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


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


def entropy(data):
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c/n) * math.log2(c/n) for c in counts.values())


def looks_xml(data):
    head = data[:512].lstrip(b'\xef\xbb\xbf\x00\x20\t\r\n')
    return head.startswith(b'<?xml') or head.startswith(b'<')


def safe_nested_probe(data):
    attempts = []
    specs = [
        ('zlib', lambda b: zlib.decompress(b)),
        ('raw_deflate', lambda b: zlib.decompress(b, -zlib.MAX_WBITS)),
        ('gzip', lambda b: gzip.decompress(b)),
    ]
    for name, fn in specs:
        try:
            out = fn(data)
            if len(out) > NESTED_OUTPUT_LIMIT:
                attempts.append({'method': name, 'success': False, 'error': f'output_limit_exceeded:{len(out)}'})
                continue
            attempts.append({
                'method': name,
                'success': True,
                'output_size': len(out),
                'output_prefix_hex': out[:32].hex(),
                'output_looks_xml': looks_xml(out),
                'output_entropy': round(entropy(out[:262144]), 4),
            })
        except Exception as exc:
            attempts.append({'method': name, 'success': False, 'error': repr(exc)[:300]})
    return attempts


def analyze_zip(data):
    records = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if not info.filename.lower().endswith(('.xml', '.xhtml', '.html')):
                continue
            payload = zf.read(info.filename)
            rec = {
                'name': info.filename,
                'zip_compress_type': info.compress_type,
                'zip_flag_bits': info.flag_bits,
                'zip_file_size': info.file_size,
                'zip_compress_size': info.compress_size,
                'zip_crc': info.CRC,
                'payload_size': len(payload),
                'payload_prefix_hex': payload[:32].hex(),
                'payload_looks_xml': looks_xml(payload),
                'payload_entropy': round(entropy(payload[:262144]), 4),
                'nested_decompression_attempts': safe_nested_probe(payload),
            }
            records.append(rec)
    return records


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 HWPX/HWTX NESTED COMPRESSION FORENSIC - S119')
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
            members = analyze_zip(bytes(buf))
            state = 'NESTED_COMPRESSION_FORENSIC_CAPTURED'
        except Exception as exc:
            technical_unknown += 1
            members = []
            state = 'ZIP_ANALYSIS_UNKNOWN'
            err = repr(exc)[:500]
        else:
            err = ''

        records.append({**a, 'http_status': resp.status_code, 'official_host': official, 'downloaded_byte_count': len(buf), 'xmlish_member_count': len(members), 'members': members, 'technical_state': state, 'error': err})
        print('SAMPLE:', idx, '/', len(samples), 'EXT:', a.get('extension'), 'XMLISH:', len(members))
        for m in members[:15]:
            successes = [x for x in m['nested_decompression_attempts'] if x.get('success')]
            print('MEMBER:', m['name'], '| ZIP_METHOD:', m['zip_compress_type'], '| FLAGS:', m['zip_flag_bits'], '| SIZE:', m['payload_size'], '| PREFIX:', m['payload_prefix_hex'][:24], '| ENTROPY:', m['payload_entropy'], '| XML:', m['payload_looks_xml'], '| NESTED_OK:', successes)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S119',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'input_registry': str(REGISTRY),
        'registry_identity_sha256': summary.get('registry_identity_sha256'),
        'summary': {
            'sample_format_count': len(samples),
            'request_count': request_count,
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'semantic_state': 'POST_HWP5_HWPX_HWTX_NESTED_COMPRESSION_FORENSIC_CAPTURED',
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
        raise AssertionError('S119 nested compression forensic failed')


if __name__ == '__main__':
    main()
