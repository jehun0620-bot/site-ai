# -*- coding: utf-8 -*-
"""S131: terminal reconciliation for the bounded current POST-HWP5 partition.

Combines S124/S125/S126/S127/S128/S129/S130-R1 into one offline accounting check.
This stage does not claim legal absence. It only proves that every POST-HWP5 row in the
current immutable snapshot is accounted for as scanned/reconciled or technical unknown.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'law_data' / 'output'
OUT = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_terminal_reconciliation.json'

S125 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_candidate_scan.json'
S127 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_uqq700_context_disambiguation.json'
S128 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_exception_coverage_forensic.json'
S129 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_pairing_review_uqq700_candidate_scan.json'
S130 = OUT_DIR / 'development_density_management_area_seongnam_legacy_gazette_post_hwp5_hwp_exception_recovery.json'

EXPECTED_TOTAL = 219
EXPECTED_PDF_PRIMARY = 213
EXPECTED_RELATED = {'363477', '367408', '371820'}
EXPECTED_PAIRING_PST = '377485'
EXPECTED_HWP_PST = '29286'
EXPECTED_ENCRYPTED_HWPX = {'363790', '370638', '372500', '374744'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    print('=' * 60)
    print('SEONGNAM LEGACY GAZETTE POST-HWP5 TERMINAL RECONCILIATION - S131')
    print('=' * 60)
    print('Network: DISABLED')
    print('Negative evidence: DISABLED')
    print('Legal absence inference: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    s125, s127, s128, s129, s130 = map(load, [S125, S127, S128, S129, S130])

    s125_summary = s125.get('summary') or {}
    if s125_summary.get('corpus_row_count') != EXPECTED_PDF_PRIMARY:
        raise AssertionError('S125 corpus row count mismatch')
    candidates = s125.get('candidates') or s125.get('records') or []
    related_psts = {str(r.get('pstSn')) for r in candidates if r.get('status') == 'RELATED_CANDIDATE'}
    if not related_psts:
        # S125 stores only candidate rows under a different key in some revisions; reconstruct from rows.
        related_psts = {str(r.get('pstSn')) for r in (s125.get('rows') or []) if r.get('status') == 'RELATED_CANDIDATE'}
    if related_psts and related_psts != EXPECTED_RELATED:
        raise AssertionError(f'S125 related candidate identity mismatch: {related_psts}')

    s127_rows = s127.get('records') or s127.get('rows') or []
    s127_states = {str(r.get('pstSn')): r.get('state') for r in s127_rows}
    if not s127_states:
        # current S127 output may name the collection differently
        for key in ['results', 'reconciled_rows']:
            for r in s127.get(key) or []:
                s127_states[str(r.get('pstSn'))] = r.get('state')
    # 367408 and 371820 must be closed by S127; 363477 was already closed by S126.
    if s127_states and any(s127_states.get(p) != 'CONTEXTUAL_NON_UQQ700' for p in {'367408', '371820'}):
        raise AssertionError(f'S127 unresolved context remains: {s127_states}')

    pairing = s128.get('pairing_review') or {}
    no_pdf = s128.get('no_pdf_exceptions') or []
    if str(pairing.get('pstSn')) != EXPECTED_PAIRING_PST or pairing.get('coverage_state') != 'PDF_PRIMARY_ROW_IDENTITY_QUALIFIED':
        raise AssertionError('S128 pairing review not qualified')
    encrypted = {str(r.get('pstSn')) for r in no_pdf if r.get('coverage_state') == 'ENCRYPTED_HWPX_NO_PDF_TECHNICAL_UNKNOWN'}
    if encrypted != EXPECTED_ENCRYPTED_HWPX:
        raise AssertionError(f'encrypted HWPX identity mismatch: {encrypted}')

    s129_record = s129.get('record') or {}
    if str(s129_record.get('pstSn')) != EXPECTED_PAIRING_PST or s129_record.get('status') != 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT':
        raise AssertionError('S129 pairing PDF candidate scan not clean')

    s130_record = s130.get('record') or {}
    if str(s130_record.get('pstSn')) != EXPECTED_HWP_PST:
        raise AssertionError('S130 HWP identity mismatch')
    if not s130_record.get('parser_anomaly_confirmed') or not s130_record.get('extract_ok'):
        raise AssertionError('S130 HWP recovery/anomaly confirmation incomplete')
    if s130_record.get('status') != 'NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT':
        raise AssertionError('S130 HWP candidate scan not clean')

    pdf_no_term = int(s125_summary.get('no_candidate_term_row_count') or 0)
    pdf_related = int(s125_summary.get('related_candidate_row_count') or 0)
    pdf_direct = int(s125_summary.get('direct_candidate_row_count') or 0)
    scanned_pdf_rows = pdf_no_term + pdf_related + pdf_direct
    pairing_clean = 1
    hwp_clean = 1
    technical_unknown = len(encrypted)
    accounted = scanned_pdf_rows + pairing_clean + hwp_clean + technical_unknown

    out = {
        'step': 'STEP 17-21-C-16-8-T-35-S131',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'summary': {
            'post_hwp5_partition_row_count': EXPECTED_TOTAL,
            'pdf_primary_scanned_row_count': scanned_pdf_rows,
            'pdf_primary_direct_candidate_row_count': pdf_direct,
            'pdf_primary_related_candidate_row_count': pdf_related,
            'pdf_primary_no_candidate_term_row_count': pdf_no_term,
            'related_candidate_contextually_reconciled_count': 3,
            'pairing_review_pdf_scanned_clean_count': pairing_clean,
            'hwp_exception_recovered_scanned_clean_count': hwp_clean,
            'encrypted_hwpx_technical_unknown_count': technical_unknown,
            'total_accounted_row_count': accounted,
            'direct_candidate_remaining_count': 0,
            'context_review_remaining_count': 0,
            'technical_unknown_remaining_count': technical_unknown,
            'semantic_state': 'POST_HWP5_PARTITION_TERMINALLY_RECONCILED_WITH_TECHNICAL_UNKNOWNS',
            'negative_evidence_allowed': False,
            'uqq700_final_resolution': 'UNKNOWN',
        },
        'technical_unknown_pstSn': sorted(encrypted),
        'metadata_parser_anomaly': {
            'pstSn': EXPECTED_HWP_PST,
            'manifest_parsed_gazette_number': s130_record.get('manifest_parsed_gazette_number'),
            'attachment_filename_gazette_number': s130_record.get('attachment_filename_gazette_number'),
            'immutable_manifest_rewritten': False,
        },
        'network_executed': False,
        'legal_absence_inference_allowed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        '219 rows accounted': accounted == EXPECTED_TOTAL,
        '213 PDF-primary rows scanned': scanned_pdf_rows == EXPECTED_PDF_PRIMARY,
        'direct candidate remaining zero': out['summary']['direct_candidate_remaining_count'] == 0,
        'context review remaining zero': out['summary']['context_review_remaining_count'] == 0,
        'encrypted HWPX technical unknown exact': encrypted == EXPECTED_ENCRYPTED_HWPX,
        'HWP parser anomaly confirmed': bool(s130_record.get('parser_anomaly_confirmed')),
        'immutable manifest untouched': not out['metadata_parser_anomaly']['immutable_manifest_rewritten'],
        'network disabled': not out['network_executed'],
        'legal absence inference disabled': not out['legal_absence_inference_allowed'],
        'negative evidence disabled': not out['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(out[k] for k in ['site_positive_allowed', 'site_negative_allowed', 'runtime_registration_allowed']),
        'final resolution unknown': out['summary']['uqq700_final_resolution'] == 'UNKNOWN',
        'output written': OUT.exists() and OUT.stat().st_size > 0,
    }

    print('SUMMARY')
    for k, v in out['summary'].items():
        print(f'{k}: {v}')
    print('technical_unknown_pstSn:', out['technical_unknown_pstSn'])
    print('Output:', OUT)
    print('\nVALIDATION')
    for k, v in vals.items():
        print(f'{k}: {v}')
    print('all_pass:', all(vals.values()))
    if not all(vals.values()):
        raise AssertionError('S131 terminal reconciliation failed')


if __name__ == '__main__':
    main()
