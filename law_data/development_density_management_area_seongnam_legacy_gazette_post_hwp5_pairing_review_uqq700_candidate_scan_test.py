# -*- coding: utf-8 -*-
"""S129: scan the qualified Gazette 2037 pairing-review PDF text for UQQ700 candidates.

Input is the S128 forensic output only. This stage is offline and restricted to pstSn 377485 /
Gazette 2037, whose PDF row identity was qualified in S128. Hits are candidates only; no legal
TRUE/FALSE, negative evidence, SITE promotion, or runtime registration is authorized.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
S128 = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_exception_coverage_forensic.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pairing_review_uqq700_candidate_scan.json'

EXPECTED_PST = '377485'
EXPECTED_GAZETTE = '2037'
CONTEXT_RADIUS = 260
DIRECT_PATTERNS = [
    ('TARGET_NAME', re.compile(r'개발\s*밀도\s*관리\s*구역')),
    ('STANDARD_CODE', re.compile(r'UQQ\s*700', re.I)),
]
RELATED_PATTERNS = [
    ('DEVELOPMENT_DENSITY_MANAGEMENT', re.compile(r'개발\s*밀도\s*관리')),
    ('DEVELOPMENT_DENSITY', re.compile(r'개발\s*밀도')),
]


def compact_context(text, start, end):
    lo = max(0, start - CONTEXT_RADIUS)
    hi = min(len(text), end + CONTEXT_RADIUS)
    return re.sub(r'\s+', ' ', text[lo:hi]).strip()


def collect(text, patterns):
    out = []
    for label, pat in patterns:
        matches = list(pat.finditer(text))
        if matches:
            out.append({
                'term': label,
                'occurrence_count': len(matches),
                'contexts': [
                    {'matched_text': m.group(0), 'context': compact_context(text, m.start(), m.end())}
                    for m in matches[:8]
                ],
            })
    return out


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 PAIRING-REVIEW UQQ700 CANDIDATE SCAN - S129')
    print('=' * 60)
    print('Network: DISABLED')
    print('Negative evidence: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    src = json.loads(S128.read_text(encoding='utf-8'))
    review = src.get('pairing_review') or {}
    if str(review.get('pstSn')) != EXPECTED_PST:
        raise AssertionError('S128 pairing-review pst mismatch')
    if str(review.get('gazette_number')) != EXPECTED_GAZETTE:
        raise AssertionError('S128 gazette mismatch')
    if review.get('coverage_state') != 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED':
        raise AssertionError('S128 PDF identity is not qualified')
    if review.get('page_extraction_error_count') != 0:
        raise AssertionError('S128 PDF page extraction errors present')
    text = str(review.get('extracted_text') or '')
    if not text.strip():
        raise AssertionError('S128 extracted text missing')

    direct = collect(text, DIRECT_PATTERNS)
    related = collect(text, RELATED_PATTERNS)
    if direct:
        status = 'DIRECT_CANDIDATE'
    elif related:
        status = 'RELATED_CANDIDATE'
    else:
        status = 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT'

    print('GAZETTE:', EXPECTED_GAZETTE, '| pstSn:', EXPECTED_PST, '| STATUS:', status)
    for hit in direct + related:
        print('TERM:', hit['term'], '| COUNT:', hit['occurrence_count'])
        for c in hit['contexts'][:4]:
            print(' CONTEXT:', c['context'])

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S129',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'record': {
            'pstSn': EXPECTED_PST,
            'gazette_number': EXPECTED_GAZETTE,
            'date': review.get('date'),
            'pdf_filename': review.get('pdf_filename'),
            'status': status,
            'direct_hits': direct,
            'related_hits': related,
        },
        'summary': {
            'scanned_row_count': 1,
            'direct_candidate_row_count': 1 if status == 'DIRECT_CANDIDATE' else 0,
            'related_candidate_row_count': 1 if status == 'RELATED_CANDIDATE' else 0,
            'no_candidate_term_row_count': 1 if status == 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT' else 0,
            'direct_occurrence_count': sum(x['occurrence_count'] for x in direct),
            'related_occurrence_count': sum(x['occurrence_count'] for x in related),
            'semantic_state': 'POST_HWP5_PAIRING_REVIEW_UQQ700_CANDIDATE_SCAN_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'network_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'pairing review identity exact': str(review.get('pstSn')) == EXPECTED_PST,
        'PDF identity qualified': review.get('coverage_state') == 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED',
        'page extraction errors zero': review.get('page_extraction_error_count') == 0,
        'one row accounted': sum(out['summary'][k] for k in ['direct_candidate_row_count', 'related_candidate_row_count', 'no_candidate_term_row_count']) == 1,
        'network disabled': not out['network_executed'],
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
        raise AssertionError('S129 pairing-review UQQ700 candidate scan failed')


if __name__ == '__main__':
    main()
