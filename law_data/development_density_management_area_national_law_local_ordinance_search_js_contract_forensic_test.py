# -*- coding: utf-8 -*-
from __future__ import annotations

import json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_local_ordinance_search_js_contract_forensic.json'
URL='https://www.law.go.kr/ordinSc.do'
UA='Mozilla/5.0'
MAX=8*1024*1024
TARGET_FUNCS=['ordinSearch','fSearch','dtlSchOrdin','movePage','fOrdinListView']

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',s).strip()

def extract_function(text,name):
    m=re.search(r'function\s+'+re.escape(name)+r'\s*\(([^)]*)\)\s*\{',text,re.I)
    if not m:return None
    i=m.end(); depth=1; in_s=None; esc=False
    while i<len(text) and depth>0:
        ch=text[i]
        if in_s:
            if esc:esc=False
            elif ch=='\\':esc=True
            elif ch==in_s:in_s=None
        else:
            if ch in ('"',"'"):in_s=ch
            elif ch=='{':depth+=1
            elif ch=='}':depth-=1
        i+=1
    return {'args':m.group(1),'body':text[m.end():i-1] if depth==0 else text[m.end():min(len(text),m.end()+12000)]}

def main():
    print('='*60);print('NATIONAL LAW LOCAL ORDINANCE SEARCH JS CONTRACT FORENSIC - S209');print('='*60)
    print('Forensic only; no search execution');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        r=s.get(URL,timeout=30,allow_redirects=True);b=r.content[:MAX];t,e=dec(b);err=None
    except requests.RequestException as ex:
        r=None;b=b'';t='';e=None;err=f'{type(ex).__name__}: {ex}'
    funcs={}
    for name in TARGET_FUNCS:
        f=extract_function(t,name)
        if f:
            body=f['body'];
            funcs[name]={'args':f['args'],'body':clean(body)[:12000],
                         'param_assignments':re.findall(r'(?:param|ordinSearchObj\.param)\.([A-Za-z_$][\w$]*)\s*=\s*([^;]+);',body),
                         'object_assignments':re.findall(r'ordinSearchObj\.param\.([A-Za-z_$][\w$]*)\s*=\s*([^;]+);',body),
                         'endpoint_literals':re.findall(r'["\']([^"\']+\.(?:do|jsp)(?:\?[^"\']*)?)["\']',body,re.I),
                         'input_refs':sorted(set(re.findall(r'(?:el\(["\']([^"\']+)["\']\)|\$\(["\']#([^"\']+)["\']\)|document\.getElementById\(["\']([^"\']+)["\']\))',body)))}
    globals_={}
    for pat,name in [(r'ordinSearchObj\s*=\s*\{([\s\S]{0,12000}?)\};','ordinSearchObj_init'),(r'var\s+ordinSearchObj\s*=\s*\{([\s\S]{0,12000}?)\};','ordinSearchObj_var')]:
        m=re.search(pat,t,re.I)
        if m:globals_[name]=clean(m.group(1))[:12000]
    html_query_refs=[]
    for m in re.finditer(r'(?:name|id)=["\']([^"\']*(?:query|q|search|ordin|area|sort)[^"\']*)["\']',t,re.I):
        v=m.group(1)
        if v not in html_query_refs:html_query_refs.append(v)
        if len(html_query_refs)>=100:break
    print('HTTP:',r.status_code if r else None,'| BYTES:',len(b),'| ENCODING:',e,'| ERROR:',err)
    for k,v in funcs.items():
        print('\nFUNCTION:',k,'ARGS:',v['args']);print('PARAM_ASSIGNMENTS:',v['param_assignments']);print('ENDPOINTS:',v['endpoint_literals']);print('INPUT_REFS:',v['input_refs']);print('BODY:',v['body'][:5000])
    print('\nGLOBAL OBJECTS:',globals_);print('HTML QUERY REFS:',html_query_refs)
    out={'step':'STEP 17-21-C-16-8-T-104-S209','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','http':r.status_code if r else None,'final_url':str(r.url) if r else None,'byte_length':len(b),'encoding':e,'error':err,'functions':funcs,'global_objects':globals_,'html_query_refs':html_query_refs,'summary':{'captured_function_count':len(funcs),'ordinSearch_captured':'ordinSearch' in funcs,'fSearch_captured':'fSearch' in funcs,'movePage_captured':'movePage' in funcs,'technical_unknown_count':1 if err or r is None or r.status_code!=200 else 0,'semantic_state':'NATIONAL_LAW_LOCAL_ORDINANCE_SEARCH_JS_CONTRACT_CAPTURED' if r is not None and r.status_code==200 and len(funcs)>0 else 'NATIONAL_LAW_LOCAL_ORDINANCE_SEARCH_JS_CONTRACT_UNRESOLVED','search_execution_enabled':False,'search_contract_qualified':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'http 200':r is not None and r.status_code==200,'ordinSearch captured':'ordinSearch' in funcs,'fSearch captured':'fSearch' in funcs,'technical unknown zero':out['summary']['technical_unknown_count']==0,'search execution disabled':not out['summary']['search_execution_enabled'],'search not prematurely qualified':not out['summary']['search_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S209 national law ordinance search JS contract forensic failed')
if __name__=='__main__':main()
