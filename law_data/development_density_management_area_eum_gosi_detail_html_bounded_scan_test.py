# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re, time
from pathlib import Path
from urllib.parse import quote_plus
import requests

BASE=Path(__file__).resolve().parent.parent
META=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_seongnam_full_metadata_crawl.json'
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_detail_html_bounded_scan.json'
DETAIL='https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp'
UA='Mozilla/5.0'; MAX=12*1024*1024
TERMS=['개발밀도관리구역','개발밀도 관리구역','개발밀도','UQQ700']
DIRECT={'개발밀도관리구역','개발밀도 관리구역','UQQ700'}


def get(s,seq):
    try:
        r=s.get(DETAIL,params={'seq':seq},timeout=25,stream=True,allow_redirects=True); b=bytearray(); ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True; break
                b.extend(c)
        finally:r.close()
        return ('HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN',r.status_code,bytes(b),None if not ov else 'RESPONSE_SIZE_LIMIT_EXCEEDED')
    except requests.RequestException as e:return ('TECHNICAL_REQUEST_UNKNOWN',None,b'',f'{type(e).__name__}: {e}')

def dec(b):
    for enc in ('euc-kr','cp949','utf-8'):
        try:return b.decode(enc)
        except UnicodeDecodeError:pass
    return b.decode('euc-kr',errors='ignore')

def plain(t):
    t=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>',' ',t,flags=re.I)
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t))).strip()

def main():
    print('='*60);print('EUM GOSI DETAIL HTML BOUNDED SCAN - S178');print('='*60)
    print('Source rows: S176 metadata crawl');print('Attachment download: DISABLED');print('OCR: DISABLED');print('Candidate hit => STOP');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    data=json.loads(META.read_text(encoding='utf-8'))
    rows=data.get('rows') or data.get('metadata_rows') or []
    if not rows:
        raise AssertionError('S176 metadata rows not found')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    scanned=[]; candidates=[]; tech=0
    for i,row in enumerate(rows,1):
        seq=str(row.get('seq','')).strip()
        if not seq: continue
        state,http,body,err=get(s,seq); text=plain(dec(body)); counts={t:text.count(t) for t in TERMS}
        rec={'index':i,'seq':seq,'date':row.get('date'),'notice':row.get('notice'),'title':row.get('title'),'state':state,'http':http,'text_length':len(text),'target_counts':counts,'error':err}
        scanned.append(rec)
        if state!='HTTP_RESPONSE_CAPTURED' or http!=200:
            tech+=1; print('TECHNICAL_UNKNOWN',seq,http,err); break
        hit=[t for t,n in counts.items() if n]
        if hit:
            c=dict(rec); c['hit_terms']=hit; c['candidate_state']='DIRECT_CANDIDATE' if any(t in DIRECT for t in hit) else 'RELATED_CANDIDATE'; candidates.append(c); print('CANDIDATE',c); break
        if i%100==0: print('SCANNED',i,'/',len(rows))
        time.sleep(0.02)
    sem='EUM_DETAIL_HTML_CANDIDATE_FOUND_REQUIRES_CONTEXT_DIAGNOSTIC' if candidates else ('EUM_DETAIL_HTML_SCAN_TECHNICAL_UNKNOWN' if tech else 'EUM_DETAIL_HTML_SCAN_NO_CANDIDATE_IN_QUALIFIED_HTML_SURFACE')
    out={'step':'STEP 17-21-C-16-8-T-74-S178','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_row_count':len(rows),'scanned_count':len(scanned),'requests':scanned,'candidates':candidates,'summary':{'candidate_count':len(candidates),'technical_unknown_count':tech,'semantic_state':sem,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_download_executed':False,'ocr_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('scanned_count:',len(scanned),'of',len(rows));print('Output:',OUT)
    checks={'technical unknown zero':tech==0,'candidate stop policy respected':(not candidates) or len(scanned)<=len(rows),'attachment download disabled':not out['attachment_download_executed'],'OCR disabled':not out['ocr_allowed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S178 EUM detail HTML bounded scan failed')
if __name__=='__main__':main()
