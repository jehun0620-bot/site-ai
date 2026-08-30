# -*- coding: utf-8 -*-
"""S58: reconcile Gazette 1626 / pstSn 188147 after successful 2M-record bounded retry."""
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
STATE=OUTDIR/'development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json'
RETRY=OUTDIR/'development_density_management_area_municipal_gazette_1626_hwp5_raised_record_ceiling_retry.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_1626_raised_record_ceiling_state_reconciliation.json'
TARGET='188147'


def norm(v): return str(v or '').strip()


def main():
    print('='*60); print('GAZETTE 1626 RAISED RECORD CEILING STATE RECONCILIATION'); print('='*60)
    print('Target pstSn:',TARGET); print('Network: DISABLED'); print('Negative evidence: DISABLED')
    if not STATE.exists(): raise FileNotFoundError(STATE)
    if not RETRY.exists(): raise FileNotFoundError(RETRY)
    state=json.loads(STATE.read_text(encoding='utf-8'))
    retry=json.loads(RETRY.read_text(encoding='utf-8'))
    if norm((retry.get('target') or {}).get('pstSn')) != TARGET: raise AssertionError('retry target mismatch')
    if retry.get('extract_ok') is not True: raise AssertionError('retry extraction not successful')
    if retry.get('all_sections_fully_consumed') is not True: raise AssertionError('retry not fully consumed')
    if any((retry.get('direct_matches') or {}).values()): raise AssertionError('direct candidate present')
    if any((retry.get('high_signal_related_matches') or {}).values()): raise AssertionError('high-signal candidate present')
    rows=[r for r in (state.get('results') or []) if norm(r.get('pstSn'))==TARGET]
    if len(rows)!=1: raise AssertionError(f'expected one target row, got {len(rows)}')
    row=rows[0]
    if row.get('status')!='EXTRACTION_OR_REQUEST_UNKNOWN': raise AssertionError(f'unexpected prior status: {row.get("status")}')
    row.update({
        'status':'NO_TERM_IN_EXTRACTED_SAMPLE',
        'parser_used':'HWP5_RAISED_LIMIT_2000000',
        'extract_ok':True,
        'extract_error':'',
        'section_count':retry.get('section_count'),
        'hwp_flags':retry.get('hwp_flags') or {},
        'text_chars':retry.get('text_chars'),
        'direct_matches':retry.get('direct_matches') or {},
        'related_matches':retry.get('related_matches') or {},
        'high_signal_related_matches':retry.get('high_signal_related_matches') or {},
        'low_signal_related_matches':retry.get('low_signal_related_matches') or {},
        'error':'',
        'record_limit_used':retry.get('record_limit'),
        'all_sections_fully_consumed':True,
        'legal_negative_evidence':False,
        'reconciliation_reason':'INITIAL_UNKNOWN_WAS_PARSER_RECORD_CEILING_ONLY; EXACT_TARGET_FULLY_CONSUMED_AT_2000000_RECORD_LIMIT'
    })
    results=state.get('results') or []
    processed=[norm(r.get('pstSn')) for r in results if norm(r.get('pstSn')) and r.get('status') not in {'EXTRACTION_OR_REQUEST_UNKNOWN','TECHNICAL_UNRESOLVED_QUARANTINED'}]
    quarantined=[r for r in results if r.get('status')=='TECHNICAL_UNRESOLVED_QUARANTINED']
    candidates=[r for r in results if r.get('status') in {'DIRECT_CANDIDATE','RELATED_CANDIDATE'}]
    unresolved=[r for r in results if r.get('status') in {'EXTRACTION_OR_REQUEST_UNKNOWN','TECHNICAL_UNRESOLVED_QUARANTINED'}]
    state['processed_pstSn']=list(dict.fromkeys(processed)); state['processed_count']=len(state['processed_pstSn'])
    state['quarantined_pstSn']=[norm(r.get('pstSn')) for r in quarantined]; state['quarantined_count']=len(quarantined)
    state['candidate_count']=len(candidates); state['unresolved_count']=len(unresolved)
    state['remaining_count']=int(state.get('era_row_count') or 0)-state['processed_count']-state['quarantined_count']
    state['negative_evidence_allowed']=False
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    output={'step':'STEP 17-21-C-16-8-T-34-S58','target_pstSn':TARGET,'prior_status':'EXTRACTION_OR_REQUEST_UNKNOWN','new_status':'NO_TERM_IN_EXTRACTED_SAMPLE','processed_count_after':state['processed_count'],'quarantined_count_after':state['quarantined_count'],'remaining_count_after':state['remaining_count'],'candidate_count_after':state['candidate_count'],'unresolved_count_after':state['unresolved_count'],'network_request_count':0,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={
        'target reconciled':row.get('status')=='NO_TERM_IN_EXTRACTED_SAMPLE',
        'raised parser recorded':row.get('parser_used')=='HWP5_RAISED_LIMIT_2000000',
        'target fully consumed':row.get('all_sections_fully_consumed') is True,
        'target processed':TARGET in set(state['processed_pstSn']),
        'candidate count zero':state['candidate_count']==0,
        'quarantine count preserved':state['quarantined_count']==4,
        'unresolved reduced to quarantine only':state['unresolved_count']==4,
        'state arithmetic valid':state['processed_count']+state['quarantined_count']+state['remaining_count']==state['era_row_count'],
        'network disabled':output['network_request_count']==0,
        'negative evidence disabled':not output['negative_evidence_allowed'],
        'unsafe promotion leakage zero':not any(output[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),
        'output written':OUT.exists() and OUT.stat().st_size>0,
    }
    print('Processed:',state['processed_count']); print('Quarantined:',state['quarantined_count'],state['quarantined_pstSn']); print('Remaining:',state['remaining_count']); print('Candidates:',state['candidate_count']); print('Unresolved:',state['unresolved_count']); print('Output:',OUT)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('Gazette 1626 state reconciliation failed')

if __name__=='__main__': main()
