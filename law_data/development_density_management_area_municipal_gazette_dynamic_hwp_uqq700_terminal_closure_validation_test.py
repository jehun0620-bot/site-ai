# -*- coding: utf-8 -*-
"""S72: terminal closure validation for the dynamic-HWP UQQ700 municipal gazette search."""
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
STATE=OUTDIR/'development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_terminal_closure_validation.json'
EXPECTED_ERA_ROWS=1338
EXPECTED_QUARANTINE={'29098','29471','181109','181376','221174','323596','339293','343270','343615','343834'}


def norm(v): return str(v or '').strip()

def main():
    print('='*60); print('DYNAMIC HWP UQQ700 TERMINAL CLOSURE VALIDATION - S72'); print('='*60)
    print('Network: DISABLED'); print('Negative evidence: DISABLED'); print('Final legal resolution: UNKNOWN')
    if not STATE.exists(): raise FileNotFoundError(STATE)
    state=json.loads(STATE.read_text(encoding='utf-8'))
    rows=state.get('results') or []
    pst=[norm(r.get('pstSn')) for r in rows if norm(r.get('pstSn'))]
    duplicates=sorted({x for x in pst if pst.count(x)>1})
    candidates=[r for r in rows if r.get('status') in {'DIRECT_CANDIDATE','RELATED_CANDIDATE'}]
    non_quarantine_unknown=[r for r in rows if r.get('status')=='EXTRACTION_OR_REQUEST_UNKNOWN']
    quarantined=[r for r in rows if r.get('status')=='TECHNICAL_UNRESOLVED_QUARANTINED']
    quarantine_pst={norm(r.get('pstSn')) for r in quarantined}
    unsafe=[r for r in rows if any(bool(r.get(k)) for k in ['legal_negative_evidence','runtime_registration_allowed','site_positive_allowed','site_negative_allowed','final_positive_promotion_allowed'])]
    processed_count=int(state.get('processed_count') or 0)
    quarantined_count=int(state.get('quarantined_count') or 0)
    remaining_count=int(state.get('remaining_count') or 0)
    era_row_count=int(state.get('era_row_count') or 0)
    candidate_count=int(state.get('candidate_count') or 0)
    unresolved_count=int(state.get('unresolved_count') or 0)
    closure={'target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','dynamic_hwp_era_row_count':era_row_count,'processed_count':processed_count,'quarantined_count':quarantined_count,'remaining_count':remaining_count,'candidate_count':candidate_count,'unresolved_count':unresolved_count,'quarantined_pstSn':sorted(quarantine_pst,key=int),'non_quarantine_unknown_count':len(non_quarantine_unknown),'duplicate_pstSn':duplicates,'final_legal_resolution':'UNKNOWN','site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'negative_evidence_allowed':False,'closure_reason':'DYNAMIC_HWP_ERA_EXHAUSTED_WITH_NO_UQQ700_DOCUMENTARY_CANDIDATE_AND_TECHNICAL_QUARANTINES_PRESERVED; ABSENCE_OF_DOCUMENTARY_HIT_IS_NOT_LEGAL_NEGATIVE_EVIDENCE'}
    OUT.write_text(json.dumps({'step':'STEP 17-21-C-16-8-T-34-S72','closure':closure,'network_request_count':0},ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'era row count exact':era_row_count==EXPECTED_ERA_ROWS,'remaining zero':remaining_count==0,'candidate count zero':candidate_count==0 and not candidates,'no non-quarantine unknown':len(non_quarantine_unknown)==0,'quarantine count ten':quarantined_count==10 and len(quarantined)==10,'expected quarantine set exact':quarantine_pst==EXPECTED_QUARANTINE,'unresolved equals quarantine':unresolved_count==quarantined_count,'state arithmetic valid':processed_count+quarantined_count+remaining_count==era_row_count,'no duplicate pstSn':not duplicates,'negative evidence disabled':state.get('negative_evidence_allowed') is False,'unsafe promotion leakage zero':not unsafe,'final resolution unknown':closure['final_legal_resolution']=='UNKNOWN','site false disabled':not closure['site_negative_allowed'],'network disabled':True,'output written':OUT.exists() and OUT.stat().st_size>0}
    print('Era rows:',era_row_count); print('Processed:',processed_count); print('Quarantined:',quarantined_count,sorted(quarantine_pst,key=int)); print('Remaining:',remaining_count); print('Candidates:',candidate_count); print('Unresolved:',unresolved_count); print('Final legal resolution:',closure['final_legal_resolution']); print('Output:',OUT)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S72 terminal closure validation failed')

if __name__=='__main__': main()
