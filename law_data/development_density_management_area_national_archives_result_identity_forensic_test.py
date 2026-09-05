# -*- coding: utf-8 -*-
from __future__ import annotations

import html, json, re
from pathlib import Path
from urllib.parse import urljoin
import requests

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'law_data'/'output'/'development_density_management_area_national_archives_result_identity_forensic.json'
URL='https://www.archives.go.kr/next/newsearch/searchTotalUp.do'
UA='Mozilla/5.0'
QUERY='성남시'
MAX=16*1024*1024

def fetch():
    params={'query_type':'keyword','is_detail':'yes','upside_query':QUERY,'keyword':QUERY,'beforeKeyword':'','afterKeyword':'','doc_type':'','srchinit':'ritem'}
    s=requests.Session();s.headers.update({'User-Agent':UA,'Accept-Language':'ko-KR,ko;q=0.9'})
    r=s.get(URL,params=params,timeout=30,stream=True,allow_redirects=True)
    b=bytearray();ov=False
    try:
        for c in r.iter_content(65536):
            if not c: continue
            if len(b)+len(c)>MAX:ov=True;break
            b.extend(c)
    finally:r.close()
    return r.status_code,str(r.url),bytes(b),ov

def dec(b):
    for e in ('utf-8','euc-kr','cp949'):
        try:return b.decode(e),e
        except UnicodeDecodeError:pass
    return b.decode('utf-8',errors='ignore'),'utf-8-ignore'
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def main():
    print('='*60);print('NATIONAL ARCHIVES RESULT IDENTITY FORENSIC - S191');print('='*60)
    print('Query:',QUERY);print('Detail navigation: DISABLED');print('Negative evidence: DISABLED');print('UQQ700 resolution: UNKNOWN')
    http,final,body,ov=fetch();text,encoding=dec(body)
    contexts=[]
    for m in re.finditer(re.escape(QUERY),text):
        frag=text[max(0,m.start()-900):min(len(text),m.end()+1800)]
        if any(k in frag for k in ['도로명주소 안내도','고령친화도시','노인실태조사','도시림등의 조성']):
            contexts.append(re.sub(r'\s+',' ',frag).strip())
        if len(contexts)>=12:break
    onclicks=[]
    for m in re.finditer(r'onclick\s*=\s*(["\'])(.*?)\1',text,re.I|re.S):
        v=html.unescape(m.group(2));
        if re.search(r'detail|view|record|item|arch|open|go[A-Z_]|fn[A-Z_]',v,re.I):onclicks.append(v[:1500])
        if len(onclicks)>=100:break
    data_attrs=[]
    for m in re.finditer(r'<[^>]+>',text):
        tag=m.group(0)
        if QUERY not in tag and not re.search(r'data-[\w-]+\s*=',tag,re.I):continue
        attrs=dict((k.lower(),html.unescape(v)) for k,_,v in re.findall(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S))
        d={k:v for k,v in attrs.items() if k.startswith('data-') or k in {'id','class','href','onclick','title'}}
        if d:data_attrs.append(d)
        if len(data_attrs)>=100:break
    scripts=[]
    for m in re.finditer(r'function\s+([A-Za-z0-9_$]+)\s*\([^)]*\)\s*\{[\s\S]{0,3000}?\}',text,re.I):
        frag=m.group(0)
        if re.search(r'detail|record|view|open|item|arch',frag,re.I):scripts.append(re.sub(r'\s+',' ',frag).strip()[:3000])
        if len(scripts)>=30:break
    result_titles=[]
    for m in re.finditer(r'<a\b([^>]*)>([\s\S]*?)</a>',text,re.I):
        label=clean(m.group(2))
        if QUERY in label and len(label)>2 and label not in result_titles:result_titles.append(label[:500])
        if len(result_titles)>=30:break
    out={'step':'STEP 17-21-C-16-8-T-87-S191','target_name':'개발밀도관리구역','standard_code':'UQQ700','source_family':'NATIONAL_ARCHIVES_OF_KOREA','query':QUERY,'response':{'http':http,'final_url':final,'byte_length':len(body),'encoding':encoding,'overflow':ov},'result_titles':result_titles,'result_contexts':contexts,'onclick_candidates':onclicks,'data_attribute_candidates':data_attrs,'script_candidates':scripts,'summary':{'result_title_count':len(result_titles),'context_count':len(contexts),'onclick_candidate_count':len(onclicks),'data_attribute_candidate_count':len(data_attrs),'script_candidate_count':len(scripts),'semantic_state':'NATIONAL_ARCHIVES_RESULT_IDENTITY_FORENSIC_CAPTURED','negative_evidence_allowed':False,'legal_absence_inference_allowed':False,'uqq700_final_resolution':'UNKNOWN'},'detail_navigation_executed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('HTTP:',http,'| BYTES:',len(body),'| ENCODING:',encoding)
    print('RESULT_TITLES:',len(result_titles));[print('  TITLE:',x) for x in result_titles[:20]]
    print('ONCLICK_CANDIDATES:',len(onclicks));[print('  ONCLICK:',x) for x in onclicks[:20]]
    print('DATA_ATTRIBUTE_CANDIDATES:',len(data_attrs));[print('  DATA:',x) for x in data_attrs[:20]]
    print('SCRIPT_CANDIDATES:',len(scripts));[print('  SCRIPT:',x) for x in scripts[:10]]
    print('CONTEXTS:',len(contexts));[print('  CONTEXT:',x[:2500]) for x in contexts[:6]]
    print('\nSUMMARY');[print(f'{k}: {v}') for k,v in out['summary'].items()];print('Output:',OUT)
    checks={'http 200':http==200,'overflow false':not ov,'result title observed':len(result_titles)>0,'detail navigation disabled':not out['detail_navigation_executed'],'negative evidence disabled':not out['summary']['negative_evidence_allowed'],'legal absence inference disabled':not out['summary']['legal_absence_inference_allowed'],'unsafe promotion leakage zero':not any(out[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),'final resolution unknown':out['summary']['uqq700_final_resolution']=='UNKNOWN','output written':OUT.exists() and OUT.stat().st_size>0}
    print('\nVALIDATION');[print(f'{k}: {v}') for k,v in checks.items()];print('all_pass:',all(checks.values()))
    if not all(checks.values()):raise AssertionError('S191 National Archives result identity forensic failed')
if __name__=='__main__':main()
