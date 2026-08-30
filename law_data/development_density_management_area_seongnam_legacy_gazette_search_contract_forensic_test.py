# -*- coding: utf-8 -*-
"""S84: forensic recovery of Seongnam legacy gazette search/pagination/detail contract.

Targets only the qualified LEGACY_LOCAL_GAZETTE endpoint /bbs010308 from S83.
Discovers forms, control names/options, pagination parameters, and row-local
navigation evidence using bounded official requests. No UQQ700 legal inference,
attachment download, state mutation, negative evidence, or SITE/runtime
promotion is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_legacy_gazette_search_contract_forensic.json"

BASE_URL = "https://www.seongnam.go.kr/bbs010308"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 6
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

FORM_RE = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
CONTROL_RE = re.compile(r"<(input|select|textarea)\b(?P<attrs>[^>]*)>(?P<body>.*?)</(?:select|textarea)>|<input\b(?P<inputattrs>[^>]*)/?>", re.I | re.S)
OPTION_RE = re.compile(r"<option\b(?P<attrs>[^>]*)>(?P<body>.*?)</option>", re.I | re.S)
LINK_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
NUM_RE = re.compile(r"\d{3,}")


def attrs(raw):
    out={}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session, url, counter, params=None):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError('request budget exceeded')
    counter[0]+=1
    r=session.get(url,params=params,timeout=TIMEOUT,allow_redirects=True)
    return {'http_status':r.status_code,'request_url':str(r.request.url),'final_url':str(r.url),'final_host':(urlparse(str(r.url)).hostname or '').lower(),'text':r.text}


def inspect(text, base_url):
    forms=[]
    for fm in FORM_RE.finditer(text or ''):
        fa=attrs(fm.group('attrs')); body=fm.group('body'); controls=[]; selects=[]
        # inputs
        for im in re.finditer(r"<input\b(?P<attrs>[^>]*)/?>",body,re.I|re.S):
            ia=attrs(im.group('attrs')); controls.append({'tag':'input','name':ia.get('name',''),'type':ia.get('type',''),'value':ia.get('value','')})
        for sm in re.finditer(r"<select\b(?P<attrs>[^>]*)>(?P<body>.*?)</select>",body,re.I|re.S):
            sa=attrs(sm.group('attrs')); opts=[]
            for om in OPTION_RE.finditer(sm.group('body')):
                oa=attrs(om.group('attrs')); opts.append({'value':oa.get('value',''),'label':clean(om.group('body')),'selected':'selected' in oa})
            controls.append({'tag':'select','name':sa.get('name',''),'options':opts}); selects.append({'name':sa.get('name',''),'options':opts})
        action=urljoin(base_url,fa.get('action',''))
        forms.append({'method':fa.get('method','GET').upper(),'action_url':action,'controls':controls,'control_names':sorted({c.get('name','') for c in controls if c.get('name')}),'selects':selects})
    links=[]; page_param_hints=[]; nav_attr_samples=[]
    for lm in LINK_RE.finditer(text or ''):
        la=attrs(lm.group('attrs')); href=la.get('href',''); onclick=la.get('onclick',''); label=clean(lm.group('body'))
        resolved=urljoin(base_url,href) if href else ''
        combined=(href+' '+onclick)
        if any(x in combined.lower() for x in ['curpage','page=','pageindex','page_no','pageno','f_view','view(','detail']):
            nav_attr_samples.append({'href':resolved,'onclick':onclick,'text':label[:160]})
        if href:
            qs=parse_qs(urlparse(resolved).query)
            for k in qs:
                if 'page' in k.lower() or 'cur' in k.lower(): page_param_hints.append(k)
        if len(nav_attr_samples)>=50: break
    years=sorted({int(y) for y in YEAR_RE.findall(clean(text))})
    numeric_hints=NUM_RE.findall(' '.join((x.get('onclick','')+' '+x.get('href','')) for x in nav_attr_samples))
    return {'forms':forms,'navigation_samples':nav_attr_samples,'page_parameter_hints':sorted(set(page_param_hints)),'observed_years':years,'numeric_navigation_hints':list(dict.fromkeys(numeric_hints))[:50]}


def main():
    print('='*60); print('SEONGNAM LEGACY GAZETTE SEARCH CONTRACT FORENSIC - S84'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    counter=[0]
    base=fetch(s,BASE_URL,counter); ins=inspect(base['text'],base['final_url'])
    print('BASE:',{'http':base['http_status'],'forms':len(ins['forms']),'nav_samples':len(ins['navigation_samples']),'years':ins['observed_years'][:10]})
    print('FORMS:')
    for f in ins['forms']: print({'method':f['method'],'action_url':f['action_url'],'control_names':f['control_names'],'selects':f['selects']})
    print('NAVIGATION SAMPLES:',ins['navigation_samples'][:20])
    print('PAGE PARAMETER HINTS:',ins['page_parameter_hints'])

    # Bounded pagination probes using common curPage contract only when exposed.
    page_records=[]
    candidate_page_param='curPage' if ('curPage' in ins['page_parameter_hints'] or any('curPage' in f['control_names'] for f in ins['forms'])) else None
    if candidate_page_param:
        for p in [2,5]:
            rec=fetch(s,BASE_URL,counter,{candidate_page_param:str(p)})
            pi=inspect(rec['text'],rec['final_url'])
            page_records.append({'page':p,'http_status':rec['http_status'],'official_host':rec['final_host']==OFFICIAL_HOST,'observed_years':pi['observed_years'],'navigation_sample_count':len(pi['navigation_samples']),'numeric_navigation_hints':pi['numeric_navigation_hints'][:20]})
            print('PAGE PROBE:',page_records[-1])

    summary={'request_count':counter[0],'form_count':len(ins['forms']),'page_parameter_hints':ins['page_parameter_hints'],'candidate_page_parameter':candidate_page_param,'base_observed_years':ins['observed_years'],'page_probe_count':len(page_records),'detail_navigation_evidence_discovered':len(ins['navigation_samples'])>0,'search_controls_discovered':any(f['control_names'] for f in ins['forms'])}
    payload={'step':'STEP 17-21-C-16-8-T-35-S84','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'LEGACY_LOCAL_GAZETTE','endpoint':BASE_URL,'base_contract':ins,'page_records':page_records,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'base transport official':base['http_status']==200 and base['final_host']==OFFICIAL_HOST,'request budget respected':counter[0]<=MAX_TOTAL_REQUESTS,'forms inspected':len(ins['forms'])>0,'attachment download disabled':not payload['attachment_body_download_executed'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S84 legacy gazette search contract forensic failed')

if __name__=='__main__': main()
