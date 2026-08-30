# -*- coding: utf-8 -*-
"""S80: probe historical coverage boundary of Seongnam /pm010301 search.

This stage paginates only broad official queries (도시관리계획, 지형도면) far
enough to observe the oldest reachable notice years and stopping behavior. It
must not infer legal absence, download attachments, mutate state, or promote
SITE/runtime conclusions.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_search_coverage_boundary_probe.json"

SEARCH_URL = "https://www.seongnam.go.kr/pm010301"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 42
MAX_PAGES_PER_QUERY = 20
CNT_PER_PAGE = 30
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

QUERY_MATRIX = [
    ("sj", "도시관리계획"),
    ("sj", "지형도면"),
]

TAG_RE = re.compile(r"<[^>]+>", re.S)
NOTICE_RE = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*(\d{4})\s*[-－]\s*\d+\s*호")
VIEW_RE = re.compile(r"f_view\(['\"](\d+)['\"]\)", re.I)


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session, params, counter):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(SEARCH_URL, params=params, timeout=TIMEOUT, allow_redirects=True)
    body = r.content[:MAX_RESPONSE_BYTES]
    text = body.decode(r.encoding or "utf-8", errors="replace")
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": text}


def main():
    print('='*60); print('SEONGNAM NOTICE SEARCH COVERAGE BOUNDARY PROBE - S80'); print('='*60)
    print('Legal negative evidence: DISABLED'); print('Attachment download: DISABLED'); print('State mutation: DISABLED')

    s=requests.Session(); s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ko-KR,ko;q=0.9'})
    counter=[0]; query_summaries=[]; all_years=Counter(); all_ids=set()

    for srch_key, term in QUERY_MATRIX:
        years=Counter(); seen_ids=set(); pages=[]; stop_reason='MAX_PAGES_REACHED'
        previous_page_ids=None
        for page in range(1, MAX_PAGES_PER_QUERY+1):
            params={'curPage':str(page),'cntPerPage':str(CNT_PER_PAGE),'sortType':'1','srchKey':srch_key,'srchText':term}
            rec=fetch(s,params,counter)
            text=clean(rec['text'])
            page_years=[int(y) for y in NOTICE_RE.findall(text)]
            page_ids=VIEW_RE.findall(rec['text'])
            unique_page_ids=list(dict.fromkeys(page_ids))
            for y in page_years: years[str(y)] += 1; all_years[str(y)] += 1
            for did in unique_page_ids: seen_ids.add(did); all_ids.add(did)
            page_rec={'page':page,'http_status':rec['http'],'official_host':rec['host']==OFFICIAL_HOST,'row_id_count':len(unique_page_ids),'notice_year_count':len(page_years),'min_year':min(page_years) if page_years else None,'max_year':max(page_years) if page_years else None,'first_ids':unique_page_ids[:5]}
            pages.append(page_rec)
            print('PAGE:', {'query':term, **page_rec})
            if rec['http'] != 200 or rec['host'] != OFFICIAL_HOST:
                stop_reason='TRANSPORT_OR_HOST_FAILURE'; break
            if len(unique_page_ids) == 0:
                stop_reason='EMPTY_PAGE'; break
            if previous_page_ids is not None and unique_page_ids == previous_page_ids:
                stop_reason='REPEATED_PAGE'; break
            previous_page_ids=unique_page_ids
            if len(unique_page_ids) < CNT_PER_PAGE:
                stop_reason='SHORT_PAGE'; break
        observed_years=sorted(int(k) for k in years)
        qs={'srchKey':srch_key,'query':term,'page_count':len(pages),'stop_reason':stop_reason,'unique_document_id_count':len(seen_ids),'observed_years':observed_years,'oldest_observed_year':min(observed_years) if observed_years else None,'newest_observed_year':max(observed_years) if observed_years else None,'year_counts':dict(sorted(years.items())),'pages':pages}
        query_summaries.append(qs)

    observed_all=sorted(int(k) for k in all_years)
    summary={'query_count':len(query_summaries),'request_count':counter[0],'unique_document_id_count':len(all_ids),'observed_years':observed_all,'oldest_observed_year':min(observed_all) if observed_all else None,'newest_observed_year':max(observed_all) if observed_all else None,'year_counts':dict(sorted(all_years.items())),'historical_coverage_reaches_pre_2020':bool(observed_all and min(observed_all)<2020)}
    payload={'step':'STEP 17-21-C-16-8-T-35-S80','target_name':'개발밀도관리구역','standard_code':'UQQ700','resolution_type':'HYBRID_SPATIAL_NOTICE','source_family':'NOTICE_NUMBER_REVERSE_LOOKUP','query_summaries':query_summaries,'summary':summary,'attachment_body_download_executed':False,'state_mutation_executed':False,'negative_evidence_allowed':False,'site_positive_allowed':False,'site_negative_allowed':False,'runtime_registration_allowed':False,'final_positive_promotion_allowed':False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    vals={'queries executed':len(query_summaries)==len(QUERY_MATRIX),'all sampled transport official':all(p['http_status']==200 and p['official_host'] for q in query_summaries for p in q['pages']),'request budget respected':counter[0]<=MAX_TOTAL_REQUESTS,'attachment download disabled':not payload['attachment_body_download_executed'],'state mutation disabled':not payload['state_mutation_executed'],'negative evidence disabled':not payload['negative_evidence_allowed'],'unsafe promotion leakage zero':not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),'output written':OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]
    for q in query_summaries: print('QUERY SUMMARY:', {k:q[k] for k in ['query','page_count','stop_reason','unique_document_id_count','oldest_observed_year','newest_observed_year','observed_years']})
    print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S80 coverage boundary probe failed')

if __name__=='__main__': main()
