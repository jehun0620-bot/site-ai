# -*- coding: utf-8 -*-
from __future__ import annotations

import html,json,re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_seongnam_urban_planning_ordinance_history_positive_control_replay.json'
PAGE='https://www.law.go.kr/ordinSc.do'
HISTORY='https://www.law.go.kr/ordinHstListR.do'
TARGET='성남시 도시계획 조례'
CURRENT_SEQ='2111431'
CURRENT_ID='2146953'
UA='Mozilla/5.0'; MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()

def read_body(r):
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c:continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    t,e=dec(bytes(b));return bytes(b),t,e,ov

def main():
    print('='*60);print('NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE HISTORY POSITIVE CONTROL REPLAY - S216');print('='*60)
    print('Anchor:',TARGET,'ordinSeq=',CURRENT_SEQ,'ordinId=',CURRENT_ID)
    print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        pre=s.get(PAGE,timeout=30,allow_redirects=True);pre_http=pre.status_code;pre_err=None
    except requests.RequestException as ex:
        pre=None;pre_http=None;pre_err=f'{type(ex).__name__}: {ex}'
    # fOrdinHstShow -> fSlimUpdate("lsHstLayer","ordinHstListR.do",makeParam(ordinVO.ordinValue))
    params={'ordinSeq':CURRENT_SEQ,'ordinId':CURRENT_ID,'ordinNm':TARGET,'chrClsCd':'010202','nwYn':'Y','vSct':TARGET,'conDatGubunCd':'1','gubun':'ELIS'}
    try:
        r=s.post(HISTORY,data=params,headers={'Referer':PAGE,'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},timeout=60,allow_redirects=True,stream=True)
        b,t,e,ov=read_body(r);http=r.status_code;err=None;ctype=r.headers.get('Content-Type')
    except requests.RequestException as ex:
        b=b'';t='';e=None;ov=False;http=None;err=f'{type(ex).__name__}: {ex}';ctype=None
    plain=clean(t)
    # Capture version navigation calls. ordinViewOrdinHst(seq,nwYn) is qualified by S215.
    rows=[]
    for m in re.finditer(r'ordinViewOrdinHst\s*\(\s*["\']?([0-9]+)["\']?\s*,\s*["\']?([^"\')\s,]+)["\']?\s*\)',t,re.I):
        seq=m.group(1);nw=m.group(2)
        ctx=clean(t[max(0,m.start()-900):min(len(t),m.end()+1400)])
        # best-effort metadata from row context
        date=None;anc_no=None;rr=None
        dm=re.search(r'(20\d{2}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2})',ctx)
        if dm:date=dm.group(1)
        am=re.search(r'제\s*([0-9]+)\s*호',ctx)
        if am:anc_no=am.group(1)
        for token in ['제정','전부개정','일부개정','폐지','타법개정']:
            if token in ctx:rr=token;break
        item={'ordin_seq':seq,'nw_yn':nw,'date_hint':date,'anc_no_hint':anc_no,'revision_hint':rr,'context':ctx[:2600]}
        if item not in rows:rows.append(item)
    # fallback: capture any likely seq-bearing onclick/href history snippets
    snippets=[]
    for m in re.finditer(r'(?:ordinViewOrdinHst|ordinInfoP\.do\?ordinSeq=)[^<\n]{0,700}',t,re.I):
        x=clean(m.group(0))[:900]
        if x not in snippets:snippets.append(x)
        if len(snippets)>=100:break
    # current identity should normally be present in history surface; older seq establishes version chain.
    seqs=[]
    for x in rows:
        if x['ordin_seq'] not in seqs:seqs.append(x['ordin_seq'])
    current_seen=CURRENT_SEQ in seqs or CURRENT_SEQ in t
    older=[x for x in seqs if x!=CURRENT_SEQ]
    target_seen=TARGET.replace(' ','') in re.sub(r'\s+','',plain)
    identity_qualified=bool(rows and current_seen and older)
    technical=(1 if pre_http!=200 else 0)+(1 if http!=200 or ov or err else 0)
    print('PRECHECK HTTP:',pre_http,'ERROR:',pre_err)
    print('HISTORY HTTP:',http,'BYTES:',len(b),'ENCODING:',e,'OVERFLOW:',ov,'ERROR:',err)
    print('TARGET SEEN:',target_seen)
    print('VERSION ROW COUNT:',len(rows))
    print('UNIQUE ORDIN SEQ COUNT:',len(seqs))
    print('CURRENT SEQ SEEN:',current_seen)
    print('OLDER VERSION COUNT:',len(older))
    for x in rows[:30]:print('  VERSION:',x)
    if not rows:
        print('HISTORY SNIPPETS:',snippets[:30])
    semantic='NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_HISTORY_VERSION_IDENTITY_QUALIFIED' if identity_qualified and technical==0 else 'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_HISTORY_VERSION_IDENTITY_UNRESOLVED'
    out={'step':'STEP 17-21-C-16-8-T-111-S216','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','anchor':{'ordinance_name':TARGET,'current_ordin_seq':CURRENT_SEQ,'ordin_id':CURRENT_ID,'gubun':'ELIS'},'request_contract':{'method':'POST','url':HISTORY,'params':params},'response':{'http':http,'byte_length':len(b),'encoding':e,'overflow':ov,'error':err,'content_type':ctype},'version_rows':rows,'unique_ordin_seqs':seqs,'fallback_history_snippets':snippets,'summary':{'target_seen':target_seen,'current_seq_seen':current_seen,'older_version_count':len(older),'history_contract_qualified':identity_qualified and technical==0,'history_version_identity_qualified':identity_qualified and technical==0,'technical_unknown_count':technical,'semantic_state':semantic,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'preflight 200':pre_http==200,'history 200':http==200,'technical unknown zero':technical==0,'version rows observed':len(rows)>0,'current seq seen':current_seen,'older version observed':len(older)>0,'history contract qualified':out['summary']['history_contract_qualified'],'history version identity qualified':out['summary']['history_version_identity_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S216 ordinance history positive control replay failed')
if __name__=='__main__':main()
