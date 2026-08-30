# -*- coding: utf-8 -*-
"""S65: inspect Gazette 1823/1843 candidate contexts and 1858/1867 attachment topology."""
from __future__ import annotations
import json
from pathlib import Path

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_quarantine_resume_test as h2

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
REG=OUTDIR/'development_density_management_area_municipal_gazette_historical_row_registry_recovery.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_1823_1843_candidate_and_1858_1867_unknown_forensic.json'
CANDIDATES=[('330054',1823,'2022-11-03'),('334568',1843,'2023-02-06')]
UNKNOWNS=['339293','343270']
TERM='개발밀도'; RADIUS=500; WINDOW=2; LARGE_FILE_LIMIT=64*1024*1024


def norm(v): return str(v or '').strip()


def candidate_probe(session,pst,gaz,date):
    hs,mu,obj=hwp5.get_json(session,pst); att=hwp5.hwp_attachment(obj)
    if not att: raise AssertionError(f'candidate attachment missing: {pst}')
    old_limit=hwp5.MAX_FILE_BYTES; old_parser=hwp5.parse_records_text
    try:
        hwp5.MAX_FILE_BYTES=LARGE_FILE_LIMIT; hwp5.parse_records_text=h2.high_limit_parse_records_text
        ds,du,raw=hwp5.get_file(session,pst,att['file_no']); ext=hwp5.extract_hwp5(raw)
    finally:
        hwp5.MAX_FILE_BYTES=old_limit; hwp5.parse_records_text=old_parser
    text=ext.get('text','') or ''; hits=[]; pos=0
    while True:
        idx=text.find(TERM,pos)
        if idx<0: break
        lo=max(0,idx-RADIUS); hi=min(len(text),idx+len(TERM)+RADIUS)
        hits.append({'index':idx,'context':text[lo:hi]}); pos=idx+len(TERM)
    return {'gazette_number':gaz,'date':date,'pstSn':pst,'metadata_http':hs,'attachment':att,'download_http':ds,'download_bytes':len(raw),'extract_ok':ext.get('ok'),'extract_error':ext.get('error'),'text_chars':len(text),'term':TERM,'term_count':len(hits),'contexts':hits}


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
    print('='*60); print('CANDIDATE + UNKNOWN FORENSIC PROBE - S65'); print('='*60)
    print('State mutation: DISABLED'); print('OCR: DISABLED'); print('Negative evidence: DISABLED')
    if not REG.exists(): raise FileNotFoundError(REG)
    reg=json.loads(REG.read_text(encoding='utf-8'))
    rows=[r for r in (reg.get('canonical_gazette_rows') or []) if norm(r.get('pstSn'))]
    rows.sort(key=lambda r:(hwp5.parse_date(r.get('date')) or hwp5.date.min,int(r.get('gazette_number') or 0),norm(r.get('pstSn'))))
    session=hwp5.requests.Session(); session.headers.update({'User-Agent':hwp5.USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})

    candidate_results=[]
    for pst,gaz,date in CANDIDATES:
        rec=candidate_probe(session,pst,gaz,date); candidate_results.append(rec)
        print(f'\nCANDIDATE Gazette {gaz} / {pst} / term_count {rec["term_count"]}')
        for i,h in enumerate(rec['contexts'],1):
            print('\n'+'-'*80); print(f'CONTEXT {i} | INDEX {h["index"]}'); print(h['context'])

    topology=[]
    for target in UNKNOWNS:
        idx=next(i for i,r in enumerate(rows) if norm(r.get('pstSn'))==target)
        selected=rows[max(0,idx-WINDOW):min(len(rows),idx+WINDOW+1)]
        findings=[]
        for r in selected:
            pst=norm(r.get('pstSn')); hs,mu,count,err=metadata_count(session,pst)
            rec={'gazette_number':r.get('gazette_number'),'date':norm(r.get('date')),'pstSn':pst,'is_target':pst==target,'http_status':hs,'attachment_count':count,'error':err,'metadata_url':mu}
            findings.append(rec); print('\nTOPOLOGY:',rec)
        t=[r for r in findings if r['is_target']]; n=[r for r in findings if not r['is_target']]
        target_empty=len(t)==1 and t[0]['http_status']==200 and t[0]['attachment_count']==0
        neighbors_ok=all(r['http_status']==200 and not r['error'] for r in n)
        nonempty=sum(1 for r in n if (r['attachment_count'] or 0)>0); empty=sum(1 for r in n if r['http_status']==200 and r['attachment_count']==0)
        summary={'target_pstSn':target,'target_empty_metadata':target_empty,'neighbor_count':len(n),'neighbor_nonempty_count':nonempty,'neighbor_empty_count':empty,'neighbors_all_transport_ok':neighbors_ok,'isolated_empty_pattern':target_empty and neighbors_ok and nonempty==len(n) and empty==0}
        topology.append({'target_pstSn':target,'rows':findings,'summary':summary}); print('TOPOLOGY SUMMARY:',summary)

    output={'step':'STEP 17-21-C-16-8-T-34-S65','candidate_results':candidate_results,'unknown_topology':topology,'state_mutation_executed':False,'ocr_used':False,'negative_evidence_allowed':False,'verified_positive':False,'runtime_registration_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'final_positive_promotion_allowed':False}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    unsafe=any(output[k] for k in ['verified_positive','runtime_registration_allowed','site_positive_allowed','site_negative_allowed','final_positive_promotion_allowed'])
    vals={'two candidates inspected':len(candidate_results)==2,'candidate downloads ok':all(r['metadata_http']==200 and r['download_http']==200 and r['extract_ok'] for r in candidate_results),'candidate term counts preserved':all(r['term_count']==34 for r in candidate_results),'two unknown topologies inspected':len(topology)==2,'state mutation disabled':not output['state_mutation_executed'],'OCR disabled':not output['ocr_used'],'negative evidence disabled':not output['negative_evidence_allowed'],'unsafe promotion leakage zero':not unsafe,'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nOutput:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S65 forensic validation failed')

if __name__=='__main__': main()
