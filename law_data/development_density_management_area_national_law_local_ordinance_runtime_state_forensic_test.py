# -*- coding: utf-8 -*-
from __future__ import annotations

import json,re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_local_ordinance_runtime_state_forensic.json'
URL='https://www.law.go.kr/ordinSc.do'
UA='Mozilla/5.0'; MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',s).strip()

def main():
    print('='*60);print('NATIONAL LAW LOCAL ORDINANCE RUNTIME STATE FORENSIC - S211');print('='*60)
    print('Forensic only; no search execution');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        r=s.get(URL,timeout=30,allow_redirects=True);b=r.content[:MAX];t,e=dec(b);err=None
    except requests.RequestException as ex:
        r=None;b=b'';t='';e=None;err=f'{type(ex).__name__}: {ex}'
    # capture assignments/declarations of runtime search state
    names=['linkUrl','ordinSearchObj','searchId','queryValCheck','chkFilter','tabMenuIdx','subMenuIdx','gIsWide','ordinVO']
    state={}
    for name in names:
        hits=[]
        pats=[rf'\bvar\s+{re.escape(name)}\s*=\s*([^;]+);',rf'\blet\s+{re.escape(name)}\s*=\s*([^;]+);',rf'\bconst\s+{re.escape(name)}\s*=\s*([^;]+);',rf'\b{re.escape(name)}\s*=\s*([^;]+);']
        for pat in pats:
            for m in re.finditer(pat,t,re.I):
                frag=clean(t[max(0,m.start()-500):min(len(t),m.end()+1800)])
                item={'expr':m.group(1).strip()[:1200],'context':frag[:2600]}
                if item not in hits:hits.append(item)
                if len(hits)>=20:break
            if len(hits)>=20:break
        state[name]=hits
    # capture makeParam function and update call helpers
    funcs={}
    for fn in ['makeParam','fOrdinUpdate','fOrdinUpd','syncChkFilter','ordinSearchChk']:
        m=re.search(r'function\s+'+re.escape(fn)+r'\s*\(([^)]*)\)\s*\{',t,re.I)
        if m:
            start=m.start(); funcs[fn]=clean(t[start:min(len(t),start+9000)])[:9000]
    # capture literal constructor-ish snippets around ordinSearchObj
    obj_context=[]
    for m in re.finditer(r'ordinSearchObj',t,re.I):
        frag=clean(t[max(0,m.start()-1500):min(len(t),m.end()+3500)])
        if frag not in obj_context:obj_context.append(frag)
        if len(obj_context)>=20:break
    # hidden inputs and checked radios relevant to default state
    controls=[]
    for im in re.finditer(r'<input\b([^>]*)>',t,re.I):
        a=im.group(1); nm=re.search(r'\b(?:name|id)=["\']([^"\']+)',a,re.I)
        if not nm:continue
        n=nm.group(1)
        if any(k.lower() in n.lower() for k in ['query','ordin','area','org','filter','sub','tab','outmax','gubun']):
            tp=re.search(r'\btype=["\']([^"\']+)',a,re.I); val=re.search(r'\bvalue=["\']([^"\']*)',a,re.I)
            controls.append({'name_or_id':n,'type':tp.group(1) if tp else None,'value':val.group(1) if val else None,'checked':bool(re.search(r'\bchecked\b',a,re.I))})
    print('HTTP:',r.status_code if r else None,'| BYTES:',len(b),'| ENCODING:',e,'| ERROR:',err)
    for k,v in state.items():
        print('\nSTATE',k,'COUNT',len(v))
        for x in v[:8]:print(' ',x)
    print('\nFUNCTIONS:',list(funcs))
    for k,v in funcs.items():print('\nFUNCTION',k,':',v[:5000])
    print('\nCONTROL SAMPLE:',controls[:80])
    out={'step':'STEP 17-21-C-16-8-T-106-S211','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','http':r.status_code if r else None,'final_url':str(r.url) if r else None,'byte_length':len(b),'encoding':e,'error':err,'runtime_state':state,'functions':funcs,'ordin_search_context':obj_context,'controls':controls,'summary':{'link_url_assignment_count':len(state['linkUrl']),'ordin_search_obj_assignment_count':len(state['ordinSearchObj']),'make_param_captured':'makeParam' in funcs,'f_ordin_update_captured':'fOrdinUpdate' in funcs,'technical_unknown_count':1 if err or r is None or r.status_code!=200 else 0,'semantic_state':'NATIONAL_LAW_LOCAL_ORDINANCE_RUNTIME_STATE_FORENSIC_CAPTURED' if r is not None and r.status_code==200 else 'NATIONAL_LAW_LOCAL_ORDINANCE_RUNTIME_STATE_FORENSIC_UNRESOLVED','search_execution_enabled':False,'search_contract_qualified':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'http 200':r is not None and r.status_code==200,'ordinSearchObj state observed':len(state['ordinSearchObj'])>0,'technical unknown zero':out['summary']['technical_unknown_count']==0,'search execution disabled':not out['summary']['search_execution_enabled'],'search not prematurely qualified':not out['summary']['search_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S211 national law ordinance runtime state forensic failed')
if __name__=='__main__':main()
