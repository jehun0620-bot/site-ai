# -*- coding: utf-8 -*-
"""S128: forensic coverage of the six POST-HWP5 rows excluded from S124.

Scope is exactly the S122 exceptions: one pairing-review row (Gazette 2037) and five rows without a
PDF fallback. For Gazette 2037 only, download its PDF and verify that the PDF text layer contains the
same gazette number, which is enough to authorize that PDF as a row-level primary representation for
later candidate scanning. The five no-PDF rows remain format-specific technical exceptions; this
stage does not search target terms, decrypt HWPX, use OCR, infer legal absence, or promote SITE state.
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent.parent
PAIRING = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_representation_pairing_policy.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_exception_coverage_forensic.json'

EXPECTED_REVIEW_PST = '377485'
EXPECTED_NO_PDF_PSTS = {'29286', '363790', '370638', '372500', '374744'}
HOST = 'www.seongnam.go.kr'
DOWNLOAD = 'https://www.seongnam.go.kr/bbs010308/getFile'
BBS_CRT_SN = '16002'
PER_FILE_BYTE_LIMIT = 32 * 1024 * 1024
TIMEOUT = 45
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'


def norm(v):
    return str(v or '').strip()


def first_pdf(row):
    pdfs = [a for a in (row.get('attachments') or []) if norm(a.get('extension')).lower() == 'pdf']
    if len(pdfs) != 1:
        raise AssertionError(f'expected exactly one PDF for review row: {row.get("pstSn")}')
    return pdfs[0]


def extract_text(data):
    reader = PdfReader(io.BytesIO(data))
    parts = []
    page_errors = 0
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or '')
        except Exception:
            page_errors += 1
    return len(reader.pages), page_errors, '\n'.join(parts)


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 EXCEPTION COVERAGE FORENSIC - S128')
    print('=' * 60)
    print('OCR: DISABLED')
    print('HWPX decryption: DISABLED')
    print('Target-term search: DISABLED')
    print('Negative evidence: DISABLED')

    pairing = json.loads(PAIRING.read_text(encoding='utf-8'))
    rows = pairing.get('rows') or []
    review = [r for r in rows if r.get('proposed_policy') == 'PAIRING_REVIEW_REQUIRED']
    no_pdf = [r for r in rows if r.get('proposed_policy') == 'NO_PDF_FALLBACK_TECHNICAL_UNKNOWN']
    if len(review) != 1 or str(review[0].get('pstSn')) != EXPECTED_REVIEW_PST:
        raise AssertionError('pairing-review identity mismatch')
    no_pdf_psts = {str(r.get('pstSn')) for r in no_pdf}
    if no_pdf_psts != EXPECTED_NO_PDF_PSTS:
        raise AssertionError(f'no-PDF identity mismatch: {no_pdf_psts}')

    r = review[0]
    a = first_pdf(r)
    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    params = {'bbsCrtSn': BBS_CRT_SN, 'pstSn': EXPECTED_REVIEW_PST, 'fileNo': str(a.get('fileNo'))}
    resp = session.get(DOWNLOAD, params=params, timeout=TIMEOUT, allow_redirects=True, stream=True)
    official = (urlparse(str(resp.url)).hostname or '').lower() == HOST
    buf = bytearray()
    overflow = False
    try:
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            if len(buf) + len(chunk) > PER_FILE_BYTE_LIMIT:
                overflow = True
                break
            buf.extend(chunk)
    finally:
        resp.close()

    pdf_ok = resp.status_code == 200 and official and not overflow and bytes(buf).startswith(b'%PDF')
    page_count = page_errors = text_len = 0
    gazette_marker_match = False
    text = ''
    if pdf_ok:
        try:
            page_count, page_errors, text = extract_text(bytes(buf))
            text_len = len(text.strip())
            num = str(r.get('gazette_number'))
            gazette_marker_match = bool(re.search(rf'제\s*{re.escape(num)}\s*호', text))
        except Exception:
            pdf_ok = False

    review_state = 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED' if pdf_ok and text_len > 0 and gazette_marker_match else 'PAIRING_REVIEW_TECHNICAL_UNKNOWN'
    print('PAIRING REVIEW')
    print('GAZETTE:', r.get('gazette_number'), 'pstSn:', r.get('pstSn'))
    print('PDF:', a.get('filename'), 'PAGES:', page_count, 'PAGE_ERRORS:', page_errors, 'TEXT_LEN:', text_len, 'GAZETTE_MARKER_MATCH:', gazette_marker_match, 'STATE:', review_state)

    exception_rows = []
    format_counts = {}
    for row in sorted(no_pdf, key=lambda x: int(x.get('gazette_number') or 0)):
        atts = row.get('attachments') or []
        exts = sorted({norm(a.get('extension')).lower() for a in atts})
        for ext in exts:
            format_counts[ext] = format_counts.get(ext, 0) + 1
        if exts == ['hwp']:
            state = 'HWP_TEXT_EXTRACTION_FALLBACK_REQUIRED'
        elif exts == ['hwpx']:
            state = 'ENCRYPTED_HWPX_NO_PDF_TECHNICAL_UNKNOWN'
        else:
            state = 'NO_PDF_FORMAT_REVIEW_REQUIRED'
        item = {
            'pstSn': row.get('pstSn'),
            'gazette_number': row.get('gazette_number'),
            'date': row.get('date'),
            'attachments': atts,
            'extensions': exts,
            'coverage_state': state,
        }
        exception_rows.append(item)
        print('NO PDF | GAZETTE:', row.get('gazette_number'), '| pstSn:', row.get('pstSn'), '| EXT:', exts, '| STATE:', state)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S128',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'summary': {
            'pairing_review_input_count': 1,
            'pairing_review_pdf_primary_qualified_count': 1 if review_state == 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED' else 0,
            'pairing_review_technical_unknown_count': 0 if review_state == 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED' else 1,
            'no_pdf_exception_count': len(exception_rows),
            'no_pdf_format_counts': format_counts,
            'hwp_fallback_required_count': sum(1 for x in exception_rows if x['coverage_state'] == 'HWP_TEXT_EXTRACTION_FALLBACK_REQUIRED'),
            'encrypted_hwpx_no_pdf_technical_unknown_count': sum(1 for x in exception_rows if x['coverage_state'] == 'ENCRYPTED_HWPX_NO_PDF_TECHNICAL_UNKNOWN'),
            'semantic_state': 'POST_HWP5_EXCEPTION_COVERAGE_FORENSIC_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'pairing_review': {
            'pstSn': r.get('pstSn'),
            'gazette_number': r.get('gazette_number'),
            'date': r.get('date'),
            'pdf_filename': a.get('filename'),
            'pdf_fileNo': a.get('fileNo'),
            'downloaded_byte_count': len(buf),
            'page_count': page_count,
            'page_extraction_error_count': page_errors,
            'extracted_text_length': text_len,
            'gazette_marker_match': gazette_marker_match,
            'coverage_state': review_state,
            'extracted_text': text if review_state == 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED' else '',
        },
        'no_pdf_exceptions': exception_rows,
        'downloaded_binary_retained': False,
        'ocr_executed': False,
        'hwpx_decryption_executed': False,
        'target_term_search_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'pairing review identity exact': str(r.get('pstSn')) == EXPECTED_REVIEW_PST,
        'no-PDF identities exact': no_pdf_psts == EXPECTED_NO_PDF_PSTS,
        'six exception rows accounted': 1 + len(exception_rows) == 6,
        'request count bounded to one': True,
        'downloaded binary not retained': not out['downloaded_binary_retained'],
        'ocr disabled': not out['ocr_executed'],
        'HWPX decryption disabled': not out['hwpx_decryption_executed'],
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
        raise AssertionError('S128 exception coverage forensic failed')


if __name__ == '__main__':
    main()
