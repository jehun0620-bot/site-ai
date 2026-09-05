# -*- coding: utf-8 -*-
from __future__ import annotations

import json,re
from pathlib import Path
from urllib.parse import urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_local_ordinance_external_js_contract_forensic.json'
PAGE='https://www.law.go.kr/ordinSc.do'
UA='Mozilla/5.0'; MAX=8*1024*1024
TARGET_NAMES=['OrdinSearchObj','OrdinValueObj','makeParam','fOrdinUpdate','syncChkFilter']

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s): return re.sub(r'\s+',' ',s).strip()

def extract_block(text, pattern):
    m=re.search(pattern,text,re.I)
    if not m:return None
    start=m.start(); i=m.end(); depth=1; quote=None; esc=False
    while i<len(text) and depth>0:
        ch=text[i]
        if quote:
            if esc:esc=False
            elif ch=='\\':esc=True
            elif ch==quote:quote=None
        else:
            if ch in ('"',"'"):quote=ch
            elif ch=='{':depth+=1
            elif ch=='}':depth-=1
        i+=1
    return text[start:i] if depth==0 else text[start:min(len(text),start+16000)]

def main():
    print('='*60);print('NATIONAL LAW LOCAL ORDINANCE EXTERNAL JS CONTRACT FORENSIC - S212');print('='*60)
    print('Forensic only; no search execution');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        pr=s.get(PAGE,timeout=30,allow_redirects=True);pt,_=dec(pr.content[:MAX]);perr=None
    except requests.RequestException as ex:
        pr=None;pt='';perr=f'{type(ex).__name__}: {ex}'
    scripts=[]
    for m in re.finditer(r'<script\b[^>]*src=["\']([^"\']+)["\']',pt,re.I):
        u=urljoin(PAGE,m.group(1).replace('&amp;','&'))
        if 'law.go.kr' in u and u not in scripts:scripts.append(u)
    results=[]; found={k:[] for k in TARGET_NAMES}
    for u in scripts:
        try:
            r=s.get(u,headers={'Referer':PAGE},timeout=30,allow_redirects=True);b=r.content[:MAX];t,e=dec(b);err=None
        except requests.RequestException as ex:
            r=None;b=b'';t='';e=None;err=f'{type(ex).__name__}: {ex}'
        hits=[]
        for name in TARGET_NAMES:
            blocks=[]
            patterns=[]
            if name in ('OrdinSearchObj','OrdinValueObj'):
                patterns=[rf'function\s+{name}\s*\([^)]*\)\s*\{{',rf'(?:var|let|const)\s+{name}\s*=\s*function\s*\([^)]*\)\s*\{{']
            else:
                patterns=[rf'function\s+{name}\s*\([^)]*\)\s*\{{']
            for pat in patterns:
                blk=extract_block(t,pat)
                if blk:
                    blocks.append(clean(blk)[:16000])
            if blocks:
                found[name].append({'script_url':u,'blocks':blocks});hits.append(name)
        if hits or 'ordin.js' in u.lower() or 'common' in u.lower():
            results.append({'url':u,'http':r.status_code if r else None,'bytes':len(b),'encoding':e,'error':err,'hits':hits})
            print('SCRIPT:',u,'HTTP:',r.status_code if r else None,'BYTES:',len(b),'HITS:',hits,'ERROR:',err)
    # derive constructor param defaults from captured OrdinSearchObj block text
    defaults=[]
    for rec in found['OrdinSearchObj']:
        for blk in rec['blocks']:
            defaults += re.findall(r'this\.param\.([A-Za-z_$][\w$]*)\s*=\s*([^;]+);',blk)
            defaults += re.findall(r'this\.param\s*=\s*\{([^}]*)\}',blk)
    print('\nFOUND SUMMARY:',{k:len(v) for k,v in found.items()})
    for k,v in found.items():
        for rec in v[:3]:
            print('\nTARGET:',k,'SCRIPT:',rec['script_url'])
            for blk in rec['blocks'][:2]:print(blk[:7000])
    print('\nDERIVED DEFAULTS:',defaults[:100])
    technical=sum(1 for x in results if x['http']!=200 or x['error']) + (1 if pr is None or pr.status_code!=200 else 0)
    out={'step':'STEP 17-21-C-16-8-T-107-S212','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','page_preflight':{'http':pr.status_code if pr else None,'error':perr},'script_count':len(scripts),'scripts':results,'targets':found,'derived_constructor_defaults':defaults,'summary':{'ordin_search_obj_captured':bool(found['OrdinSearchObj']),'make_param_captured':bool(found['makeParam']),'f_ordin_update_captured':bool(found['fOrdinUpdate']),'technical_unknown_count':technical,'semantic_state':'NATIONAL_LAW_LOCAL_ORDINANCE_EXTERNAL_JS_CONTRACT_CAPTURED' if pr is not None and pr.status_code==200 and bool(found['OrdinSearchObj']) else 'NATIONAL_LAW_LOCAL_ORDINANCE_EXTERNAL_JS_CONTRACT_UNRESOLVED','search_execution_enabled':False,'search_contract_qualified':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'page http 200':pr is not None and pr.status_code==200,'ordinSearchObj captured':bool(found['OrdinSearchObj']),'technical unknown zero':technical==0,'search execution disabled':not out['summary']['search_execution_enabled'],'search not prematurely qualified':not out['summary']['search_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S212 national law ordinance external JS contract forensic failed')
if __name__=='__main__':main()
