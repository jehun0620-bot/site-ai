# -*- coding: utf-8 -*-
from __future__ import annotations

import html,json,re
from pathlib import Path
from urllib.parse import urlencode
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_seongnam_urban_planning_ordinance_browser_equivalent_positive_control.json'
PAGE='https://www.law.go.kr/ordinSc.do'
LIST='https://www.law.go.kr/ordinScListR.do?menuId=3&subMenuId=27&tabMenuId=139'
TARGET='성남시 도시계획 조례'
UA='Mozilla/5.0'; MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def read_body(r):
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c:continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    t,e=dec(bytes(b));return bytes(b),t,e,ov

def parse(text):
    plain=clean(text)
    direct={}
    for key in ['direct1','direct2','direct3','direct4','gubun1','gubun2']:
        m=re.search(r'<input[^>]+id=["\']'+re.escape(key)+r'["\'][^>]*>',text,re.I)
        if m:
            v=re.search(r'value=["\']([^"\']*)',m.group(0),re.I);direct[key]=html.unescape(v.group(1)) if v else ''
    calls=[]
    for fn in ['fOrdinListView','ordinViewAll']:
        for m in re.finditer(fn+r'\s*\(([^)]{1,500})\)',text,re.I):
            calls.append({'function':fn,'args':clean(m.group(1)),'context':clean(text[max(0,m.start()-900):min(len(text),m.end()+1300)])[:2400]})
    title_hits=[]
    for m in re.finditer(re.escape(TARGET),text):
        title_hits.append(clean(text[max(0,m.start()-800):min(len(text),m.end()+1000)])[:2200])
        if len(title_hits)>=10:break
    total=None
    for pat in [r'총\s*<strong[^>]*>\s*([0-9,]+)\s*</strong>\s*건',r'총\s*([0-9,]+)\s*건']:
        m=re.search(pat,text,re.I)
        if m: total=m.group(1); break
    return {'target_exact_seen':TARGET in plain,'seongnam_seen':'성남시' in plain,'urban_planning_seen':'도시계획' in plain,'total_count_text':total,'direct_identity':direct,'result_calls':calls[:50],'target_contexts':title_hits,'plain_prefix':plain[:3000]}

def main():
    print('='*60);print('NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE BROWSER-EQUIVALENT POSITIVE CONTROL - S213');print('='*60)
    print('Known positive control:',TARGET);print('Method: POST browser-equivalent list request');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        pre=s.get(PAGE,timeout=30,allow_redirects=True);pre_http=pre.status_code;pre_err=None
    except requests.RequestException as ex:
        pre=None;pre_http=None;pre_err=f'{type(ex).__name__}: {ex}'
    # OrdinSearchObj defaults + ordinSearch() mutations for current ordinance-name tab.
    params={'q':TARGET,'outmax':'50','p3':'3','idxList':'LsKwdNm_idx,OrdinNm_idx','pg':'1','section':'ordinNm','dtlYn':'N'}
    # makeParam omits empty fields. requests form encoding reproduces POST semantics.
    try:
        r=s.post(LIST,data=params,headers={'Referer':PAGE,'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},timeout=60,allow_redirects=True,stream=True)
        b,t,e,ov=read_body(r);http=r.status_code;final_url=str(r.url);ctype=r.headers.get('Content-Type');err=None
    except requests.RequestException as ex:
        b=b'';t='';e=None;ov=False;http=None;final_url=LIST;ctype=None;err=f'{type(ex).__name__}: {ex}'
    parsed=parse(t)
    identity_observed=bool(parsed['direct_identity']) or any(c['function']=='fOrdinListView' for c in parsed['result_calls']) or any(c['function']=='ordinViewAll' for c in parsed['result_calls'])
    positive=bool(parsed['target_exact_seen'] and identity_observed)
    print('PRECHECK HTTP:',pre_http,'ERROR:',pre_err)
    print('POST HTTP:',http,'BYTES:',len(b),'ENCODING:',e,'OVERFLOW:',ov,'ERROR:',err)
    print('REQUEST URL:',LIST)
    print('POST PARAMS:',params)
    print('TARGET EXACT SEEN:',parsed['target_exact_seen'])
    print('TOTAL COUNT:',parsed['total_count_text'])
    print('DIRECT IDENTITY:',parsed['direct_identity'])
    print('RESULT CALL COUNT:',len(parsed['result_calls']))
    for x in parsed['result_calls'][:10]:print('  CALL:',x)
    for x in parsed['target_contexts'][:5]:print('  TARGET CONTEXT:',x)
    technical=(1 if pre_http!=200 else 0)+(1 if http!=200 or ov or err else 0)
    semantic='NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_BROWSER_EQUIVALENT_SEARCH_QUALIFIED' if positive else 'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_BROWSER_EQUIVALENT_SEARCH_UNRESOLVED'
    out={'step':'STEP 17-21-C-16-8-T-108-S213','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','positive_control':TARGET,'request_contract':{'method':'POST','url':LIST,'params':params,'serialized_preview':urlencode(params)},'preflight':{'http':pre_http,'error':pre_err},'response':{'http':http,'final_url':final_url,'content_type':ctype,'byte_length':len(b),'encoding':e,'overflow':ov,'error':err},'parsed':parsed,'summary':{'positive_control_resolved':positive,'result_identity_observed':identity_observed,'technical_unknown_count':technical,'semantic_state':semantic,'search_contract_qualified':positive,'result_identity_qualified':positive,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'preflight 200':pre_http==200,'post 200':http==200,'technical unknown zero':technical==0,'positive control resolved':positive,'result identity observed':identity_observed,'search contract qualified':out['summary']['search_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S213 browser-equivalent ordinance positive control failed')
if __name__=='__main__':main()
