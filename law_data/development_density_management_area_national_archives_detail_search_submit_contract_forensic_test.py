# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
import requests
from urllib.parse import urljoin

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_detail_search_submit_contract_forensic.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'; MAX=4*1024*1024

FUNC_NAMES=['detailSearch','detailSearchForm','fn_detailSearch','goDetailSearch','uniDetailSearch','searchDetail','setOrg','orgSearch']


def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'

def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def fetch():
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    r=s.get(URL,params={'query_type':'keyword','is_detail':'yes','upside_query':'성남시','keyword':'성남시','srchinit':'ritem'},timeout=30,stream=True)
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c:continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    text,enc=dec(bytes(b));return r.status_code,str(r.url),text,len(b),enc,ov

def form_block(text):
    m=re.search(r'<form\b[^>]*(?:name=["\']detailSearchForm["\']|id=["\']detailSearchForm["\'])[^>]*>([\s\S]*?)</form>',text,re.I)
    return m.group(0) if m else ''

def controls(form):
    out=[]
    for m in re.finditer(r'<(input|select|textarea)\b([^>]*)>',form,re.I):
        tag=m.group(1).lower(); attrs=m.group(2)
        def a(n):
            x=re.search(r'\b'+re.escape(n)+r'\s*=\s*["\']([^"\']*)["\']',attrs,re.I)
            return html.unescape(x.group(1)) if x else ''
        name=a('name'); ident=a('id'); typ=a('type') if tag=='input' else tag; value=a('value')
        if not value and tag=='select':
            tail=form[m.end():]
            sm=re.search(r'<option\b[^>]*selected[^>]*value=["\']([^"\']*)["\']',tail,re.I)
            if sm:value=html.unescape(sm.group(1))
        checked=bool(re.search(r'\bchecked\b',attrs,re.I)); disabled=bool(re.search(r'\bdisabled\b',attrs,re.I))
        out.append({'tag':tag,'name':name,'id':ident,'type':typ,'value':value,'checked':checked,'disabled':disabled,'attrs':clean(attrs)[:500]})
    return out

def function_bodies(text):
    out=[]
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{',text):
        name=m.group(1)
        if not any(k.lower() in name.lower() for k in ['detail','search','org','kikwan']): continue
        start=m.start(); i=m.end(); depth=1; quote=None; esc=False
        while i<len(text) and depth:
            ch=text[i]
            if quote:
                if esc:esc=False
                elif ch=='\\':esc=True
                elif ch==quote:quote=None
            else:
                if ch in ('"',"'",'`'):quote=ch
                elif ch=='{':depth+=1
                elif ch=='}':depth-=1
            i+=1
        out.append({'name':name,'args':m.group(2),'body':re.sub(r'\s+',' ',text[start:i]).strip()[:12000]})
    return out

def main():
    print('='*60);print('NATIONAL ARCHIVES DETAIL SEARCH SUBMIT CONTRACT FORENSIC - S199');print('='*60)
    print('Search execution: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    http,final_url,text,n,enc,ov=fetch();form=form_block(text);ctrls=controls(form);funcs=function_bodies(text)
    fm=re.search(r'<form\b([^>]*)',form,re.I)
    attrs=fm.group(1) if fm else ''
    def attr(name):
        m=re.search(r'\b'+name+r'\s*=\s*["\']([^"\']*)["\']',attrs,re.I);return html.unescape(m.group(1)) if m else ''
    action=attr('action');method=attr('method');resolved=urljoin(final_url,action) if action else ''
    endpoint_literals=sorted(set(re.findall(r'["\'](/next/[^"\']+\.(?:do|jsp)(?:\?[^"\']*)?)["\']',text,re.I)))
    assignments=[]
    for f in funcs:
        for m in re.finditer(r'(?:document\.)?detailSearchForm\.([A-Za-z_][\w]*)\.value\s*=\s*([^;]+)',f['body']):
            assignments.append({'function':f['name'],'field':m.group(1),'expr':m.group(2)[:300]})
        for m in re.finditer(r'\$\(["\'](?:#|\[name=)([^"\']+)["\']\)\.val\(([^)]*)\)',f['body']):
            assignments.append({'function':f['name'],'field_like':m.group(1),'expr':m.group(2)[:300]})
    submit_markers=[]
    for f in funcs:
        if 'submit(' in f['body'] or '.action' in f['body'] or 'uniDetailSearch' in f['body']:
            submit_markers.append(f)
    print('HTTP:',http,'| BYTES:',n,'| ENCODING:',enc,'| OVERFLOW:',ov)
    print('FORM METHOD:',method,'| ACTION:',action,'| RESOLVED:',resolved)
    print('\nCONTROLS')
    for c in ctrls: print(c)
    print('\nSUBMIT FUNCTIONS')
    for f in submit_markers: print('FUNCTION',f['name'],':',f['body'])
    print('\nASSIGNMENTS:',assignments)
    print('ENDPOINT_LITERALS:',endpoint_literals)
    out={'step':'STEP 17-21-C-16-8-T-95-S199','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','http':http,'final_url':final_url,'byte_length':n,'encoding':enc,'overflow':ov,'detail_form':{'method':method,'action':action,'resolved_action':resolved,'controls':ctrls},'functions':funcs,'submit_functions':submit_markers,'assignments':assignments,'endpoint_literals':endpoint_literals,'summary':{'form_found':bool(form),'control_count':len(ctrls),'function_count':len(funcs),'submit_function_count':len(submit_markers),'semantic_state':'NATIONAL_ARCHIVES_DETAIL_SEARCH_SUBMIT_CONTRACT_FORENSIC_CAPTURED','search_execution_enabled':False,'negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    names={c['name'] for c in ctrls}
    checks={'http 200':http==200,'overflow false':not ov,'detail form found':bool(form),'detail action observed':'uniDetailSearch.do' in resolved,'keyword controls observed':bool({'keyword','detailOneKeyword','detailMatchKeyword'} & names),'organization controls observed':bool({'org_nm','org_nm_fst','orgName','kikwancode','kikwanname'} & names),'search execution disabled':not out['summary']['search_execution_enabled'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S199 National Archives detail-search submit contract forensic failed')
if __name__=='__main__':main()
