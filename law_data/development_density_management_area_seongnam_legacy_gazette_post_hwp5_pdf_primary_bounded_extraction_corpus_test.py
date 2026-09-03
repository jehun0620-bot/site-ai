# -*- coding: utf-8 -*-
"""S124: build a bounded PDF text-layer extraction corpus for S122-authorized POST-HWP5 rows.

Inputs are the S113 attachment registry and S122 representation pairing policy. Only rows already
classified as PDF-primary-authorized are processed. This stage downloads one PDF per authorized row,
extracts the pypdf text layer, stores text in the output JSON for later candidate search, and records
technical failures separately. It does NOT search UQQ700 terms, infer legal absence, promote SITE
state, use OCR, or process the one pairing-review row and five no-PDF rows.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.parse import urlparse

import requests
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_attachment_metadata_registry.json'
PAIRING = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_representation_pairing_policy.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pdf_primary_bounded_extraction_corpus.json'

EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
EXPECTED_AUTHORIZED_ROWS = 213
MAX_REQUESTS = 213
PER_FILE_BYTE_LIMIT = 64 * 1024 * 1024
TOTAL_BYTE_LIMIT = 1024 * 1024 * 1024
TIMEOUT = 45
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v):
    return str(v or '').strip()


def authorized_rows(pairing):
    rows = [r for r in (pairing.get('rows') or []) if r.get('proposed_policy') in {'PDF_PRIMARY', 'PDF_PRIMARY_SOURCE_REPRESENTATION_PAIRED'}]
    rows.sort(key=lambda r: (str(r.get('date') or ''), int(r.get('gazette_number') or 0), int(r.get('pstSn') or 0)))
    return rows


def pdf_attachment(row):
    pdfs = [a for a in (row.get('attachments') or []) if norm(a.get('extension')).lower() == 'pdf']
    if not pdfs:
        raise AssertionError(f'authorized row without PDF: {row.get("pstSn")}')
    pdfs.sort(key=lambda a: (int(a.get('position') or 0), int(a.get('fileNo') or 0)))
    return pdfs[0]


def extract_pdf_text(data):
    reader = PdfReader(io.BytesIO(data))
    texts = []
    page_errors = 0
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or '')
        except Exception:
            page_errors += 1
    text = '\n'.join(texts)
    return len(reader.pages), page_errors, text


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 PDF PRIMARY BOUNDED EXTRACTION CORPUS - S124')
    print('=' * 60)
    print('OCR: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    pairing = json.loads(PAIRING.read_text(encoding='utf-8'))
    rsum = reg.get('summary') or {}
    if rsum.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('registry identity mismatch')
    if pairing.get('registry_identity_sha256') != EXPECTED_REGISTRY_SHA:
        raise AssertionError('pairing registry identity mismatch')

    rows = authorized_rows(pairing)
    if len(rows) != EXPECTED_AUTHORIZED_ROWS:
        raise AssertionError(f'authorized row count mismatch: {len(rows)}')

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    records = []
    request_count = 0
    total_bytes = 0
    extracted_count = 0
    technical_unknown_count = 0
    total_pages = 0
    total_text_length = 0

    for idx, row in enumerate(rows, 1):
        a = pdf_attachment(row)
        params = {'bbsCrtSn': BBS_CRT_SN, 'pstSn': str(row.get('pstSn')), 'fileNo': str(a.get('fileNo'))}
        request_count += 1
        base_rec = {
            'pstSn': row.get('pstSn'),
            'gazette_number': row.get('gazette_number'),
            'date': row.get('date'),
            'policy': row.get('proposed_policy'),
            'filename': a.get('filename'),
            'fileNo': a.get('fileNo'),
        }
        try:
            resp = session.get(DOWNLOAD, params=params, timeout=TIMEOUT, allow_redirects=True, stream=True)
        except Exception as exc:
            technical_unknown_count += 1
            records.append({**base_rec, 'technical_state': 'TRANSPORT_ERROR', 'error': repr(exc)[:500]})
            print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'STATE: TRANSPORT_ERROR')
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

        if resp.status_code != 200 or not official or overflow or not bytes(buf).startswith(b'%PDF'):
            technical_unknown_count += 1
            records.append({**base_rec, 'http_status': resp.status_code, 'official_host': official, 'byte_limit_overflow': overflow, 'pdf_magic': bytes(buf).startswith(b'%PDF'), 'downloaded_byte_count': len(buf), 'technical_state': 'DOWNLOAD_OR_FORMAT_UNKNOWN'})
            print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'STATE: DOWNLOAD_OR_FORMAT_UNKNOWN')
            continue

        try:
            page_count, page_errors, text = extract_pdf_text(bytes(buf))
        except Exception as exc:
            technical_unknown_count += 1
            records.append({**base_rec, 'downloaded_byte_count': len(buf), 'technical_state': 'PDF_EXTRACTION_UNKNOWN', 'error': repr(exc)[:500]})
            print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'STATE: PDF_EXTRACTION_UNKNOWN')
            continue

        text_len = len(text.strip())
        total_pages += page_count
        total_text_length += text_len
        if text_len > 0:
            state = 'PDF_TEXT_LAYER_EXTRACTED'
            extracted_count += 1
        else:
            state = 'PDF_TEXT_LAYER_EMPTY'
            technical_unknown_count += 1

        records.append({
            **base_rec,
            'downloaded_byte_count': len(buf),
            'page_count': page_count,
            'page_extraction_error_count': page_errors,
            'extracted_text_length': text_len,
            'extracted_text': text if text_len > 0 else '',
            'technical_state': state,
        })
        print('ROW:', idx, '/', len(rows), 'GAZETTE:', row.get('gazette_number'), 'PAGES:', page_count, 'PAGE_ERRORS:', page_errors, 'TEXT_LEN:', text_len, 'STATE:', state)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S124',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'registry_identity_sha256': EXPECTED_REGISTRY_SHA,
        'summary': {
            'authorized_row_count': len(rows),
            'request_count': request_count,
            'extracted_count': extracted_count,
            'technical_unknown_count': technical_unknown_count,
            'total_downloaded_bytes': total_bytes,
            'total_page_count': total_pages,
            'total_extracted_text_length': total_text_length,
            'excluded_pairing_review_row_count': 1,
            'excluded_no_pdf_row_count': 5,
            'semantic_state': 'POST_HWP5_PDF_PRIMARY_BOUNDED_EXTRACTION_CORPUS_CAPTURED',
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
        'registry identity exact': rsum.get('registry_identity_sha256') == EXPECTED_REGISTRY_SHA,
        'authorized row count exact': len(rows) == EXPECTED_AUTHORIZED_ROWS,
        'request budget exact': request_count == MAX_REQUESTS,
        'all authorized rows accounted': len(records) == EXPECTED_AUTHORIZED_ROWS,
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
        raise AssertionError('S124 PDF primary bounded extraction corpus failed')


if __name__ == '__main__':
    main()
