# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_law_seongnam_urban_planning_ordinance_positive_control.json'
BASE_URL='https://www.law.go.kr/ordinSc.do'
UA='Mozilla/5.0'
TARGET='성남시 도시계획 조례'
MAX=8*1024*1024

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def parse_selected_defaults(text):
    data={}
    fm=re.search(r'<form\b[^>]*(?:id|name)=["\']search["\'][^>]*>([\s\S]*?)</form>',text,re.I)
    if not fm:return data
    body=fm.group(1)
    for im in re.finditer(r'<input\b([^>]*)>',body,re.I):
        a=im.group(1);nm=re.search(r'\bname=["\']([^"\']+)',a,re.I)
        if not nm:continue
        tp=re.search(r'\btype=["\']([^"\']+)',a,re.I); val=re.search(r'\bvalue=["\']([^"\']*)',a,re.I)
        typ=(tp.group(1).lower() if tp else 'text')
        if typ in ('checkbox','radio') and not re.search(r'\bchecked\b',a,re.I):continue
        data[nm.group(1)]=val.group(1) if val else ''
    for sm in re.finditer(r'<select\b([^>]*)>([\s\S]*?)</select>',body,re.I):
        a=sm.group(1);nm=re.search(r'\bname=["\']([^"\']+)',a,re.I)
        if not nm:continue
        chosen=None
        for om in re.finditer(r'<option\b([^>]*)>([\s\S]*?)</option>',sm.group(2),re.I):
            oa=om.group(1);ov=re.search(r'\bvalue=["\']([^"\']*)',oa,re.I)
            v=ov.group(1) if ov else clean(om.group(2))
            if chosen is None:chosen=v
            if re.search(r'\bselected\b',oa,re.I):chosen=v;break
        if chosen is not None:data[nm.group(1)]=chosen
    return data

def extract_rows(text):
    rows=[];seen=set()
    # National Law pages commonly expose ordinance details via fOrdinListView / ordinInfoR links.
    pats=[
        re.compile(r"fOrdinListView\s*\(\s*['\"]?([^,'\")]+)['\"]?\s*(?:,\s*['\"]?([^,'\")]+)['\"]?)?",re.I),
        re.compile(r"ordinInfoR\.do\?[^\"']*(?:ID|id|ordinSeq|ordinId)=([^&\"']+)",re.I),
    ]
    for pat in pats:
        for m in pat.finditer(text):
            ctx=clean(text[max(0,m.start()-1200):min(len(text),m.end()+1800)])
            key=(pat.pattern,m.group(1),ctx[:250])
            if key in seen:continue
            seen.add(key)
            rows.append({'identity':list(m.groups()),'context':ctx[:2600],'target_title_seen':TARGET in ctx,'seongnam_seen':'성남시' in ctx,'urban_planning_seen':'도시계획 조례' in ctx})
    return rows

def main():
    print('='*60);print('NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE POSITIVE CONTROL - S208');print('='*60)
    print('Known positive control:',TARGET);print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        r0=s.get(BASE_URL,timeout=30,allow_redirects=True);b0=r0.content[:MAX];t0,e0=dec(b0);err0=None
    except requests.RequestException as ex:
        r0=None;t0='';e0=None;err0=f'{type(ex).__name__}: {ex}'
    defaults=parse_selected_defaults(t0)
    cases=[
        ('QUERY_PARAM_QUERY',{'query':TARGET}),
        ('QUERY_PARAM_KEYWORD',{'keyword':TARGET}),
        ('QUERY_PARAM_LSNM',{'lsNm':TARGET}),
    ]
    rec=[]
    for name,extra in cases:
        params=dict(defaults);params.update(extra)
        try:
            r=s.get(BASE_URL,params=params,timeout=30,allow_redirects=True);b=r.content[:MAX];t,e=dec(b);err=None
            rows=extract_rows(t);plain=clean(t)
            rr={'case':name,'params':extra,'http':r.status_code,'final_url':str(r.url),'byte_length':len(b),'encoding':e,'target_exact_in_page':TARGET in plain,'seongnam_in_page':'성남시' in plain,'urban_planning_in_page':'도시계획 조례' in plain,'row_count':len(rows),'positive_row_count':sum(x['target_title_seen'] for x in rows),'rows':rows[:30],'error':err}
        except requests.RequestException as ex:
            rr={'case':name,'params':extra,'http':None,'final_url':None,'byte_length':0,'encoding':None,'target_exact_in_page':False,'seongnam_in_page':False,'urban_planning_in_page':False,'row_count':0,'positive_row_count':0,'rows':[],'error':f'{type(ex).__name__}: {ex}'}
        rec.append(rr)
        print(f"CASE: {name} | HTTP: {rr['http']} | BYTES: {rr['byte_length']} | EXACT: {rr['target_exact_in_page']} | ROWS: {rr['row_count']} | POSITIVE_ROWS: {rr['positive_row_count']}")
        for x in rr['rows'][:5]:print('  ROW:',x)
    qualified=[x for x in rec if x['http']==200 and (x['positive_row_count']>0 or x['target_exact_in_page'])]
    best=qualified[0]['case'] if qualified else None
    out={'step':'STEP 17-21-C-16-8-T-104-S208','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY','known_positive_control':TARGET,'base_form_defaults':defaults,'cases':rec,'summary':{'case_count':len(rec),'qualified_positive_control_case_count':len(qualified),'best_positive_control_case':best,'technical_unknown_count':sum(1 for x in rec if x['error'] or x['http']!=200),'semantic_state':'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_POSITIVE_CONTROL_RESOLVED' if qualified else 'NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_POSITIVE_CONTROL_UNRESOLVED','search_contract_qualified':bool(qualified),'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'case exact':len(rec)==3,'technical unknown zero':out['summary']['technical_unknown_count']==0,'positive control resolved':len(qualified)>0,'search contract qualified iff positive':out['summary']['search_contract_qualified']==(len(qualified)>0),'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S208 national law Seongnam urban planning ordinance positive control failed')
if __name__=='__main__':main()
