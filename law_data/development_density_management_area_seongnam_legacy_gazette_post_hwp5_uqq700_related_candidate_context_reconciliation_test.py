# -*- coding: utf-8 -*-
"""S126: reconcile S125 RELATED_CANDIDATE rows using wider offline context.

This stage is intentionally limited to the three S125 related-candidate rows. It reads the fixed S124
text corpus and S125 candidate output, extracts wider contexts around every '개발밀도' occurrence,
and classifies only whether the lexical hit is contextual general development-density language or
still unresolved for UQQ700. It does not create legal TRUE/FALSE, authorize negative evidence, or
search new source families.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pdf_primary_bounded_extraction_corpus.json'
SCAN = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_candidate_scan.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_related_candidate_context_reconciliation.json'

EXPECTED_PST = {'363477', '367408', '371820'}
RELATED = re.compile(r'개발\s*밀도')
TARGET = re.compile(r'개발\s*밀도\s*관리\s*구역')
CODE = re.compile(r'UQQ\s*700', re.I)
CONTEXT_RADIUS = 1200

GENERAL_CONTEXT_TERMS = [
    '노후계획도시', '특별정비예정구역', '특별정비계획', '기준용적률', '정비용적률',
    '공공기여', '계획인구', '건축물의 밀도계획', '분당신도시', '정비사업'
]
UQQ700_CONTEXT_TERMS = [
    '개발밀도관리구역', '국토의 계획 및 이용에 관한 법률 제66조', '국토계획법 제66조',
    '기반시설의 설치', '기반시설 용량', '개발밀도관리구역의 지정'
]


def compact(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def wider_context(text, start, end):
    lo = max(0, start - CONTEXT_RADIUS)
    hi = min(len(text), end + CONTEXT_RADIUS)
    return compact(text[lo:hi])


def classify(text, contexts):
    if TARGET.search(text) or CODE.search(text):
        return 'UQQ700_DIRECT_SIGNAL_PRESENT'
    uqq_signals = sorted({term for term in UQQ700_CONTEXT_TERMS if term in text})
    general_signals = sorted({term for term in GENERAL_CONTEXT_TERMS if term in text})
    if uqq_signals:
        return 'UQQ700_CONTEXT_REVIEW_REQUIRED'
    if general_signals and all(any(term in c for term in general_signals) for c in contexts):
        return 'CONTEXTUAL_NON_UQQ700'
    return 'CONTEXT_REVIEW_REQUIRED'


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 UQQ700 RELATED CANDIDATE CONTEXT RECONCILIATION - S126')
    print('=' * 60)
    print('Network: DISABLED')
    print('Negative evidence: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    corpus = json.loads(CORPUS.read_text(encoding='utf-8'))
    scan = json.loads(SCAN.read_text(encoding='utf-8'))
    candidates = scan.get('candidates') or []
    related = [c for c in candidates if c.get('status') == 'RELATED_CANDIDATE']
    pst_set = {str(c.get('pstSn')) for c in related}
    if pst_set != EXPECTED_PST:
        raise AssertionError(f'S125 related pst mismatch: {pst_set}')
    if scan.get('summary', {}).get('direct_candidate_row_count') != 0:
        raise AssertionError('direct candidate present; S126 is not authorized')

    by_pst = {str(r.get('pstSn')): r for r in (corpus.get('records') or [])}
    records = []
    contextual_non = 0
    unresolved = 0

    for c in sorted(related, key=lambda x: int(x.get('gazette_number') or 0)):
        pst = str(c.get('pstSn'))
        rec = by_pst.get(pst)
        if not rec:
            raise AssertionError(f'missing corpus row {pst}')
        text = str(rec.get('extracted_text') or '')
        hits = list(RELATED.finditer(text))
        contexts = [wider_context(text, m.start(), m.end()) for m in hits]
        state = classify(text, contexts)
        general_signals = sorted({term for term in GENERAL_CONTEXT_TERMS if term in text})
        uqq_signals = sorted({term for term in UQQ700_CONTEXT_TERMS if term in text})
        if state == 'CONTEXTUAL_NON_UQQ700':
            contextual_non += 1
        else:
            unresolved += 1
        item = {
            'pstSn': pst,
            'gazette_number': c.get('gazette_number'),
            'date': c.get('date'),
            'filename': c.get('filename'),
            'related_occurrence_count': len(hits),
            'general_context_signals': general_signals,
            'uqq700_context_signals': uqq_signals,
            'reconciliation_state': state,
            'contexts': contexts,
        }
        records.append(item)
        print('\nGAZETTE:', item['gazette_number'], '| pstSn:', pst, '| STATE:', state)
        print('GENERAL_SIGNALS:', general_signals)
        print('UQQ700_SIGNALS:', uqq_signals)
        for i, ctx in enumerate(contexts, 1):
            print('CONTEXT', i, ':', ctx)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S126',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'summary': {
            'input_related_candidate_count': len(related),
            'contextual_non_uqq700_count': contextual_non,
            'context_review_required_count': unresolved,
            'semantic_state': 'POST_HWP5_UQQ700_RELATED_CANDIDATE_CONTEXT_RECONCILED',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'records': records,
        'network_executed': False,
        'candidate_promotion_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'related candidate count exact': len(related) == 3,
        'related pst identities exact': pst_set == EXPECTED_PST,
        'no direct candidates in S125': scan.get('summary', {}).get('direct_candidate_row_count') == 0,
        'all related rows accounted': len(records) == 3,
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
        raise AssertionError('S126 related candidate context reconciliation failed')


if __name__ == '__main__':
    main()
