# -*- coding: utf-8 -*-
"""S140: offline terminal reconciliation for the current-snapshot PRE-HWP5 partition.

Inputs:
- S134-R1: 48 PRE rows, one HWP attachment each.
- S135: 47 HWP3 + 1 extractable HWP5.
- S138: all 47 HWP3 have no alternative representation on the current official surface.
- S139: Gazette 525 HWP5 has no UQQ700 direct/related candidate term.

This stage performs no network access and does not infer legal absence from technical non-searchability or
from a clean lexical scan. It only accounts the partition and preserves UQQ700=UNKNOWN.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'
S134=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_attachment_format_inventory.json'
S135=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp_extraction_qualification.json'
S138=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_hwp3_alternative_representation_probe.json'
S139=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_gazette525_uqq700_candidate_scan.json'
OUT=OUT_DIR/'development_density_management_area_seongnam_legacy_gazette_pre_hwp5_terminal_reconciliation.json'
EXPECTED=48
HWP3_EXPECTED=47
HWP5_EXPECTED=1
HWP5_PST='28674'


def load(path):
    if not path.exists(): raise AssertionError(f'missing input: {path}')
    return json.loads(path.read_text(encoding='utf-8'))

def norm(v): return str(v or '').strip()

def main():
    print('='*60)
    print('SEONGNAM LEGACY GAZETTE PRE-HWP5 TERMINAL RECONCILIATION - S140')
    print('='*60)
    print('Network: DISABLED')
    print('HWP3 heuristic parsing: DISABLED')
    print('OCR/decryption: DISABLED')
    print('Negative evidence: DISABLED')
    print('Legal absence inference: DISABLED')
    print('SITE/runtime promotion: DISABLED')

    a=load(S134); b=load(S135); c=load(S138); d=load(S139)
    arows=a.get('results') or []; brows=b.get('results') or []; crows=c.get('results') or []
    if len(arows)!=EXPECTED: raise AssertionError(f'S134 row count {len(arows)}')
    if len(brows)!=EXPECTED: raise AssertionError(f'S135 row count {len(brows)}')
    if len(crows)!=HWP3_EXPECTED: raise AssertionError(f'S138 HWP3 row count {len(crows)}')

    a_ids={norm(r.get('pstSn')) for r in arows}; b_ids={norm(r.get('pstSn')) for r in brows}; c_ids={norm(r.get('pstSn')) for r in crows}
    if len(a_ids)!=EXPECTED or a_ids!=b_ids: raise AssertionError('S134/S135 PRE identity mismatch')

    hwp3=[r for r in brows if r.get('signature')=='HWP3']
    hwp5=[r for r in brows if r.get('signature')=='HWP5']
    if len(hwp3)!=HWP3_EXPECTED or len(hwp5)!=HWP5_EXPECTED: raise AssertionError('S135 signature partition mismatch')
    hwp3_ids={norm(r.get('pstSn')) for r in hwp3}
    if c_ids!=hwp3_ids: raise AssertionError('S138 identities do not exactly match S135 HWP3 identities')
    if any(r.get('state')!='NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE' for r in crows):
        raise AssertionError('S138 contains non-terminal HWP3 alternative-representation state')

    scan=d.get('scan') or {}; summary139=d.get('summary') or {}
    if norm((d.get('row') or {}).get('pstSn'))!=HWP5_PST: raise AssertionError('S139 target pst mismatch')
    if scan.get('status')!='NO_CANDIDATE_TERM_IN_EXTRACTED_TEXT': raise AssertionError(f"S139 candidate state requires review: {scan.get('status')}")
    if summary139.get('direct_candidate_count')!=0 or summary139.get('related_candidate_count')!=0: raise AssertionError('S139 candidate count nonzero')

    searchable_clean=1
    technical_nonsearchable=HWP3_EXPECTED
    accounted=searchable_clean+technical_nonsearchable
    out={
        'step':'STEP 17-21-C-16-8-T-36-S140',
        'target_name':'개발밀도관리구역','standard_code':'UQQ700',
        'summary':{
            'pre_hwp5_partition_row_count':EXPECTED,
            'hwp5_text_searchable_clean_count':searchable_clean,
            'hwp3_current_surface_technical_nonsearchable_count':technical_nonsearchable,
            'total_accounted_row_count':accounted,
            'direct_candidate_remaining_count':0,
            'context_review_remaining_count':0,
            'technical_unknown_remaining_count':technical_nonsearchable,
            'technical_unknown_reason':'HWP3_UNQUALIFIED_FOR_TEXT_EXTRACTION_AND_NO_ALTERNATIVE_REPRESENTATION_IN_CURRENT_OFFICIAL_SURFACE',
            'semantic_state':'PRE_HWP5_PARTITION_TERMINALLY_RECONCILED_WITH_47_HWP3_TECHNICAL_UNKNOWNS',
            'negative_evidence_allowed':False,
            'uqq700_final_resolution':'UNKNOWN'
        },
        'searchable_clean_pstSn':[HWP5_PST],
        'technical_unknown_pstSn':sorted(hwp3_ids,key=int),
        'network_executed':False,
        'hwp3_heuristic_parsing_executed':False,
        'ocr_executed':False,
        'decryption_executed':False,
        'negative_evidence_allowed':False,
        'legal_absence_inference_allowed':False,
        'site_positive_allowed':False,
        'site_negative_allowed':False,
        'runtime_registration_allowed':False,
        'next_source_family':'OTHER_HISTORICAL_OFFICIAL_SOURCE_FAMILY_OR_NOTICE_NUMBER_REVERSE_LOOKUP'
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')

    vals={
        'PRE partition exact':out['summary']['pre_hwp5_partition_row_count']==EXPECTED,
        'HWP5 searchable clean exact':out['summary']['hwp5_text_searchable_clean_count']==1,
        'HWP3 technical unknown exact':out['summary']['hwp3_current_surface_technical_nonsearchable_count']==47,
        'accounting exact':out['summary']['total_accounted_row_count']==EXPECTED,
        'direct candidate remaining zero':out['summary']['direct_candidate_remaining_count']==0,
        'context review remaining zero':out['summary']['context_review_remaining_count']==0,
        'network disabled':not out['network_executed'],
        'HWP3 heuristic parsing disabled':not out['hwp3_heuristic_parsing_executed'],
        'OCR disabled':not out['ocr_executed'],
        'decryption disabled':not out['decryption_executed'],
        'negative evidence disabled':not out['negative_evidence_allowed'],
        'legal absence inference disabled':not out['legal_absence_inference_allowed'],
        'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),
        'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN',
        'output written':OUT.exists() and OUT.stat().st_size>0,
    }
    print('\nSUMMARY')
    for k,v in out['summary'].items(): print(f'{k}: {v}')
    print('searchable_clean_pstSn:',out['searchable_clean_pstSn'])
    print('technical_unknown_pstSn:',out['technical_unknown_pstSn'])
    print('next_source_family:',out['next_source_family'])
    print('Output:',OUT)
    print('\nVALIDATION')
    for k,v in vals.items(): print(f'{k}: {v}')
    print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S140 PRE-HWP5 terminal reconciliation failed')

if __name__=='__main__': main()
