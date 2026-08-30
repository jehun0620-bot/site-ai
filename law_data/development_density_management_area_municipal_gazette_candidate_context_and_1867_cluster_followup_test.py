# -*- coding: utf-8 -*-
"""S66: compact candidate-context review plus wider Gazette 1867 cluster topology follow-up."""
from __future__ import annotations
import json
from pathlib import Path

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
S65=OUTDIR/'development_density_management_area_municipal_gazette_1823_1843_candidate_and_1858_1867_unknown_forensic.json'
REG=OUTDIR/'development_density_management_area_municipal_gazette_historical_row_registry_recovery.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_candidate_context_and_1867_cluster_followup.json'
TARGET='343270'; WINDOW=5


def norm(v): return str(v or '').strip()

def compact_context(text:str, term='개발밀도', radius=180):
    idx=text.find(term)
    if idx<0: return text[:360]
    lo=max(0,idx-radius); hi=min(len(text),idx+len(term)+radius)
    return ' '.join(text[lo:hi].split())

def metadata_count(session,pst):
    try:
        hs,mu,obj=hwp5.get_json(session,pst); items=hwp5.flatten_items(obj); seen=[]
        for item in items:
            att=hwp5.hwp_attachment(item)
            if att and att.get('file_no') and att['file_no'] not in seen: seen.append(att['file_no'])
        return hs,mu,len(seen),''
    except Exception as exc:
        return None,'',None,repr(exc)

def main():
    print('='*60); print('CANDIDATE CONTEXT + GAZETTE 1867 CLUSTER FOLLOW-UP - S66'); print('='*60)
    print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    if not S65.exists(): raise FileNotFoundError(S65)
    if not REG.exists(): raise FileNotFoundError(REG)
    s65=json.loads(S65.read_text(encoding='utf-8'))
    compact=[]
    for c in s65.get('candidate_results') or []:
        contexts=c.get('contexts') or []
        uniq=[]; seen=set()
        for h in contexts:
            x=compact_context(h.get('context',''))
            if x and x not in seen:
                seen.add(x); uniq.append(x)
        rec={'gazette_number':c.get('gazette_number'),'date':c.get('date'),'pstSn':c.get('pstSn'),'term_count':c.get('term_count'),'unique_compact_context_count':len(uniq),'compact_contexts':uniq}
        compact.append(rec)
        print(f"\nCANDIDATE Gazette {rec['gazette_number']} / {rec['pstSn']} / term_count {rec['term_count']} / unique_contexts {len(uniq)}")
        for i,x in enumerate(uniq,1): print(f'  CONTEXT {i}: {x}')

    reg=json.loads(REG.read_text(encoding='utf-8'))
    rows=[r for r in (reg.get('canonical_gazette_rows') or []) if norm(r.get('pstSn'))]
    rows.sort(key=lambda r:(hwp5.parse_date(r.get('date')) or hwp5.date.min,int(r.get('gazette_number') or 0),norm(r.get('pstSn'))))
    idx=next(i for i,r in enumerate(rows) if norm(r.get('pstSn'))==TARGET)
    selected=rows[max(0,idx-WINDOW):min(len(rows),idx+WINDOW+1)]
    session=hwp5.requests.Session(); session.headers.update({'User-Agent':hwp5.USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    findings=[]
    for r in selected:
        pst=norm(r.get('pstSn')); hs,mu,count,err=metadata_count(session,pst)
        rec={'gazette_number':r.get('gazette_number'),'date':norm(r.get('date')),'pstSn':pst,'is_target':pst==TARGET,'http_status':hs,'attachment_count':count,'error':err,'metadata_url':mu}
        findings.append(rec); print('CLUSTER:',rec)
    empties=[r for r in findings if r.get('http_status')==200 and r.get('attachment_count')==0]
    target_index=next(i for i,r in enumerate(findings) if r['is_target'])
    contiguous=[findings[target_index]]
    i=target_index-1
    while i>=0 and findings[i].get('http_status')==200 and findings[i].get('attachment_count')==0: contiguous.insert(0,findings[i]); i-=1
    i=target_index+1
    while i<len(findings) and findings[i].get('http_status')==200 and findings[i].get('attachment_count')==0: contiguous.append(findings[i]); i+=1
    summary={'target_pstSn':TARGET,'window_neighbor_count':len(findings)-1,'empty_metadata_pstSn':[r['pstSn'] for r in empties],'contiguous_empty_cluster_pstSn':[r['pstSn'] for r in contiguous],'contiguous_empty_cluster_size':len(contiguous),'all_transport_ok':all(r.get('http_status')==200 and not r.get('error') for r in findings),'has_nonempty_before_cluster':any((r.get('attachment_count') or 0)>0 for r in findings[:max(0,target_index-len(contiguous))]),'has_nonempty_after_cluster':any((r.get('attachment_count') or 0)>0 for r in findings[target_index+len(contiguous):])}
    print('\nCLUSTER SUMMARY:',summary)
    payload={'step':'STEP 17-21-C-16-8-T-34-S66','candidate_compact_contexts':compact,'gazette_1867_cluster_rows':findings,'cluster_summary':summary,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'two candidates summarized':len(compact)==2,'candidate counts retained':all(r.get('term_count')==34 for r in compact),'target present in cluster':any(r['is_target'] for r in findings),'transport ok':summary['all_transport_ok'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nOutput:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S66 validation failed')

if __name__=='__main__': main()
