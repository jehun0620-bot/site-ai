# -*- coding: utf-8 -*-
"""S68-R1: corrected detail/metadata forensic for the 2023-06~07 attachment-empty cluster around Gazette 1867."""
from __future__ import annotations
import json
import re
from pathlib import Path

import requests
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE=Path(__file__).resolve().parent.parent
OUTDIR=BASE/'law_data'/'output'
REG=OUTDIR/'development_density_management_area_municipal_gazette_historical_row_registry_recovery.json'
OUT=OUTDIR/'development_density_management_area_municipal_gazette_1867_cluster_detail_metadata_forensic.json'
TARGETS=['343270','343615','343834']
DETAIL_URL='https://www.seongnam.go.kr/bbs010308/{pst}'


def norm(v): return str(v or '').strip()

def main():
    print('='*60); print('GAZETTE 1867 CLUSTER DETAIL/METADATA FORENSIC - S68-R1'); print('='*60)
    print('Attachment body download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    if not REG.exists(): raise FileNotFoundError(REG)
    reg=json.loads(REG.read_text(encoding='utf-8'))
    registry={norm(r.get('pstSn')):r for r in (reg.get('canonical_gazette_rows') or []) if norm(r.get('pstSn'))}
    session=requests.Session(); session.headers.update({'User-Agent':hwp5.USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    records=[]
    for pst in TARGETS:
        if pst not in registry: raise AssertionError(f'missing registry row {pst}')
        row=registry[pst]
        hs,mu,obj=hwp5.get_json(session,pst)
        flat=hwp5.flatten_items(obj)
        attachments=[]
        for item in flat:
            att=hwp5.hwp_attachment(item)
            if att and att.get('file_no'):
                key=(att.get('file_no'),att.get('file_name'))
                if key not in [(a.get('file_no'),a.get('file_name')) for a in attachments]: attachments.append(att)
        url=DETAIL_URL.format(pst=pst)
        resp=session.get(url,timeout=20,allow_redirects=True)
        text=resp.text or ''
        title=''
        m=re.search(r'<title[^>]*>(.*?)</title>',text,re.I|re.S)
        if m: title=' '.join(re.sub(r'<[^>]+>',' ',m.group(1)).split())
        file_nos=sorted(set(re.findall(r'''fileNo[^0-9]{0,20}([0-9]{1,12})''',text,re.I)))
        concrete_names=sorted(set(re.findall(r'''[^<>"']+\.(?:hwp|hwpx|pdf|xls|xlsx)''',text,re.I)))[:50]
        plumbing={k:(k in text) for k in ['atchFileDetail','getFile','filePreview']}
        rec={'gazette_number':row.get('gazette_number'),'date':norm(row.get('date')),'pstSn':pst,'metadata_http':hs,'metadata_url':mu,'metadata_attachment_count':len(attachments),'metadata_attachments':attachments,'detail_http':resp.status_code,'detail_url':url,'detail_final_url':str(resp.url),'detail_title':title,'detail_html_chars':len(text),'dynamic_attachment_plumbing':plumbing,'concrete_file_nos':file_nos,'concrete_file_names':concrete_names}
        records.append(rec); print('RECORD:',rec)
    same_detail_pattern=len({tuple(sorted(r['dynamic_attachment_plumbing'].items())) for r in records})==1
    all_metadata_empty=all(r['metadata_http']==200 and r['metadata_attachment_count']==0 for r in records)
    all_detail_ok=all(r['detail_http']==200 for r in records)
    no_concrete_refs=all(not r['concrete_file_nos'] and not r['concrete_file_names'] for r in records)
    all_dynamic_plumbing=all(all(r['dynamic_attachment_plumbing'].values()) for r in records)
    summary={'target_count':len(records),'all_metadata_empty':all_metadata_empty,'all_detail_http_200':all_detail_ok,'same_detail_attachment_plumbing_pattern':same_detail_pattern,'all_have_dynamic_attachment_plumbing':all_dynamic_plumbing,'all_without_concrete_attachment_refs':no_concrete_refs,'cluster_consistent_technical_pattern':all_metadata_empty and all_detail_ok and same_detail_pattern and all_dynamic_plumbing and no_concrete_refs}
    payload={'step':'STEP 17-21-C-16-8-T-34-S68-R1','records':records,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'three targets inspected':len(records)==3,'metadata transport ok':all(r['metadata_http']==200 for r in records),'detail transport ok':all_detail_ok,'body download disabled':not payload['attachment_body_download_executed'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S68-R1 forensic validation failed')

if __name__=='__main__': main()
