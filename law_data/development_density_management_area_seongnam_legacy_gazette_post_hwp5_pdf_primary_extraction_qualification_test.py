# -*- coding: utf-8 -*-
"""S123: qualify PDF-primary extraction on a deterministic sample of S122-authorized rows.

This stage reads S113 metadata and S122 pairing policy, selects a small deterministic sample from
PDF-primary-authorized rows (including the PDF-only case when present), downloads only those PDFs,
and verifies text-layer extraction with pypdf. It does not search UQQ700 terms and does not infer
legal absence from extraction success or failure.
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
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pdf_primary_extraction_qualification.json'
EXPECTED_REGISTRY_SHA = '1df06268311b3d1a1a1922bb3266c1cd26001477c4e8e688e22cbbbe98f3e570'
HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
MAX_REQUESTS = 6
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TOTAL_BYTE_LIMIT = 96 * 1024 * 1024
TIMEOUT = 30
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v):
    return str(v or '').strip()


def pick_samples(rows):
    eligible = [r for r in rows if r.get('proposed_policy') in {'PDF_PRIMARY', 'PDF_PRIMARY_SOURCE_REPRESENTATION_PAIRED'}]
    eligible.sort(key=lambda r: (str(r.get('date') or ''), int(r.get('gazette_number') or 0), int(r.get('pstSn') or 0)))
    if len(eligible) < MAX_REQUESTS:
        raise AssertionError('insufficient PDF-primary rows')
    idxs = [0, len(eligible)//5, (len(eligible)*2)//5, (len(eligible)*3)//5, (len(eligible)*4)//5, len(eligible)-1]
    picked = []
    seen = set()
    for i in idxs:
        r = eligible[i]
        pst = str(r.get('pstSn'))
        if pst not in seen:
            picked.append(r)
            seen.add(pst)
    for r in eligible:
        if len(picked) >= MAX_REQUESTS:
            break
        pst = str(r.get('pstSn'))
        if pst not in seen:
            picked.append(r)
            seen.add(pst)
    return picked[:MAX_REQUESTS]


def pdf_attachment(row):
    pdfs = [a for a in (row.get('attachments') or []) if norm(a.get('extension')).lower() == 'pdf']
    if not pdfs:
        raise AssertionError(f'authorized row without PDF: {row.get("pstSn")}')
    pdfs.sort(key=lambda a: (int(a.get('position') or 0), int(a.get('fileNo') or 0)))
    return pdfs[0]


def extract_text(data):
    reader = PdfReader(io.BytesIO(data))
    texts = []
    page_errors = 0
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or '')
        except Exception:
            page_errors += 1
    text = '\n'.join(texts)
    return len(reader.pages), page_errors, len(text.strip())


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 PDF PRIMARY EXTRACTION QUALIFICATION - S123')
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

    samples = pick_samples(pairing.get('rows') or [])
    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    request_count = 0
    total_bytes = 0
    technical_unknown = 0
    qualified = 0
    records = []

    for idx, row in enumerate(samples, 1):
        a = pdf_attachment(row)
        params = {'bbsCrtSn': BBS_CRT_SN, 'pstSn': str(row.get('pstSn')), 'fileNo': str(a.get('fileNo'))}
        request_count += 1
        try:
            resp = session.get(DOWNLOAD, params=params, timeout=TIMEOUT, allow_redirects=True, stream=True)
        except Exception as exc:
            technical_unknown += 1
            records.append({'pstSn': row.get('pstSn'), 'gazette_number': row.get('gazette_number'), 'technical_state': 'TRANSPORT_ERROR', 'error': repr(exc)[:500]})
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
            technical_unknown += 1
            records.append({'pstSn': row.get('pstSn'), 'gazette_number': row.get('gazette_number'), 'http_status': resp.status_code, 'official_host': official, 'byte_limit_overflow': overflow, 'pdf_magic': bytes(buf).startswith(b'%PDF'), 'technical_state': 'DOWNLOAD_OR_FORMAT_UNKNOWN'})
            continue
        try:
            page_count, page_errors, text_len = extract_text(bytes(buf))
        except Exception as exc:
            technical_unknown += 1
            records.append({'pstSn': row.get('pstSn'), 'gazette_number': row.get('gazette_number'), 'technical_state': 'PDF_EXTRACTION_UNKNOWN', 'error': repr(exc)[:500]})
            continue
        state = 'PDF_TEXT_LAYER_QUALIFIED' if text_len > 0 else 'PDF_TEXT_LAYER_EMPTY'
        if state == 'PDF_TEXT_LAYER_QUALIFIED':
            qualified += 1
        else:
            technical_unknown += 1
        rec = {'pstSn': row.get('pstSn'), 'gazette_number': row.get('gazette_number'), 'date': row.get('date'), 'filename': a.get('filename'), 'fileNo': a.get('fileNo'), 'downloaded_byte_count': len(buf), 'page_count': page_count, 'page_extraction_error_count': page_errors, 'extracted_text_length': text_len, 'technical_state': state}
        records.append(rec)
        print('SAMPLE:', idx, '/', len(samples), 'GAZETTE:', row.get('gazette_number'), 'pstSn:', row.get('pstSn'), 'PAGES:', page_count, 'PAGE_ERRORS:', page_errors, 'TEXT_LEN:', text_len, 'STATE:', state)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S123',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'registry_identity_sha256': EXPECTED_REGISTRY_SHA,
        'summary': {
            'sample_count': len(samples),
            'request_count': request_count,
            'qualified_count': qualified,
            'technical_unknown_count': technical_unknown,
            'total_downloaded_bytes': total_bytes,
            'semantic_state': 'POST_HWP5_PDF_PRIMARY_EXTRACTION_QUALIFICATION_CAPTURED',
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
        raise AssertionError('S123 PDF primary extraction qualification failed')


if __name__ == '__main__':
    main()
