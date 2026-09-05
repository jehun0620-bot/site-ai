# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_contract_forensic.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'
QUERY='성남시'
MAX=16*1024*1024
TARGET_FUNCTIONS=['showItemDetailWithQuery','showDetail']

def fetch():
    params={'query_type':'keyword','is_detail':'yes','upside_query':QUERY,'keyword':QUERY,'beforeKeyword':'','afterKeyword':'','doc_type':'','srchinit':'ritem'}
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    r=s.get(URL,params=params,timeout=30,stream=True,allow_redirects=True)
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c:continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    return s,r.status_code,str(r.url),bytes(b),ov

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def extract_function(text,name):
    m=re.search(r'function\s+'+re.escape(name)+r'\s*\([^)]*\)\s*\{',text,re.I)
    if not m:return None
    start=m.start(); i=m.end()-1; depth=0; quote=None; esc=False
    for j in range(i,len(text)):
        ch=text[j]
        if quote:
            if esc:esc=False
            elif ch=='\\':esc=True
            elif ch==quote:quote=None
            continue
        if ch in ('"',"'"):quote=ch;continue
        if ch=='{':depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:return re.sub(r'\s+',' ',text[start:j+1]).strip()
    return re.sub(r'\s+',' ',text[start:start+8000]).strip()

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL CONTRACT FORENSIC - S192');print('='*60)
    print('Query:',QUERY);print('Detail request execution: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s,http,final,body,ov=fetch();text,encoding=dec(body)
    functions={name:extract_function(text,name) for name in TARGET_FUNCTIONS}
    urls=[]
    for name,frag in functions.items():
        if not frag:continue
        for u in re.findall(r'["\']([^"\']+\.(?:do|jsp)(?:\?[^"\']*)?)["\']',frag,re.I):
            if u not in urls:urls.append(u)
    param_names=[]
    for name,frag in functions.items():
        if not frag:continue
        for p in re.findall(r'(?:data\s*:\s*\{|\?|&|\+\s*["\']&)([A-Za-z0-9_]+)',frag):
            if p not in param_names:param_names.append(p)
        for p in re.findall(r'([A-Za-z0-9_]+)\s*:',frag):
            if p not in param_names:param_names.append(p)
    call_examples=[]
    for m in re.finditer(r'showItemDetailWithQuery\(([^)]*)\)',text,re.I):
        args=[x.strip().strip("'\"") for x in m.group(1).split(',')]
        if len(args)>=5:call_examples.append(args[:5])
        if len(call_examples)>=10:break
    out={'step':'STEP 17-21-C-16-8-T-88-S192','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','query':QUERY,'response':{'http':http,'final_url':final,'byte_length':len(body),'encoding':encoding,'overflow':ov},'functions':functions,'candidate_endpoint_literals':urls,'candidate_parameter_names':param_names,'showItemDetailWithQuery_examples':call_examples,'summary':{'function_found_count':sum(v is not None for v in functions.values()),'endpoint_literal_count':len(urls),'call_example_count':len(call_examples),'semantic_state':'NATIONAL_ARCHIVES_DETAIL_CONTRACT_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'detail_request_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('HTTP:',http,'| BYTES:',len(body),'| ENCODING:',encoding)
    for name,frag in functions.items():
        print('FUNCTION',name,':', 'FOUND' if frag else 'NOT_FOUND')
        if frag:print(' ',frag[:5000])
    print('ENDPOINT_LITERALS:',urls)
    print('PARAM_NAMES:',param_names)
    print('CALL_EXAMPLES:',call_examples)
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'http 200':http==200,'overflow false':not ov,'both functions found':all(functions.values()),'call examples observed':len(call_examples)>0,'detail request disabled':not out['detail_request_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S192 National Archives detail contract forensic failed')
if __name__=='__main__':main()
