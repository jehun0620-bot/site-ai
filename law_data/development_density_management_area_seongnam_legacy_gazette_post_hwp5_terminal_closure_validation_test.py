# -*- coding: utf-8 -*-
"""S133: terminal closure validation for the current-snapshot POST-HWP5 partition.

This offline stage freezes the S131/S132 interpretation:
- 219 current-snapshot POST-HWP5 rows are fully accounted.
- 215 rows are text-searchable and candidate-reconciled (213 PDF primary + 1 pairing PDF + 1 HWP).
- 4 encrypted HWPX-only rows remain explicit technical unknowns.
- S132 found no alternative representation on the current official detail/metadata surface.

Closure is operational only. It is not legal negative evidence and does not establish UQQ700 absence.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
S131 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_terminal_reconciliation.json'
S132 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_encrypted_hwpx_alternative_representation_probe.json'
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_terminal_closure_validation.json'

EXPECTED_TOTAL = 219
EXPECTED_SEARCHABLE = 215
EXPECTED_UNKNOWN = {'363790', '370638', '372500', '374744'}


def load(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 TERMINAL CLOSURE VALIDATION - S133')
    print('=' * 60)
    print('Network: DISABLED')
    print('Encrypted HWPX decryption: DISABLED')
    print('OCR: DISABLED')
    print('Negative evidence: DISABLED')
    print('Legal absence inference: DISABLED')
    print('Final legal resolution: UNKNOWN')

    s131 = load(S131)
    s132 = load(S132)
    a = s131.get('summary') or {}
    b = s132.get('summary') or {}

    unknown_131 = set(map(str, s131.get('technical_unknown_pstSn') or []))
    states_132 = s132.get('results') or []
    unknown_132 = {str(r.get('pstSn')) for r in states_132}
    state_map = {str(r.get('pstSn')): r.get('state') for r in states_132}

    searchable = (
        int(a.get('pdf_primary_scanned_row_count') or 0)
        + int(a.get('pairing_review_pdf_scanned_clean_count') or 0)
        + int(a.get('hwp_exception_recovered_scanned_clean_count') or 0)
    )
    technical_unknown = int(a.get('technical_unknown_remaining_count') or 0)
    accounted = searchable + technical_unknown

    output = {
        'step': 'STEP 17-21-C-16-8-T-35-S133',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'summary': {
            'post_hwp5_partition_row_count': EXPECTED_TOTAL,
            'text_searchable_and_reconciled_row_count': searchable,
            'technical_unknown_row_count': technical_unknown,
            'total_accounted_row_count': accounted,
            'direct_candidate_remaining_count': int(a.get('direct_candidate_remaining_count') or 0),
            'context_review_remaining_count': int(a.get('context_review_remaining_count') or 0),
            'alternative_representation_found_count': int(b.get('alternative_representation_found_count') or 0),
            'detail_html_target_candidate_count': int(b.get('detail_html_target_candidate_count') or 0),
            'current_official_surface_no_alternative_count': int(b.get('no_alternative_current_surface_count') or 0),
            'technical_probe_unknown_count': int(b.get('technical_probe_unknown_count') or 0),
            'semantic_state': 'POST_HWP5_CURRENT_SNAPSHOT_TERMINALLY_CLOSED_WITH_FOUR_ENCRYPTED_HWPX_TECHNICAL_UNKNOWNS',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'technical_unknown_pstSn': sorted(unknown_131),
        'technical_unknown_states': state_map,
        'closure_policy': {
            'rerun_bulk_pdf_primary_scan_allowed': False,
            'encrypted_hwpx_password_guessing_allowed': False,
            'encrypted_hwpx_decryption_attempt_allowed': False,
            'ocr_allowed': False,
            'current_surface_absence_as_legal_negative_allowed': False,
            'historical_1338_identity_reconstruction_allowed': False,
            'immutable_manifest_rewrite_allowed': False,
            'next_source_family': 'PRE_HWP5_GAZETTE_ROWS_OR_OTHER_HISTORICAL_OFFICIAL_SOURCE_FAMILY',
        },
        'network_executed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'S131 terminal reconciliation state': a.get('semantic_state') == 'POST_HWP5_PARTITION_TERMINALLY_RECONCILED_WITH_TECHNICAL_UNKNOWNS',
        '219 rows accounted': accounted == EXPECTED_TOTAL,
        '215 rows text-searchable/reconciled': searchable == EXPECTED_SEARCHABLE,
        'technical unknown count four': technical_unknown == 4,
        'S131 unknown identities exact': unknown_131 == EXPECTED_UNKNOWN,
        'S132 probe identities exact': unknown_132 == EXPECTED_UNKNOWN,
        'S132 all four no alternative current surface': all(state_map.get(p) == 'NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE' for p in EXPECTED_UNKNOWN),
        'alternative representation found zero': output['summary']['alternative_representation_found_count'] == 0,
        'detail HTML target candidate zero': output['summary']['detail_html_target_candidate_count'] == 0,
        'technical probe unknown zero': output['summary']['technical_probe_unknown_count'] == 0,
        'direct candidate remaining zero': output['summary']['direct_candidate_remaining_count'] == 0,
        'context review remaining zero': output['summary']['context_review_remaining_count'] == 0,
        'bulk rerun disabled': not output['closure_policy']['rerun_bulk_pdf_primary_scan_allowed'],
        'password guessing disabled': not output['closure_policy']['encrypted_hwpx_password_guessing_allowed'],
        'decryption attempt disabled': not output['closure_policy']['encrypted_hwpx_decryption_attempt_allowed'],
        'OCR disabled': not output['closure_policy']['ocr_allowed'],
        'legal negative from current surface disabled': not output['closure_policy']['current_surface_absence_as_legal_negative_allowed'],
        'historical 1338 reconstruction disabled': not output['closure_policy']['historical_1338_identity_reconstruction_allowed'],
        'immutable manifest rewrite disabled': not output['closure_policy']['immutable_manifest_rewrite_allowed'],
        'network disabled': not output['network_executed'],
        'unsafe promotion leakage zero': not any(output[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': output['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('SUMMARY')
    for k, v in output['summary'].items():
        print(f'{k}: {v}')
    print('technical_unknown_pstSn:', output['technical_unknown_pstSn'])
    print('next_source_family:', output['closure_policy']['next_source_family'])
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S133 post-HWP5 terminal closure validation failed')


if __name__ == '__main__':
    main()
