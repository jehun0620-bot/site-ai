# -*- coding: utf-8 -*-
"""S82: forensic probe for pre-2010 boundary of Seongnam notice search.

Determines whether /pm010301 broad-query pagination truly ends around 2010 and
collects bounded clues for any legacy/predecessor notice endpoints present in
page HTML or navigation. No legal negative evidence, attachment download, state
mutation, or SITE/runtime promotion is allowed.
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
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_pre2010_boundary_forensic.json"

SEARCH_URL = "https://www.seongnam.go.kr/pm010301"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 12
CNT_PER_PAGE = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

PROBES = [
    ("sj", "도시관리계획", 9),
    ("sj", "도시관리계획", 10),
    ("sj", "지형도면", 7),
    ("sj", "지형도면", 8),
]

TAG_RE = re.compile(r"<[^>]+>", re.S)
NOTICE_RE = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*(\d{4})\s*[-－]\s*\d+\s*호")
VIEW_RE = re.compile(r"f_view\(['\"](\d+)['\"]\)", re.I)
LINK_RE = re.compile(r"<a\b[^>]*href\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))", re.I)
LEGACY_HINT_RE = re.compile(r"(?:고시|공고|시보|gazette|notice|bbs|archive|legacy|old)", re.I)


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session, params, counter):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(SEARCH_URL, params=params, timeout=TIMEOUT, allow_redirects=True)
    return {"http":r.status_code,"url":str(r.url),"host":(urlparse(str(r.url)).hostname or "").lower(),"text":r.text}


def legacy_hints(text: str):
    out=[]
    for m in LINK_RE.finditer(text or ""):
        href=m.group(1) or m.group(2) or m.group(3) or ""
        resolved=urljoin(SEARCH_URL,html.unescape(href))
        if LEGACY_HINT_RE.search(resolved):
            if resolved not in out: out.append(resolved)
        if len(out)>=50: break
    return out


def main():
    print('='*60); print('SEONGNAM NOTICE PRE-2010 BOUNDARY FORENSIC - S82'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    counter=[0]; records=[]; hints=[]
    for key,term,page in PROBES:
        params={'curPage':str(page),'cntPerPage':str(CNT_PER_PAGE),'sortType':'1','srchKey':key,'srchText':term}
        rec=fetch(s,params,counter)
        years=[int(y) for y in NOTICE_RE.findall(clean(rec['text']))]
        ids=list(dict.fromkeys(VIEW_RE.findall(rec['text'])))
        lh=legacy_hints(rec['text'])
        for h in lh:
            if h not in hints: hints.append(h)
        item={'query':term,'page':page,'http_status':rec['http'],'official_host':rec['host']==OFFICIAL_HOST,'row_id_count':len(ids),'notice_year_count':len(years),'min_year':min(years) if years else None,'max_year':max(years) if years else None,'first_ids':ids[:8]}
        records.append(item); print('PROBE:',item)
    by_query={}
    for term in sorted({r['query'] for r in records}):
        rs=[r for r in records if r['query']==term]
        rs.sort(key=lambda x:x['page'])
        by_query[term]={'last_nonempty_page':max((r['page'] for r in rs if r['row_id_count']>0),default=None),'first_empty_page':min((r['page'] for r in rs if r['row_id_count']==0),default=None),'oldest_observed_year':min((r['min_year'] for r in rs if r['min_year'] is not None),default=None),'records':rs}
    summary={'request_count':counter[0],'query_boundaries':by_query,'legacy_hint_count':len(hints),'legacy_hints':hints[:50],'pre2010_notice_year_observed':any((r['min_year'] or 9999)<2010 for r in records)}
    payload={'step':'STEP 17-21-C-16-8-T-35-S82','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'NOTICE_NUMBER_REVERSE_LOOKUP','records':records,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={'all probe transport official':all(r['http_status']==200 and r['official_host'] for r in records),'request budget respected':counter[0]<=MAX_TOTAL_REQUESTS,'attachment download disabled':not payload['attachment_body_download_executed'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); print('pre2010_notice_year_observed:',summary['pre2010_notice_year_observed']); print('legacy_hint_count:',summary['legacy_hint_count']); print('legacy_hints:',summary['legacy_hints'][:20]);
    for k,v in by_query.items(): print('BOUNDARY:',k,{x:v[x] for x in ['last_nonempty_page','first_empty_page','oldest_observed_year']})
    print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S82 pre-2010 boundary forensic failed')

if __name__=='__main__': main()
