# -*- coding: utf-8 -*-
"""S83: qualify pre-2010 Seongnam legacy source-family entry endpoints.

Uses the official legacy hints surfaced by S82 and performs a bounded endpoint
qualification pass. The purpose is to decide which legacy local notice/gazette
families are technically reachable and expose search/navigation structure that
could support pre-2010 reverse discovery. No UQQ700 legal inference, attachment
download, cumulative state mutation, or SITE/runtime promotion is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_pre2010_boundary_forensic.json"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_pre2010_legacy_source_family_entry_qualification.json"

TIMEOUT = 20
MAX_TOTAL_REQUESTS = 8
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
OFFICIAL_HOSTS = {"www.seongnam.go.kr", "seongnam.go.kr"}

# Prioritize the official Seongnam gazette/notice-style hints observed in S82.
PREFERRED_PATHS = [
    "/bbs010308",  # municipal gazette / 시보 family already known in project
    "/bbs010101",
    "/bbs010402",
    "/bbs010403",
]

FORM_RE = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<(?:input|select|textarea)\b(?P<attrs>[^>]*)>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
LINK_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>", re.S)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
SEARCH_HINT_RE = re.compile(r"(?:search|srch|query|keyword|subject|title|content|제목|내용|검색)", re.I)
DETAIL_HINT_RE = re.compile(r"(?:view|detail|read|bbs|pst|seq|idx|no)[^\s'\"]*", re.I)


def attrs(raw: str) -> dict[str, str]:
    out={}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session, url, counter):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r=session.get(url, timeout=TIMEOUT, allow_redirects=True)
    body=r.content[:MAX_RESPONSE_BYTES]
    text=body.decode(r.encoding or "utf-8", errors="replace")
    return {"http":r.status_code,"request_url":url,"final_url":str(r.url),"host":(urlparse(str(r.url)).hostname or "").lower(),"text":text,"body_bytes":len(body)}


def inspect_page(rec):
    text=rec['text']; page_text=clean(text)
    forms=[]
    for fm in FORM_RE.finditer(text):
        fa=attrs(fm.group('attrs')); controls=[]
        for im in INPUT_RE.finditer(fm.group('body')):
            ia=attrs(im.group('attrs')); name=ia.get('name','')
            if name: controls.append(name)
        action=urljoin(rec['final_url'],fa.get('action',''))
        forms.append({'method':fa.get('method','GET').upper(),'action_url':action,'control_names':sorted(set(controls)),'search_like':bool(SEARCH_HINT_RE.search(' '.join(controls)+' '+action))})
    links=[]
    for lm in LINK_RE.finditer(text):
        la=attrs(lm.group('attrs')); href=la.get('href',''); onclick=la.get('onclick','')
        if href or onclick:
            value=(href+' '+onclick).strip()
            if DETAIL_HINT_RE.search(value):
                links.append({'href':urljoin(rec['final_url'],href) if href else '', 'onclick':onclick, 'text':clean(lm.group('body'))[:180]})
            if len(links)>=30: break
    years=sorted({int(y) for y in YEAR_RE.findall(page_text)})
    return {'title_hint':page_text[:240],'form_count':len(forms),'search_like_forms':[f for f in forms if f['search_like']],'detail_navigation_hints':links,'observed_years':years,'pre2010_year_visible':any(y<2010 for y in years)}


def main():
    print('='*60); print('SEONGNAM PRE-2010 LEGACY SOURCE FAMILY ENTRY QUALIFICATION - S83'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    if not INPUT_PATH.exists(): raise FileNotFoundError(INPUT_PATH)
    s82=json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    hints=s82.get('summary',{}).get('legacy_hints') or []
    selected=[]
    for path in PREFERRED_PATHS:
        for h in hints:
            u=urlparse(h)
            if u.path.rstrip('/')==path:
                selected.append(h); break
    # Always retain bbs010308 if S82 surfaced it.
    selected=list(dict.fromkeys(selected))[:MAX_TOTAL_REQUESTS]
    if not selected:
        raise AssertionError('no official legacy endpoints selected from S82')

    session=requests.Session(); session.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    counter=[0]; records=[]
    for url in selected:
        rec=fetch(session,url,counter); ins=inspect_page(rec)
        official=rec['host'] in OFFICIAL_HOSTS
        technically_qualified=rec['http']==200 and official and (len(ins['search_like_forms'])>0 or len(ins['detail_navigation_hints'])>0)
        family='LEGACY_LOCAL_GAZETTE' if '/bbs010308' in rec['final_url'] else 'LEGACY_LOCAL_NOTICE'
        item={'family':family,'input_url':url,'http_status':rec['http'],'official_host':official,'final_url':rec['final_url'],'body_bytes_read':rec['body_bytes'],**ins,'technically_qualified':technically_qualified}
        records.append(item)
        print('ENDPOINT:',{'family':family,'url':url,'http':rec['http'],'qualified':technically_qualified,'search_forms':len(ins['search_like_forms']),'detail_hints':len(ins['detail_navigation_hints']),'pre2010_visible':ins['pre2010_year_visible']})

    qualified=[r for r in records if r['technically_qualified']]
    gazette=[r for r in qualified if r['family']=='LEGACY_LOCAL_GAZETTE']
    summary={'input_hint_count':len(hints),'selected_endpoint_count':len(selected),'request_count':counter[0],'qualified_endpoint_count':len(qualified),'qualified_gazette_endpoint_count':len(gazette),'any_pre2010_year_visible_on_entry':any(r['pre2010_year_visible'] for r in records),'next_stage_source_family_ready':len(gazette)>0}
    payload={'step':'STEP 17-21-C-16-8-T-35-S83','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_scope':'PRE2010_LEGACY_SOURCE_FAMILY_ENTRY','records':records,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'selected endpoints inspected':len(records)==len(selected) and len(records)>0,'all selected transport official':all(r['http_status']==200 and r['official_host'] for r in records),'request budget respected':counter[0]<=MAX_TOTAL_REQUESTS,'attachment download disabled':not payload['attachment_body_download_executed'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]
    print('QUALIFIED:',[(r['family'],r['final_url'],len(r['search_like_forms']),len(r['detail_navigation_hints'])) for r in qualified])
    print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S83 legacy source entry qualification failed')

if __name__=='__main__': main()
