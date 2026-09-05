# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent
OUT_DIR=BASE/'law_data'/'output'
OUT=OUT_DIR/'development_density_management_area_national_archives_source_family_terminal_reconciliation.json'
FILES={
 's189':OUT_DIR/'development_density_management_area_national_archives_search_contract_forensic.json',
 's191':OUT_DIR/'development_density_management_area_national_archives_result_identity_forensic.json',
 's192':OUT_DIR/'development_density_management_area_national_archives_detail_contract_forensic.json',
 's193':OUT_DIR/'development_density_management_area_national_archives_detail_positive_control.json',
 's194':OUT_DIR/'development_density_management_area_national_archives_uqq700_bounded_candidate_search.json',
 's195':OUT_DIR/'development_density_management_area_national_archives_uqq700_related_candidate_detail_reconciliation.json',
 's197':OUT_DIR/'development_density_management_area_national_archives_search_tokenization_semantics_forensic.json',
 's199':OUT_DIR/'development_density_management_area_national_archives_detail_search_submit_contract_forensic.json',
 's201':OUT_DIR/'development_density_management_area_national_archives_detail_search_response_structure_forensic.json',
 's202':OUT_DIR/'development_density_management_area_national_archives_detail_search_result_identity_forensic.json',
 's203':OUT_DIR/'development_density_management_area_national_archives_detail_search_parser_replay.json',
 's204':OUT_DIR/'development_density_management_area_national_archives_seongnam_org_bounded_uqq700_search.json',
}

def load(p):
    if not p.exists():raise AssertionError(f'missing prerequisite output: {p}')
    return json.loads(p.read_text(encoding='utf-8'))

def g(d,*path,default=None):
    cur=d
    for k in path:
        if not isinstance(cur,dict) or k not in cur:return default
        cur=cur[k]
    return cur

def main():
    print('='*60);print('NATIONAL ARCHIVES SOURCE FAMILY TERMINAL RECONCILIATION - S205');print('='*60)
    print('Negative evidence: DISABLED');print('Legal absence inference: DISABLED');print('UQQ700 resolution: UNKNOWN')
    D={k:load(v) for k,v in FILES.items()}
    observations={
        'search_contract_captured':g(D['s189'],'summary','semantic_state')=='NATIONAL_ARCHIVES_SEARCH_CONTRACT_FORENSIC_CAPTURED' or g(D['s189'],'semantic_state')=='NATIONAL_ARCHIVES_SEARCH_CONTRACT_FORENSIC_CAPTURED',
        'result_identity_captured':g(D['s191'],'summary','semantic_state')=='NATIONAL_ARCHIVES_RESULT_IDENTITY_FORENSIC_CAPTURED' or g(D['s191'],'semantic_state')=='NATIONAL_ARCHIVES_RESULT_IDENTITY_FORENSIC_CAPTURED',
        'detail_contract_captured':g(D['s192'],'summary','semantic_state')=='NATIONAL_ARCHIVES_DETAIL_CONTRACT_FORENSIC_CAPTURED',
        'detail_positive_control_qualified':g(D['s193'],'summary','qualified_count')==2 and g(D['s193'],'summary','technical_unknown_count')==0,
        'general_bounded_direct_candidate_zero':g(D['s194'],'summary','direct_candidate_count')==0,
        'general_related_candidates_reconciled':g(D['s195'],'summary','contextual_non_uqq700_count')==4 and g(D['s195'],'summary','review_remaining_count')==0,
        'search_tokenization_limitation_captured':g(D['s197'],'summary','semantic_state')=='NATIONAL_ARCHIVES_SEARCH_TOKENIZATION_SEMANTICS_CAPTURED',
        'detail_submit_contract_captured':g(D['s199'],'summary','semantic_state')=='NATIONAL_ARCHIVES_DETAIL_SEARCH_SUBMIT_CONTRACT_FORENSIC_CAPTURED',
        'post_response_structure_captured':g(D['s201'],'summary','semantic_state')=='NATIONAL_ARCHIVES_DETAIL_SEARCH_RESPONSE_STRUCTURE_CAPTURED',
        'post_result_identity_captured':g(D['s202'],'summary','semantic_state')=='NATIONAL_ARCHIVES_DETAIL_SEARCH_RESULT_IDENTITY_FORENSIC_CAPTURED',
        'post_parser_qualified':g(D['s203'],'summary','semantic_state')=='NATIONAL_ARCHIVES_DETAIL_SEARCH_POST_PARSER_QUALIFIED',
        'org_filter_positive_control_qualified':g(D['s203'],'summary','org_filter_positive_control_resolved') is True,
        'seongnam_org_bounded_candidate_zero':g(D['s204'],'summary','candidate_count')==0,
        'seongnam_org_bounded_technical_unknown_zero':g(D['s204'],'summary','technical_unknown_count')==0,
    }
    technical_unknown_total=sum(int(g(D[k],'summary','technical_unknown_count',default=0) or 0) for k in ['s193','s194','s195','s197','s201','s203','s204'])
    source_closed=all(observations.values()) and technical_unknown_total==0
    semantic='NATIONAL_ARCHIVES_QUALIFIED_SEARCH_AND_SEONGNAM_ORG_FILTERED_SURFACES_RECONCILED_NO_UQQ700_CANDIDATE'
    out={'step':'STEP 17-21-C-16-8-T-101-S205','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','observations':observations,'summary':{'technical_unknown_total':technical_unknown_total,'source_family_operationally_closed':source_closed,'semantic_state':semantic if source_closed else 'NATIONAL_ARCHIVES_SOURCE_FAMILY_RECONCILIATION_PARTIAL','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'legal_absence_established':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'uqq700_final_resolution':'UNKNOWN','next_stage':'OTHER_HISTORICAL_OFFICIAL_SOURCE_FAMILY_OR_NOTICE_IDENTITY_REVERSE_DISCOVERY'},'prerequisite_files':{k:str(v) for k,v in FILES.items()}}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nOBSERVATIONS');[print(f'{k}: {v}') for k,v in observations.items()]
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'all observations true':all(observations.values()),'technical unknown total zero':technical_unknown_total==0,'source family operationally closed':source_closed,'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'legal absence not established':not out['summary']['legal_absence_established'],'unsafe promotion leakage zero':not any(out['summary'][k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','next stage set':bool(out['summary']['next_stage']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S205 National Archives source family terminal reconciliation failed')
if __name__=='__main__':main()
