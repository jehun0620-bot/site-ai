# -*- coding: utf-8 -*-
"""S70: quarantine Gazette 1867 (pstSn 343270) as cluster-consistent technical attachment unresolved."""
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
STATE=OUTDIR/'development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_1867_cluster_quarantine_reconciliation.json'
TARGET='343270'
REASON='OFFICIAL_DETAIL_PRESENT_AND_ATTACHMENT_METADATA_EMPTY_WITH_CLUSTER_CONSISTENT_DYNAMIC_ATTACHMENT_PATTERN_NO_CONCRETE_FILE_REFERENCE'


def norm(v): return str(v or '').strip()

def main():
    print('='*60); print('GAZETTE 1867 CLUSTER QUARANTINE RECONCILIATION - S70'); print('='*60)
    print('Network: DISABLED'); print('Negative evidence: DISABLED')
    if not STATE.exists(): raise FileNotFoundError(STATE)
    state=json.loads(STATE.read_text(encoding='utf-8'))
    rows=state.get('results') or []
    by={norm(r.get('pstSn')):r for r in rows if norm(r.get('pstSn'))}
    if TARGET not in by: raise AssertionError('missing target 343270')
    row=by[TARGET]
    if row.get('status')!='EXTRACTION_OR_REQUEST_UNKNOWN':
        raise AssertionError(f'unexpected prior status: {row.get("status")}')
    row.update({'status':'TECHNICAL_UNRESOLVED_QUARANTINED','quarantine_reason':REASON,'legal_negative_evidence':False,'runtime_registration_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'final_positive_promotion_allowed':False})

    quarantined=[r for r in rows if r.get('status')=='TECHNICAL_UNRESOLVED_QUARANTINED']
    candidates=[r for r in rows if r.get('status') in {'DIRECT_CANDIDATE','RELATED_CANDIDATE'}]
    unknown=[r for r in rows if r.get('status')=='EXTRACTION_OR_REQUEST_UNKNOWN']
    processed=[norm(r.get('pstSn')) for r in rows if norm(r.get('pstSn')) and r.get('status') not in {'EXTRACTION_OR_REQUEST_UNKNOWN','TECHNICAL_UNRESOLVED_QUARANTINED'}]
    state['processed_pstSn']=list(dict.fromkeys(processed)); state['processed_count']=len(state['processed_pstSn'])
    state['quarantined_pstSn']=[norm(r.get('pstSn')) for r in quarantined]; state['quarantined_count']=len(quarantined)
    state['candidate_count']=len(candidates); state['unresolved_count']=len(quarantined)+len(unknown)
    state['remaining_count']=int(state.get('era_row_count') or 0)-state['processed_count']-state['quarantined_count']
    state['negative_evidence_allowed']=False
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')

    output={'step':'STEP 17-21-C-16-8-T-34-S70','target_pstSn':TARGET,'status_after':row['status'],'quarantine_reason':REASON,'processed_count_after':state['processed_count'],'quarantined_count_after':state['quarantined_count'],'remaining_count_after':state['remaining_count'],'candidate_count_after':state['candidate_count'],'unresolved_count_after':state['unresolved_count'],'network_request_count':0,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'343270 quarantined':row.get('status')=='TECHNICAL_UNRESOLVED_QUARANTINED','no non-quarantine unknown remains':len(unknown)==0,'candidate count zero':state['candidate_count']==0,'unresolved equals quarantine count':state['unresolved_count']==state['quarantined_count'],'state arithmetic valid':state['processed_count']+state['quarantined_count']+state['remaining_count']==state['era_row_count'],'network disabled':output['network_request_count']==0,'negative evidence disabled':not output['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(output[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('Processed:',state['processed_count']); print('Quarantined:',state['quarantined_count'],state['quarantined_pstSn']); print('Remaining:',state['remaining_count']); print('Candidates:',state['candidate_count']); print('Unresolved:',state['unresolved_count']); print('Output:',OUT)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S70 reconciliation failed')

if __name__=='__main__': main()
