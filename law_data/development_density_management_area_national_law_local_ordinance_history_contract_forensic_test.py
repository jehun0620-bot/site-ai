# -*- coding: utf-8 -*-
from __future__ import annotations

import json, re
from pathlib import Path
from urllib.parse import urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_local_ordinance_history_contract_forensic.json'
URL='https://www.law.go.kr/ordinSc.do'
UA='Mozilla/5.0'
MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).strip()

def main():
    print('='*60);print('NATIONAL LAW LOCAL ORDINANCE HISTORY CONTRACT FORENSIC - S207');print('='*60)
    print('Forensic only; no UQQ700 absence inference');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        r=s.get(URL,timeout=30,allow_redirects=True);b=r.content[:MAX];t,e=dec(b)
        err=None
    except requests.RequestException as ex:
        r=None;b=b'';t='';e=None;err=f'{type(ex).__name__}: {ex}'
    forms=[]
    if r is not None:
        for fm in re.finditer(r'<form\b([^>]*)>([\s\S]*?)</form>',t,re.I):
            attrs=fm.group(1);body=fm.group(2)
            mid=re.search(r'\bid=["\']([^"\']+)',attrs,re.I); mname=re.search(r'\bname=["\']([^"\']+)',attrs,re.I); ma=re.search(r'\baction=["\']([^"\']*)',attrs,re.I); mm=re.search(r'\bmethod=["\']([^"\']+)',attrs,re.I)
            controls=[]
            for im in re.finditer(r'<input\b([^>]*)>',body,re.I):
                a=im.group(1);nm=re.search(r'\bname=["\']([^"\']+)',a,re.I);tp=re.search(r'\btype=["\']([^"\']+)',a,re.I);val=re.search(r'\bvalue=["\']([^"\']*)',a,re.I)
                if nm:controls.append({'tag':'input','name':nm.group(1),'type':tp.group(1) if tp else None,'value':val.group(1) if val else None,'checked':bool(re.search(r'\bchecked\b',a,re.I))})
            for sm in re.finditer(r'<select\b([^>]*)>([\s\S]*?)</select>',body,re.I):
                a=sm.group(1);nm=re.search(r'\bname=["\']([^"\']+)',a,re.I)
                if nm:
                    opts=[]
                    for om in re.finditer(r'<option\b([^>]*)>([\s\S]*?)</option>',sm.group(2),re.I):
                        oa=om.group(1);ov=re.search(r'\bvalue=["\']([^"\']*)',oa,re.I);opts.append({'value':ov.group(1) if ov else clean(om.group(2)),'text':clean(om.group(2)),'selected':bool(re.search(r'\bselected\b',oa,re.I))})
                    controls.append({'tag':'select','name':nm.group(1),'options':opts[:50]})
            forms.append({'id':mid.group(1) if mid else None,'name':mname.group(1) if mname else None,'method':(mm.group(1).upper() if mm else 'GET'),'action':urljoin(str(r.url),ma.group(1)) if ma else str(r.url),'control_count':len(controls),'controls':controls})
    funcs={}
    for name in ['search','ordin','history','hist','detail','view','move','page','select']:
        vals=[]
        for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*'+name+r'[\w$]*)\s*\([^)]*\)\s*\{',t,re.I):
            fn=m.group(1);start=m.start();frag=clean(t[start:min(len(t),start+5000)])
            if fn not in vals:vals.append((fn,frag[:2200]))
            if len(vals)>=12:break
        if vals:funcs[name]=vals
    endpoints=[]
    for m in re.finditer(r'["\']([^"\']+\.(?:do|jsp)(?:\?[^"\']*)?)["\']',t,re.I):
        u=m.group(1)
        if any(x in u.lower() for x in ['ordin','history','hist','search','lsinfo','det']):
            u=urljoin(str(r.url) if r else URL,u)
            if u not in endpoints:endpoints.append(u)
            if len(endpoints)>=80:break
    keywords={x:(x in t) for x in ['자치법규','연혁','현행','폐지','성남시','도시계획','개정','시행']}
    print('HTTP:',r.status_code if r else None,'| URL:',str(r.url) if r else URL,'| BYTES:',len(b),'| ENCODING:',e,'| ERROR:',err)
    print('FORMS:',len(forms))
    for f in forms:print('FORM:',f['id'],f['name'],f['method'],f['action'],'CONTROLS:',f['control_count']);print('  NAMES:',[c['name'] for c in f['controls']])
    print('KEYWORDS:',keywords);print('ENDPOINTS:',endpoints[:30]);print('FUNCTION GROUPS:',{k:[x[0] for x in v] for k,v in funcs.items()})
    out={'step':'STEP 17-21-C-16-8-T-103-S207','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','http':r.status_code if r else None,'final_url':str(r.url) if r else None,'byte_length':len(b),'encoding':e,'error':err,'forms':forms,'keywords':keywords,'endpoint_hints':endpoints,'function_groups':funcs,'summary':{'form_count':len(forms),'endpoint_hint_count':len(endpoints),'has_ordinance_keyword':keywords['자치법규'],'has_history_keyword':keywords['연혁'],'technical_unknown_count':1 if err or r is None or r.status_code!=200 else 0,'semantic_state':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY_CONTRACT_FORENSIC_CAPTURED' if r is not None and r.status_code==200 else 'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY_CONTRACT_FORENSIC_UNRESOLVED','source_family_qualified':False,'search_contract_qualified':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'http 200':r is not None and r.status_code==200,'form observed':len(forms)>0,'ordinance keyword observed':keywords['자치법규'],'history keyword observed':keywords['연혁'],'technical unknown zero':out['summary']['technical_unknown_count']==0,'source not prematurely qualified':not out['summary']['source_family_qualified'],'search not prematurely qualified':not out['summary']['search_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S207 national law local ordinance history contract forensic failed')
if __name__=='__main__':main()
