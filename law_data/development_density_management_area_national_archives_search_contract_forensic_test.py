# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_search_contract_forensic.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotal.do'
UA='Mozilla/5.0'
MAX=12*1024*1024


def fetch():
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    try:
        r=s.get(URL,timeout=25,stream=True,allow_redirects=True); b=bytearray();ov=False
        try:
            for c in r.iter_content(65536):
                if not c: continue
                if len(b)+len(c)>MAX: ov=True; break
                b.extend(c)
        finally:r.close()
        return s,{'state':'HTTP_RESPONSE_CAPTURED' if not ov else 'TECHNICAL_REQUEST_UNKNOWN','http':r.status_code,'url':str(r.url),'body':bytes(b),'error':'RESPONSE_SIZE_LIMIT_EXCEEDED' if ov else None}
    except requests.RequestException as e:
        return s,{'state':'TECHNICAL_REQUEST_UNKNOWN','http':None,'url':URL,'body':b'','error':f'{type(e).__name__}: {e}'}

def dec(b):
    for enc in ('utf-8','euc-kr','cp949'):
        try:return b.decode(enc),enc
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def attrs(tag):
    out={}
    for m in re.finditer(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S):out[m.group(1).lower()]=html.unescape(m.group(3))
    return out

def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def main():
    print('='*60);print('NATIONAL ARCHIVES SEARCH CONTRACT FORENSIC - S189');print('='*60)
    print('Search execution: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    s,r=fetch(); text,encoding=dec(r['body'])
    forms=[]
    for fm in re.finditer(r'<form\b([^>]*)>([\s\S]*?)</form>',text,re.I):
        fa=attrs(fm.group(1)); body=fm.group(2); controls=[]
        for im in re.finditer(r'<(?:input|select|textarea)\b([^>]*)>',body,re.I):
            a=attrs(im.group(1));
            if a.get('name') or a.get('id'):controls.append({'name':a.get('name'),'id':a.get('id'),'type':a.get('type'),'value':a.get('value')})
        action=urljoin(r['url'],fa.get('action','')) if fa.get('action') else r['url']
        forms.append({'name':fa.get('name'),'id':fa.get('id'),'method':fa.get('method','GET').upper(),'action_raw':fa.get('action',''),'action_resolved':action,'official_host':(urlparse(action).hostname or '').endswith('archives.go.kr'),'controls':controls[:100]})
    scripts=[]
    for sm in re.finditer(r'<script\b([^>]*)>',text,re.I):
        a=attrs(sm.group(1)); src=a.get('src')
        if src:scripts.append(urljoin(r['url'],src))
    search_markers=[]
    for needle in ['searchTotal.do','상세검색','검색어','생산기관','생산연도','원문서비스']:
        if needle in text:search_markers.append(needle)
    candidate_forms=[f for f in forms if any((c.get('name') or '').lower() in {'keyword','query','searchword','searchtext','searchkeyword','searchkey'} for c in f['controls']) or 'search' in (f.get('action_raw') or '').lower() or 'search' in (f.get('id') or '').lower()]
    out={'step':'STEP 17-21-C-16-8-T-85-S189','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','endpoint':URL,'response':{'state':r['state'],'http':r['http'],'final_url':r['url'],'byte_length':len(r['body']),'encoding':encoding,'error':r['error']},'forms':forms,'candidate_search_forms':candidate_forms,'script_srcs':scripts,'search_markers':search_markers,'summary':{'form_count':len(forms),'candidate_search_form_count':len(candidate_forms),'technical_unknown_count':1 if r['state']=='TECHNICAL_REQUEST_UNKNOWN' else 0,'semantic_state':'NATIONAL_ARCHIVES_SEARCH_CONTRACT_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'search_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('HTTP:',r['http'],'| BYTES:',len(r['body']),'| ENCODING:',encoding)
    print('FORMS:',len(forms),'| CANDIDATE_SEARCH_FORMS:',len(candidate_forms))
    for f in forms[:10]:
        print('  FORM:',{'name':f['name'],'id':f['id'],'method':f['method'],'action_raw':f['action_raw'],'action_resolved':f['action_resolved'],'official_host':f['official_host']})
        print('    CONTROLS:',f['controls'][:40])
    print('SEARCH_MARKERS:',search_markers)
    print('SCRIPT_SRCS:',scripts[:20])
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'http 200':r['http']==200,'technical unknown zero':out['summary']['technical_unknown_count']==0,'search execution disabled':not out['search_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S189 National Archives search contract forensic failed')
if __name__=='__main__':main()
