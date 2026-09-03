# -*- coding: utf-8 -*-
"""S127: disambiguate the two S126 review-required rows using legal-context structure.

S126 left pstSn 367408 and 371820 unresolved because generic phrases such as '기반시설의 설치' and
'기반시설 용량' overlap lexically with UQQ700 concepts. This offline stage inspects those exact rows
only and distinguishes (a) explicit UQQ700 designation/management-area language from (b) ordinary
no후계획도시 planning language about infrastructure, density, and FAR. It does not assert legal
absence, promote SITE state, or authorize negative evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pdf_primary_bounded_extraction_corpus.json'
S126 = BASE / 'law_data' / 'output' / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_related_candidate_context_reconciliation.json'
OUT_DIR = BASE / 'law_data' / 'output'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_context_disambiguation.json'

EXPECTED_PST = {'367408', '371820'}
TARGET_PATTERNS = [
    re.compile(r'개발\s*밀도\s*관리\s*구역'),
    re.compile(r'UQQ\s*700', re.I),
    re.compile(r'개발\s*밀도\s*관리\s*구역\s*(지정|변경|해제)'),
]
UQQ_DESIGNATION_TERMS = [
    '개발밀도관리구역 지정', '개발밀도관리구역의 지정', '개발밀도관리구역 변경',
    '개발밀도관리구역 해제', '개발밀도관리구역 결정', '개발밀도관리구역 지형도면'
]
PLANNING_FRAME_TERMS = [
    '노후계획도시 정비 및 지원에 관한 특별법', '노후계획도시정비사업', '특별정비계획',
    '특별정비예정구역', '기준용적률', '정비용적률', '공공기여', '분당신도시',
    '노후계획도시 계획인구', '노후계획도시 정비기본계획'
]
GENERIC_INFRA_TERMS = ['기반시설의 설치', '기반시설 용량', '기반시설 설치계획', '기반시설 확충']


def compact(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def classify(text):
    direct = [p.pattern for p in TARGET_PATTERNS if p.search(text)]
    designation = sorted({t for t in UQQ_DESIGNATION_TERMS if t in text})
    planning = sorted({t for t in PLANNING_FRAME_TERMS if t in text})
    generic = sorted({t for t in GENERIC_INFRA_TERMS if t in text})
    if direct or designation:
        state = 'UQQ700_DIRECT_OR_DESIGNATION_SIGNAL_PRESENT'
    elif planning and generic:
        state = 'CONTEXTUAL_NON_UQQ700'
    elif planning:
        state = 'CONTEXTUAL_NON_UQQ700'
    else:
        state = 'CONTEXT_REVIEW_REQUIRED'
    return state, direct, designation, planning, generic


def extract_windows(text):
    needles = [re.compile(r'개발\s*밀도'), re.compile(r'기반시설\s*(?:의\s*)?(?:설치|용량|확충)')]
    spans = []
    for pat in needles:
        for m in pat.finditer(text):
            spans.append((m.start(), m.end()))
    spans.sort()
    out = []
    for start, end in spans[:12]:
        lo = max(0, start - 900)
        hi = min(len(text), end + 900)
        out.append(compact(text[lo:hi]))
    return out


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 UQQ700 CONTEXT DISAMBIGUATION - S127')
    print('=' * 60)
    print('Network: DISABLED')
    print('Negative evidence: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    corpus = json.loads(CORPUS.read_text(encoding='utf-8'))
    prev = json.loads(S126.read_text(encoding='utf-8'))
    review_rows = [r for r in (prev.get('records') or []) if r.get('reconciliation_state') != 'CONTEXTUAL_NON_UQQ700']
    pst_set = {str(r.get('pstSn')) for r in review_rows}
    if pst_set != EXPECTED_PST:
        raise AssertionError(f'S126 review set mismatch: {pst_set}')
    by_pst = {str(r.get('pstSn')): r for r in (corpus.get('records') or [])}

    records = []
    contextual_non = 0
    unresolved = 0
    direct_signal = 0

    for pst in sorted(EXPECTED_PST, key=int):
        rec = by_pst.get(pst)
        if not rec:
            raise AssertionError(f'missing S124 row {pst}')
        text = str(rec.get('extracted_text') or '')
        state, direct, designation, planning, generic = classify(text)
        if state == 'CONTEXTUAL_NON_UQQ700':
            contextual_non += 1
        elif state == 'UQQ700_DIRECT_OR_DESIGNATION_SIGNAL_PRESENT':
            direct_signal += 1
        else:
            unresolved += 1
        item = {
            'pstSn': pst,
            'gazette_number': rec.get('gazette_number'),
            'date': rec.get('date'),
            'filename': rec.get('filename'),
            'state': state,
            'direct_pattern_hits': direct,
            'designation_term_hits': designation,
            'planning_frame_hits': planning,
            'generic_infrastructure_hits': generic,
            'context_windows': extract_windows(text),
        }
        records.append(item)
        print('\nGAZETTE:', item['gazette_number'], '| pstSn:', pst, '| STATE:', state)
        print('DIRECT_PATTERN_HITS:', direct)
        print('DESIGNATION_TERM_HITS:', designation)
        print('PLANNING_FRAME_HITS:', planning)
        print('GENERIC_INFRASTRUCTURE_HITS:', generic)
        for i, ctx in enumerate(item['context_windows'][:4], 1):
            print('CONTEXT', i, ':', ctx)

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S127',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'summary': {
            'input_review_row_count': len(review_rows),
            'contextual_non_uqq700_count': contextual_non,
            'direct_or_designation_signal_count': direct_signal,
            'context_review_required_count': unresolved,
            'semantic_state': 'POST_HWP5_UQQ700_CONTEXT_DISAMBIGUATED',
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
        'review row count exact': len(review_rows) == 2,
        'review pst identities exact': pst_set == EXPECTED_PST,
        'all review rows accounted': len(records) == 2,
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
        raise AssertionError('S127 UQQ700 context disambiguation failed')


if __name__ == '__main__':
    main()
