# -*- coding: utf-8 -*-
"""S125: scan the fixed S124 PDF text corpus for UQQ700 candidates only.

This is an offline candidate-discovery stage. A hit is not a legal fact and cannot promote SITE
TRUE/FALSE. Direct candidates are exact target-name/code occurrences after whitespace normalization.
Related candidates use only narrow lexical signals ('개발밀도관리', '개발밀도') and are retained for
later context inspection. No negative evidence is authorized when no hit is found.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pdf_primary_bounded_extraction_corpus.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_candidate_scan.json'

EXPECTED_ROWS = 213
EXPECTED_EXTRACTED = 213
EXPECTED_TECH_UNKNOWN = 0
TARGET = '개발밀도관리구역'
CODE = 'UQQ700'
DIRECT_PATTERNS = [
    ('TARGET_NAME', re.compile(r'개발\s*밀도\s*관리\s*구역')),
    ('STANDARD_CODE', re.compile(r'UQQ\s*700', re.I)),
]
RELATED_PATTERNS = [
    ('DEVELOPMENT_DENSITY_MANAGEMENT', re.compile(r'개발\s*밀도\s*관리')),
    ('DEVELOPMENT_DENSITY', re.compile(r'개발\s*밀도')),
]
CONTEXT_RADIUS = 220
MAX_CONTEXTS_PER_TERM_PER_ROW = 8


def compact_context(text, start, end):
    lo = max(0, start - CONTEXT_RADIUS)
    hi = min(len(text), end + CONTEXT_RADIUS)
    return re.sub(r'\s+', ' ', text[lo:hi]).strip()


def collect_hits(text, patterns):
    hits = []
    for label, pattern in patterns:
        count = 0
        contexts = []
        for m in pattern.finditer(text):
            count += 1
            if len(contexts) < MAX_CONTEXTS_PER_TERM_PER_ROW:
                contexts.append({'start': m.start(), 'end': m.end(), 'matched_text': m.group(0), 'context': compact_context(text, m.start(), m.end())})
        if count:
            hits.append({'term': label, 'occurrence_count': count, 'contexts': contexts})
    return hits


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 UQQ700 CANDIDATE SCAN - S125')
    print('=' * 60)
    print('Network: DISABLED')
    print('Candidate promotion: DISABLED')
    print('Negative evidence: DISABLED')

    if not CORPUS.exists():
        raise FileNotFoundError(CORPUS)
    corpus = json.loads(CORPUS.read_text(encoding='utf-8'))
    summary = corpus.get('summary') or {}
    records = corpus.get('records') or []

    if summary.get('authorized_row_count') != EXPECTED_ROWS:
        raise AssertionError('S124 authorized row count mismatch')
    if summary.get('extracted_count') != EXPECTED_EXTRACTED:
        raise AssertionError('S124 extracted count mismatch')
    if summary.get('technical_unknown_count') != EXPECTED_TECH_UNKNOWN:
        raise AssertionError('S124 technical unknown must be zero before S125')
    if len(records) != EXPECTED_ROWS:
        raise AssertionError('S124 record count mismatch')

    candidates = []
    status_counts = Counter()
    total_direct_occurrences = 0
    total_related_occurrences = 0

    for rec in records:
        if rec.get('technical_state') != 'PDF_TEXT_LAYER_EXTRACTED':
            raise AssertionError(f'non-extracted record leaked into S125: {rec.get("pstSn")}')
        text = str(rec.get('extracted_text') or '')
        direct = collect_hits(text, DIRECT_PATTERNS)
        related_all = collect_hits(text, RELATED_PATTERNS)

        # Avoid double-counting related lexical matches inside a direct target occurrence for status.
        direct_count = sum(x['occurrence_count'] for x in direct)
        related_count = sum(x['occurrence_count'] for x in related_all)
        total_direct_occurrences += direct_count
        total_related_occurrences += related_count

        if direct:
            status = 'DIRECT_CANDIDATE'
        elif related_all:
            status = 'RELATED_CANDIDATE'
        else:
            status = 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT'
        status_counts[status] += 1

        if status != 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT':
            item = {
                'pstSn': rec.get('pstSn'),
                'gazette_number': rec.get('gazette_number'),
                'date': rec.get('date'),
                'filename': rec.get('filename'),
                'status': status,
                'direct_hits': direct,
                'related_hits': related_all,
            }
            candidates.append(item)
            print('\nCANDIDATE:', status, '| GAZETTE:', item['gazette_number'], '| pstSn:', item['pstSn'], '| DATE:', item['date'])
            for hit in direct + related_all:
                print(' TERM:', hit['term'], '| COUNT:', hit['occurrence_count'])
                for ctx in hit['contexts'][:3]:
                    print('  CONTEXT:', ctx['context'])

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S125',
        'target_name': TARGET,
        'standard_code': CODE,
        'input_corpus': str(CORPUS),
        'summary': {
            'corpus_row_count': len(records),
            'candidate_row_count': len(candidates),
            'direct_candidate_row_count': status_counts.get('DIRECT_CANDIDATE', 0),
            'related_candidate_row_count': status_counts.get('RELATED_CANDIDATE', 0),
            'no_candidate_term_row_count': status_counts.get('NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT', 0),
            'direct_occurrence_count': total_direct_occurrences,
            'related_occurrence_count': total_related_occurrences,
            'status_counts': dict(status_counts),
            'semantic_state': 'POST_HWP5_UQQ700_CANDIDATE_SCAN_CAPTURED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'candidates': candidates,
        'network_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'S124 corpus row count exact': len(records) == EXPECTED_ROWS,
        'S124 extracted count exact': summary.get('extracted_count') == EXPECTED_EXTRACTED,
        'S124 technical unknown zero': summary.get('technical_unknown_count') == 0,
        'candidate accounting exact': sum(status_counts.values()) == EXPECTED_ROWS,
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
        raise AssertionError('S125 UQQ700 candidate scan failed')


if __name__ == '__main__':
    main()
