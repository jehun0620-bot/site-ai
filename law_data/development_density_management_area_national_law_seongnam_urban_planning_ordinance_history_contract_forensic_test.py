# -*- coding: utf-8 -*-
from __future__ import annotations

import html,json,re
from pathlib import Path
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_seongnam_urban_planning_ordinance_history_contract_forensic.json'
PAGE='https://www.law.go.kr/ordinSc.do'
LIST='https://www.law.go.kr/ordinScListR.do?menuId=3&subMenuId=27&tabMenuId=139'
DETAIL='https://www.law.go.kr/ordinInfoR.do'
TARGET='성남시 도시계획 조례'
ORDIN_SEQ='2111431'
UA='Mozilla/5.0'; MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()

def read_body(r):
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c:continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    t,e=dec(bytes(b));return bytes(b),t,e,ov

def fetch_post(s,url,data,referer):
    try:
        r=s.post(url,data=data,headers={'Referer':referer,'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},timeout=60,allow_redirects=True,stream=True)
        b,t,e,ov=read_body(r)
        return {'http':r.status_code,'url':str(r.url),'body':b,'text':t,'encoding':e,'overflow':ov,'error':None,'content_type':r.headers.get('Content-Type')}
    except requests.RequestException as ex:
        return {'http':None,'url':url,'body':b'','text':'','encoding':None,'overflow':False,'error':f'{type(ex).__name__}: {ex}','content_type':None}

def capture_functions(text,names):
    out={}
    for name in names:
        hits=[]
        for m in re.finditer(r'function\s+'+re.escape(name)+r'\s*\(([^)]*)\)\s*\{',text,re.I):
            start=m.start();i=m.end();depth=1;quote=None;esc=False
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
            body=text[start:i] if depth==0 else text[start:min(len(text),start+12000)]
            hits.append({'args':m.group(1),'body':re.sub(r'\s+',' ',body).strip()[:12000]})
        if hits: out[name]=hits
    return out

def main():
    print('='*60);print('NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE HISTORY CONTRACT FORENSIC - S215');print('='*60)
    print('Anchor ordinance:',TARGET,'ordinSeq=',ORDIN_SEQ);print('Forensic only; no history conclusion');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    # establish browser-like session + resolve current list identity
    try:
        pre=s.get(PAGE,timeout=30,allow_redirects=True);pre_http=pre.status_code;pre_err=None
    except requests.RequestException as ex:
        pre=None;pre_http=None;pre_err=f'{type(ex).__name__}: {ex}'
    list_params={'q':TARGET,'outmax':'50','p3':'3','idxList':'LsKwdNm_idx,OrdinNm_idx','pg':'1','section':'ordinNm','dtlYn':'N'}
    lr=fetch_post(s,LIST,list_params,PAGE)
    # fOrdinListView sets ordinValue: vSct, ordinSeq, gubun, nwYn, conDatGubunCd and detail defaults.
    detail_params={'ordinSeq':ORDIN_SEQ,'chrClsCd':'010202','nwYn':'Y','vSct':TARGET,'conDatGubunCd':'1','gubun':'ELIS'}
    dr=fetch_post(s,DETAIL,detail_params,LIST)
    text=dr['text']
    # Capture visible history-related endpoints, JS calls, parameters, and hidden identity values.
    endpoint_hints=sorted(set(re.findall(r'[A-Za-z0-9_/.-]*(?:Hst|Hist|history|rvs|Rvs)[A-Za-z0-9_/?.=&-]*\.do(?:\?[^"\'<>\s]*)?',text,re.I)))
    all_do=sorted(set(re.findall(r'[A-Za-z0-9_/.-]+\.do(?:\?[^"\'<>\s]*)?',text,re.I)))
    history_do=[x for x in all_do if re.search(r'hst|hist|rvs|history',x,re.I)]
    call_hits=[]
    for pat in [r'([A-Za-z_$][\w$]*(?:Hst|Hist|Rvs|history)[\w$]*)\s*\(([^)]{0,800})\)',r'([A-Za-z_$][\w$]*)\s*\(([^)]{0,800}(?:hst|hist|rvs|history)[^)]{0,800})\)']:
        for m in re.finditer(pat,text,re.I):
            ctx=clean(text[max(0,m.start()-800):min(len(text),m.end()+1500)])
            item={'function':m.group(1),'args':clean(m.group(2)),'context':ctx[:2600]}
            if item not in call_hits:call_hits.append(item)
            if len(call_hits)>=100:break
    hidden={}
    for m in re.finditer(r'<input\b([^>]*)>',text,re.I):
        attrs=m.group(1)
        idm=re.search(r'\b(?:id|name)=["\']([^"\']+)',attrs,re.I)
        if not idm:continue
        key=idm.group(1)
        if re.search(r'ordin|hst|hist|rvs|gubun|anc|nwYn|seq',key,re.I):
            vm=re.search(r'\bvalue=["\']([^"\']*)',attrs,re.I)
            hidden[key]=html.unescape(vm.group(1)) if vm else ''
    scripts=[]
    for m in re.finditer(r'<script\b[^>]*src=["\']([^"\']+)["\']',text,re.I):
        scripts.append(m.group(1))
    inline_funcs=capture_functions(text,['fOrdinHst','fOrdinHstList','fHst','fLsHst','fOrdinRvs','ordinHstView','fRvsDoc'])
    # Also inspect already-qualified external ordin.js for history functions.
    ext_url='https://www.law.go.kr/LSW/js/ordin/ordin.js'
    try:
        er=s.get(ext_url,headers={'Referer':PAGE},timeout=30);et,_=dec(er.content[:MAX]);eerr=None;eh=er.status_code
    except requests.RequestException as ex:
        et='';eerr=f'{type(ex).__name__}: {ex}';eh=None
    ext_names=[]
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*(?:Hst|Hist|Rvs|history)[\w$]*)\s*\(',et,re.I):
        if m.group(1) not in ext_names:ext_names.append(m.group(1))
    ext_funcs=capture_functions(et,ext_names[:80])
    ext_endpoints=sorted(set(x for x in re.findall(r'[A-Za-z0-9_/.-]+\.do(?:\?[^"\'<>\s]*)?',et,re.I) if re.search(r'hst|hist|rvs|history',x,re.I)))
    print('PRECHECK HTTP:',pre_http,'ERROR:',pre_err)
    print('LIST HTTP:',lr['http'],'BYTES:',len(lr['body']),'ERROR:',lr['error'])
    print('DETAIL HTTP:',dr['http'],'BYTES:',len(dr['body']),'ERROR:',dr['error'])
    print('DETAIL TARGET SEEN:',TARGET.replace(' ','') in re.sub(r'\s+','',clean(text)))
    print('HISTORY ENDPOINT HINTS:',history_do[:100])
    print('HISTORY CALLS:',call_hits[:30])
    print('HIDDEN IDENTITY:',hidden)
    print('INLINE HISTORY FUNCTIONS:',list(inline_funcs))
    print('EXTERNAL JS HTTP:',eh,'ERROR:',eerr)
    print('EXTERNAL HISTORY FUNCTIONS:',ext_names[:100])
    for k,v in ext_funcs.items():
        print('\nEXTERNAL FUNCTION:',k)
        for x in v[:3]:print(x['body'][:6000])
    print('\nEXTERNAL HISTORY ENDPOINTS:',ext_endpoints[:100])
    technical=sum([1 if pre_http!=200 else 0,1 if lr['http']!=200 or lr['error'] or lr['overflow'] else 0,1 if dr['http']!=200 or dr['error'] or dr['overflow'] else 0,1 if eh!=200 or eerr else 0])
    contract_signal=bool(history_do or call_hits or ext_names or ext_endpoints)
    out={'step':'STEP 17-21-C-16-8-T-110-S215','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','anchor':{'ordinance_name':TARGET,'ordin_seq':ORDIN_SEQ,'gubun':'ELIS'},'preflight':{'http':pre_http,'error':pre_err},'list_response':{'http':lr['http'],'bytes':len(lr['body']),'error':lr['error']},'detail_request':{'method':'POST','url':DETAIL,'params':detail_params},'detail_response':{'http':dr['http'],'bytes':len(dr['body']),'encoding':dr['encoding'],'error':dr['error'],'overflow':dr['overflow']},'detail_history_endpoint_hints':history_do,'detail_history_calls':call_hits,'detail_hidden_identity':hidden,'detail_inline_history_functions':inline_funcs,'external_ordin_js':{'http':eh,'error':eerr,'history_function_names':ext_names,'history_functions':ext_funcs,'history_endpoints':ext_endpoints},'summary':{'history_contract_signal_observed':contract_signal,'history_contract_qualified':False,'technical_unknown_count':technical,'semantic_state':'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_HISTORY_CONTRACT_FORENSIC_CAPTURED' if technical==0 and contract_signal else 'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_HISTORY_CONTRACT_FORENSIC_UNRESOLVED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'preflight 200':pre_http==200,'list 200':lr['http']==200,'detail 200':dr['http']==200,'external js 200':eh==200,'technical unknown zero':technical==0,'history contract signal observed':contract_signal,'history not prematurely qualified':not out['summary']['history_contract_qualified'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S215 ordinance history contract forensic failed')
if __name__=='__main__':main()
