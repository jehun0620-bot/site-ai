# -*- coding: utf-8 -*-
"""S53: detail-page attachment reference probe for Gazette 1597/1598. No body download/state mutation."""
from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_municipal_gazette_1597_1598_detail_attachment_reference_probe.json'
TARGETS=[(1597,'2019-04-09','181109'),(1598,'2019-04-15','181376')]
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
KEYS=['atchFileDetail','atchFile','fileDown','download','fileNo','pstSn','.hwp','.pdf','.xls','.hwpx','getFile','filePreview']

def official(u):
    h=(urlparse(u).hostname or '').lower(); return h=='go.kr' or h.endswith('.go.kr')

def main():
    print('='*60); print('GAZETTE 1597 / 1598 DETAIL ATTACHMENT REFERENCE PROBE'); print('='*60)
    print('Attachment body download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    rows=[]
    for gaz,date,pst in TARGETS:
        url=f'https://www.seongnam.go.kr/bbs010308/{pst}'
        r=s.get(url,timeout=20,allow_redirects=True); r.raise_for_status(); text=r.text
        counts={k:text.lower().count(k.lower()) for k in KEYS}
        hrefs=re.findall(r'''href\s*=\s*["']([^"']+)["']''',text,re.I)
        onclicks=re.findall(r'''onclick\s*=\s*["']([^"']+)["']''',text,re.I)
        relevant_hrefs=[x for x in hrefs if any(k in x.lower() for k in ['file','atch','download','.hwp','.pdf','.xls','.hwpx'])][:50]
        relevant_onclicks=[x for x in onclicks if any(k in x.lower() for k in ['file','atch','download'])][:50]
        file_tokens=sorted(set(re.findall(r'''fileNo[^0-9]{0,20}([0-9]{1,12})''',text,re.I)))
        pst_tokens=sorted(set(re.findall(r'''pstSn[^0-9]{0,20}([0-9]{1,12})''',text,re.I)))
        filenames=sorted(set(re.findall(r'''[^<>"']+\.(?:hwp|hwpx|pdf|xls|xlsx)''',text,re.I)))[:50]
        lines=[ln.strip() for ln in text.splitlines() if any(k.lower() in ln.lower() for k in ['atchFileDetail','getFile','filePreview','fn_atch_detail','orginlFileNm','fileNo'])][:80]
        row={'gazette_number':gaz,'date':date,'pstSn':pst,'http_status':r.status_code,'final_url':str(r.url),'html_chars':len(text),'keyword_counts':counts,'attachment_like_hrefs':relevant_hrefs,'attachment_like_onclicks':relevant_onclicks,'fileNo_tokens':file_tokens,'pstSn_tokens':pst_tokens,'filename_tokens':filenames,'suspicious_lines':lines}
        rows.append(row)
        print('\n'+'-'*60); print('Gazette:',gaz,date,'pstSn',pst); print('HTTP:',r.status_code); print('HTML chars:',len(text)); print('Keyword counts:',counts); print('Attachment-like hrefs:',relevant_hrefs); print('Attachment-like onclicks:',relevant_onclicks); print('FileNo tokens:',file_tokens); print('pstSn tokens:',pst_tokens); print('Filename tokens:',filenames); print('Suspicious lines:'); [print(' ',x) for x in lines]
    out={'step':'STEP 17-21-C-16-8-T-34-S53','targets':rows,'request_count':2,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'two exact targets':len(rows)==2,'all HTTP 200':all(x['http_status']==200 for x in rows),'all official host':all(official(x['final_url']) for x in rows),'body download disabled':not out['attachment_body_download_executed'],'state mutation disabled':not out['state_mutation_executed'],'negative evidence disabled':not out['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nOutput:',OUT); print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('detail attachment reference probe failed')
if __name__=='__main__': main()
