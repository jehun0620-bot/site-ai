# -*- coding: utf-8 -*-
"""S69: determine whether test.hwp in Gazette 1868/1870 detail HTML is a real attachment reference or template/example text."""
from __future__ import annotations
import json
from pathlib import Path
import requests
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_municipal_gazette_1867_cluster_test_hwp_reference_forensic.json'
TARGETS=[('343270',1867),('343615',1868),('343834',1870)]
NEEDLES=['test.hwp','atchFileDetail','getFile','filePreview']
RADIUS=500

def main():
    print('='*60); print('GAZETTE 1867 CLUSTER TEST.HWP REFERENCE FORENSIC - S69'); print('='*60)
    print('Attachment body download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({'User-Agent':hwp5.USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    rows=[]
    for pst,gaz in TARGETS:
        url=f'https://www.seongnam.go.kr/bbs010308/{pst}'
        r=s.get(url,timeout=20,allow_redirects=True); r.raise_for_status(); text=r.text or ''
        needle_hits={}
        for needle in NEEDLES:
            hits=[]; pos=0
            low=text.lower(); nlow=needle.lower()
            while True:
                idx=low.find(nlow,pos)
                if idx<0: break
                lo=max(0,idx-RADIUS); hi=min(len(text),idx+len(needle)+RADIUS)
                hits.append({'index':idx,'context':' '.join(text[lo:hi].split())})
                pos=idx+len(needle)
            needle_hits[needle]=hits
        row={'gazette_number':gaz,'pstSn':pst,'http_status':r.status_code,'final_url':str(r.url),'html_chars':len(text),'needle_hits':needle_hits}
        rows.append(row)
        print(f'\nGazette {gaz} / {pst}')
        for needle in NEEDLES:
            hits=needle_hits[needle]
            print(f'  {needle} count:',len(hits))
            for i,h in enumerate(hits,1):
                print(f'    [{i}] {h["context"]}')
    test_rows=[r for r in rows if r['needle_hits']['test.hwp']]
    all_test_contexts=[]
    for r in test_rows:
        all_test_contexts.extend(h['context'] for h in r['needle_hits']['test.hwp'])
    template_markers=['sample','example','test','dummy','파일명','fileName','fileNm','preview','javascript','function']
    template_like=bool(all_test_contexts) and all(any(m.lower() in c.lower() for m in template_markers) for c in all_test_contexts)
    summary={'target_count':len(rows),'test_hwp_present_in_pstSn':[r['pstSn'] for r in test_rows],'test_hwp_total_hits':sum(len(r['needle_hits']['test.hwp']) for r in rows),'test_hwp_contexts_template_like':template_like,'all_detail_http_200':all(r['http_status']==200 for r in rows)}
    out={'step':'STEP 17-21-C-16-8-T-34-S69','rows':rows,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'three targets inspected':len(rows)==3,'detail transport ok':summary['all_detail_http_200'],'body download disabled':not out['attachment_body_download_executed'],'state mutation disabled':not out['state_mutation_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUT)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S69 validation failed')

if __name__=='__main__': main()
