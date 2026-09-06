# -*- coding: utf-8 -*-
from __future__ import annotations

import html,json,re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_seongnam_urban_planning_ordinance_positive_control_normalized.json'
PAGE='https://www.law.go.kr/ordinSc.do'
LIST='https://www.law.go.kr/ordinScListR.do?menuId=3&subMenuId=27&tabMenuId=139'
TARGET='성남시 도시계획 조례'
EXPECTED_SEQ='2111431'
UA='Mozilla/5.0'; MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def strip_tags(s): return html.unescape(re.sub(r'<[^>]+>',' ',s))
def norm(s): return re.sub(r'\s+','',strip_tags(s or ''))

def read_body(r):
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c:continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    t,e=dec(bytes(b));return bytes(b),t,e,ov

def input_value(text,key):
    m=re.search(r'<input[^>]+id=["\']'+re.escape(key)+r'["\'][^>]*>',text,re.I)
    if not m:return None
    v=re.search(r'value=["\']([^"\']*)',m.group(0),re.I)
    return html.unescape(v.group(1)) if v else ''

def main():
    print('='*60);print('NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE NORMALIZED POSITIVE CONTROL - S214');print('='*60)
    print('Known positive control:',TARGET);print('Expected current ordinSeq:',EXPECTED_SEQ);print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        pre=s.get(PAGE,timeout=30,allow_redirects=True);pre_http=pre.status_code;pre_err=None
    except requests.RequestException as ex:
        pre=None;pre_http=None;pre_err=f'{type(ex).__name__}: {ex}'
    params={'q':TARGET,'outmax':'50','p3':'3','idxList':'LsKwdNm_idx,OrdinNm_idx','pg':'1','section':'ordinNm','dtlYn':'N'}
    try:
        r=s.post(LIST,data=params,headers={'Referer':PAGE,'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},timeout=60,allow_redirects=True,stream=True)
        b,t,e,ov=read_body(r);http=r.status_code;err=None
    except requests.RequestException as ex:
        b=b'';t='';e=None;ov=False;http=None;err=f'{type(ex).__name__}: {ex}'
    direct={k:input_value(t,k) for k in ['direct1','direct2','direct3','direct4','gubun1','gubun2']}
    target_norm=norm(TARGET); direct3_norm=norm(direct.get('direct3'))
    page_norm=norm(t)
    target_seen=target_norm in page_norm
    direct_target_match=direct3_norm==target_norm
    seq_match=(direct.get('direct1')==EXPECTED_SEQ)
    current_match=(direct.get('direct4')=='3')
    identity_complete=all(direct.get(k) not in (None,'') for k in ['direct1','direct2','direct3','direct4','gubun1','gubun2'])
    calls=[]
    for m in re.finditer(r'ordinViewAll\s*\(([^)]{1,500})\)',t,re.I):
        ctx=strip_tags(t[max(0,m.start()-800):min(len(t),m.end()+1200)])
        calls.append({'args':re.sub(r'\s+',' ',m.group(1)).strip(),'context':re.sub(r'\s+',' ',ctx).strip()[:2200],'target_seen_normalized':target_norm in norm(ctx),'expected_seq_seen':EXPECTED_SEQ in m.group(1)})
    target_call=[x for x in calls if x['expected_seq_seen'] and x['target_seen_normalized']]
    positive=bool(http==200 and not ov and err is None and target_seen and direct_target_match and seq_match and current_match and identity_complete and target_call)
    technical=(1 if pre_http!=200 else 0)+(1 if http!=200 or ov or err else 0)
    print('PRECHECK HTTP:',pre_http,'ERROR:',pre_err)
    print('POST HTTP:',http,'BYTES:',len(b),'ENCODING:',e,'OVERFLOW:',ov,'ERROR:',err)
    print('DIRECT IDENTITY:',direct)
    print('TARGET NORMALIZED SEEN:',target_seen)
    print('DIRECT TARGET MATCH:',direct_target_match)
    print('EXPECTED SEQ MATCH:',seq_match)
    print('CURRENT MATCH:',current_match)
    print('IDENTITY COMPLETE:',identity_complete)
    print('TARGET CALL COUNT:',len(target_call))
    for x in target_call[:5]:print('  TARGET CALL:',x)
    out={'step':'STEP 17-21-C-16-8-T-109-S214','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','positive_control':TARGET,'request_contract':{'method':'POST','url':LIST,'params':params},'response':{'http':http,'byte_length':len(b),'encoding':e,'overflow':ov,'error':err},'direct_identity':direct,'normalized_checks':{'target_seen':target_seen,'direct_target_match':direct_target_match,'expected_seq_match':seq_match,'current_match':current_match,'identity_complete':identity_complete,'target_call_count':len(target_call)},'target_calls':target_call,'summary':{'positive_control_resolved':positive,'current_ordin_seq':direct.get('direct1'),'search_contract_qualified':positive,'result_identity_qualified':positive,'technical_unknown_count':technical,'semantic_state':'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_SEARCH_AND_RESULT_IDENTITY_QUALIFIED' if positive else 'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_NORMALIZED_POSITIVE_CONTROL_UNRESOLVED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'preflight 200':pre_http==200,'post 200':http==200,'technical unknown zero':technical==0,'positive control resolved':positive,'current ordin seq exact':direct.get('direct1')==EXPECTED_SEQ,'search contract qualified':out['summary']['search_contract_qualified'],'result identity qualified':out['summary']['result_identity_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S214 normalized ordinance positive control failed')
if __name__=='__main__':main()
