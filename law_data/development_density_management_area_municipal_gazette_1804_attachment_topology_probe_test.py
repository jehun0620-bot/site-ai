# -*- coding: utf-8 -*-
"""S62: attachment topology probe for Gazette 1804 / pstSn 323596."""
from __future__ import annotations
import json
from pathlib import Path

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
REG=OUTDIR/'development_density_management_area_municipal_gazette_historical_row_registry_recovery.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_1804_attachment_topology_probe.json'
TARGET='323596'
WINDOW=3


def norm(v): return str(v or '').strip()


def main():
    print('='*60); print('GAZETTE 1804 ATTACHMENT TOPOLOGY PROBE - S62'); print('='*60)
    print('Attachment body download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    if not REG.exists(): raise FileNotFoundError(REG)
    reg=json.loads(REG.read_text(encoding='utf-8'))
    rows=[r for r in (reg.get('canonical_gazette_rows') or []) if norm(r.get('pstSn'))]
    rows.sort(key=lambda r:(hwp5.parse_date(r.get('date')) or hwp5.date.min,int(r.get('gazette_number') or 0),norm(r.get('pstSn'))))
    idx=next((i for i,r in enumerate(rows) if norm(r.get('pstSn'))==TARGET),None)
    if idx is None: raise AssertionError('target not found in registry')
    selected=rows[max(0,idx-WINDOW):min(len(rows),idx+WINDOW+1)]
    session=hwp5.requests.Session(); session.headers.update({'User-Agent':hwp5.USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    findings=[]
    for r in selected:
        pst=norm(r.get('pstSn'))
        rec={'gazette_number':r.get('gazette_number'),'date':norm(r.get('date')),'pstSn':pst,'is_target':pst==TARGET,'http_status':None,'json_detected':False,'attachment_count':None,'error':''}
        try:
            hs,mu,obj=hwp5.get_json(session,pst)
            rec['http_status']=hs; rec['metadata_url']=mu; rec['json_detected']=isinstance(obj,(dict,list))
            items=hwp5.flatten_items(obj)
            seen=[]
            for item in items:
                att=hwp5.hwp_attachment(item)
                if att and att.get('file_no') and att.get('file_no') not in seen: seen.append(att.get('file_no'))
            rec['attachment_count']=len(seen)
        except Exception as exc:
            rec['error']=repr(exc)
        findings.append(rec); print(rec)
    target_rows=[r for r in findings if r['is_target']]
    neighbors=[r for r in findings if not r['is_target']]
    target_empty=len(target_rows)==1 and target_rows[0].get('http_status')==200 and target_rows[0].get('attachment_count')==0
    neighbor_nonempty=sum(1 for r in neighbors if (r.get('attachment_count') or 0)>0)
    neighbor_empty=sum(1 for r in neighbors if r.get('http_status')==200 and r.get('attachment_count')==0)
    neighbors_ok=all(r.get('http_status')==200 and not r.get('error') for r in neighbors)
    isolated=target_empty and neighbors_ok and neighbor_nonempty==len(neighbors) and neighbor_empty==0
    summary={'target_empty_metadata':target_empty,'neighbor_count':len(neighbors),'neighbor_nonempty_count':neighbor_nonempty,'neighbor_empty_count':neighbor_empty,'neighbors_all_transport_ok':neighbors_ok,'isolated_empty_pattern':isolated}
    payload={'step':'STEP 17-21-C-16-8-T-34-S62','target_pstSn':TARGET,'rows':findings,'summary':summary,'attachment_body_downloaded':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT)
    unsafe=any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed'])
    vals={'target found':len(target_rows)==1,'target empty metadata':target_empty,'neighbors present':len(neighbors)>0,'neighbor transport ok':neighbors_ok,'at least one neighbor attachment':neighbor_nonempty>0,'body download disabled':not payload['attachment_body_downloaded'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not unsafe,'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('Gazette 1804 topology validation failed')

if __name__=='__main__': main()
