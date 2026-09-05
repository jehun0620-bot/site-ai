# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE=Path(__file__).resolve().parent.parent
S177=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_detail_representation_qualification.json'
S179=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_attachment_delivery_contract_qualification.json'
OUT=BASE/'law_data'/'output'/'development_density_management_area_eum_gosi_attachment_contract_forensic.json'
DETAIL='https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp'
UA='Mozilla/5.0'; MAX=12*1024*1024
SAMPLES=['638968','117916','117520']

def get(s,seq):
    try:
        r=s.get(DETAIL,params={'seq':seq},timeout=25,stream=True,allow_redirects=True); b=bytearray(); ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True; break
                b.extend(c)
        finally:r.close()
        return ('HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN',r.status_code,str(r.url),bytes(b),None if not ov else 'RESPONSE_SIZE_LIMIT_EXCEEDED')
    except requests.RequestException as e:return ('TECHNICAL_REQUEST_UNKNOWN',None,DETAIL,b'',f'{type(e).__name__}: {e}')

def dec(b):
    for enc in ('euc-kr','cp949','utf-8'):
        try:return b.decode(enc)
        except UnicodeDecodeError:pass
    return b.decode('euc-kr',errors='ignore')

def main():
    print('='*60);print('EUM GOSI ATTACHMENT CONTRACT FORENSIC - S180');print('='*60)
    print('Attachment download execution: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    src177=json.loads(S177.read_text(encoding='utf-8')) if S177.exists() else {}
    src179=json.loads(S179.read_text(encoding='utf-8')) if S179.exists() else {}
    prior={str(x.get('seq')):x for x in src179.get('results',[]) if x.get('seq')}
    prior_links={str(x.get('seq')):x.get('attachment_like_links',[]) for x in src177.get('samples',[]) if x.get('seq')}
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    rows=[]
    for seq in SAMPLES:
        state,http,final,body,err=get(s,seq); text=dec(body)
        hrefs=[]; onclicks=[]; forms=[]; scripts=[]
        for m in re.finditer(r'<a\b([^>]*)>([\s\S]*?)</a>',text,re.I):
            attrs=m.group(1); label=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',m.group(2)))).strip()
            hrefm=re.search(r'href=["\']([^"\']+)',attrs,re.I); onm=re.search(r'onclick=["\']([^"\']+)',attrs,re.I)
            h=html.unescape(hrefm.group(1)) if hrefm else ''
            o=html.unescape(onm.group(1)) if onm else ''
            low=(h+' '+o+' '+label).lower()
            if any(k in low for k in ['file','down','attach','첨부','다운','pdf','hwp','hwpx']):
                hrefs.append({'label':label,'href_raw':h,'href_resolved':urljoin(final,h) if h and not h.lower().startswith('javascript:') else h,'href_scheme':urlparse(h).scheme,'onclick':o})
        for m in re.finditer(r'<form\b([^>]*)>',text,re.I):
            a=m.group(1)
            if re.search(r'file|down|attach',a,re.I): forms.append(re.sub(r'\s+',' ',a).strip())
        for m in re.finditer(r'function\s+([A-Za-z0-9_$]+)\s*\([^)]*\)\s*\{[\s\S]{0,2000}?\}',text,re.I):
            frag=m.group(0)
            if re.search(r'file|down|attach',frag,re.I): scripts.append(re.sub(r'\s+',' ',frag).strip())
        row={'seq':seq,'detail_state':state,'detail_http':http,'prior_s177_links':prior_links.get(seq,[]),'prior_s179_state':prior.get(seq,{}).get('state'),'prior_s179_error':prior.get(seq,{}).get('error'),'attachment_anchor_evidence':hrefs[:30],'form_evidence':forms[:20],'script_evidence':scripts[:20],'detail_error':err}
        rows.append(row)
        print('SEQ:',seq,'| DETAIL:',state,http,'| PRIOR_S179:',row['prior_s179_state'],'| ERROR:',row['prior_s179_error'])
        for x in hrefs[:10]: print('  ANCHOR:',x)
        for x in scripts[:5]: print('  SCRIPT:',x)
    tech=sum(r['detail_state']=='TECHNICAL_REQUEST_UNKNOWN' for r in rows)
    out={'step':'STEP 17-21-C-16-8-T-76-S180','target_name':'개발밀도관리구역','standard_code':'UQQ700','rows':rows,'summary':{'sample_count':len(rows),'technical_unknown_count':tech,'semantic_state':'EUM_ATTACHMENT_CONTRACT_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'attachment_download_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'sample exact':len(rows)==3,'technical unknown zero':tech==0,'attachment download disabled':not out['attachment_download_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()): raise AssertionError('S180 EUM attachment contract forensic failed')
if __name__=='__main__':main()
