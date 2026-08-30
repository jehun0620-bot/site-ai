# -*- coding: utf-8 -*-
"""S77: collect canonical Seongnam notice candidates through validated reverse lookup.

Uses the validated GET search contract and f_view(document_id) -> /pm010301/{id}
contract. Search hits are only candidates. No attachment download, cumulative-state
mutation, legal negative evidence, or SITE/runtime promotion is allowed.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_reverse_lookup_candidate_collection.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NOTICE_NUMBER_REVERSE_LOOKUP"
SEARCH_URL = "https://www.seongnam.go.kr/pm010301"
DETAIL_PREFIX = "https://www.seongnam.go.kr/pm010301/"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 40
MAX_PAGES_PER_QUERY = 3
CNT_PER_PAGE = 30
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

QUERY_MATRIX = [
    ("sj", "개발밀도관리구역"),
    ("cn", "개발밀도관리구역"),
    ("sj", "개발밀도"),
    ("cn", "개발밀도"),
    ("sj", "도시관리계획"),
    ("cn", "도시관리계획"),
    ("sj", "지형도면"),
    ("cn", "지형도면"),
]

TAG_RE = re.compile(r"<[^>]+>", re.S)
NOTICE_NUMBER_RE = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*\d{4}\s*[-－]\s*\d+\s*호")
VIEW_RE = re.compile(r"f_view\(['\"](\d+)['\"]\)", re.I)
ANCHOR_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
ROW_RE = re.compile(r"<(tr|li)\b[^>]*>.*?</\1>", re.I | re.S)


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session: requests.Session, params: dict, counter: list[int]) -> dict:
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(SEARCH_URL, params=params, timeout=TIMEOUT, allow_redirects=True)
    body = r.content[:MAX_RESPONSE_BYTES]
    text = body.decode(r.encoding or "utf-8", errors="replace")
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": text}


def extract_rows(text: str) -> list[dict]:
    rows = []
    for rm in ROW_RE.finditer(text or ""):
        block = rm.group(0)
        row_text = clean(block)
        notice_numbers = NOTICE_NUMBER_RE.findall(row_text)
        ids = VIEW_RE.findall(block)
        if not notice_numbers or not ids:
            continue
        title = ""
        onclick_id = ""
        for am in ANCHOR_RE.finditer(block):
            aa = attrs(am.group("attrs"))
            onclick = aa.get("onclick", "")
            vm = VIEW_RE.search(onclick)
            if vm:
                onclick_id = vm.group(1)
                title = clean(am.group("body"))
                break
        document_id = onclick_id or ids[0]
        notice_number = notice_numbers[0]
        rows.append({
            "document_id": document_id,
            "detail_url": DETAIL_PREFIX + document_id,
            "notice_number": notice_number,
            "title": title,
            "row_text": row_text[:1800],
        })
    if rows:
        return rows
    # Broad fallback: pair each f_view anchor with nearest notice-number text window.
    for am in ANCHOR_RE.finditer(text or ""):
        aa = attrs(am.group("attrs"))
        vm = VIEW_RE.search(aa.get("onclick", ""))
        if not vm:
            continue
        lo=max(0,am.start()-1400); hi=min(len(text),am.end()+1400); window=text[lo:hi]
        nums=NOTICE_NUMBER_RE.findall(clean(window))
        if not nums:
            continue
        did=vm.group(1)
        rows.append({"document_id":did,"detail_url":DETAIL_PREFIX+did,"notice_number":nums[0],"title":clean(am.group("body")),"row_text":clean(window)[:1800]})
    return rows


def main():
    print('='*60); print('SEONGNAM NOTICE REVERSE LOOKUP CANDIDATE COLLECTION - S77'); print('='*60)
    print('Search hit = candidate only'); print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')

    s=requests.Session(); s.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ko-KR,ko;q=0.9"})
    counter=[0]; provenance=defaultdict(list); canonical={}; query_records=[]

    for srch_key, term in QUERY_MATRIX:
        seen_this_query=set()
        for page in range(1,MAX_PAGES_PER_QUERY+1):
            params={"curPage":str(page),"cntPerPage":str(CNT_PER_PAGE),"sortType":"1","srchKey":srch_key,"srchText":term}
            rec=fetch(s,params,counter)
            rows=extract_rows(rec['text']) if rec['http']==200 and rec['host']==OFFICIAL_HOST else []
            new_ids=[]
            for row in rows:
                did=row['document_id']
                if did not in canonical:
                    canonical[did]={k:row[k] for k in ['document_id','detail_url','notice_number','title']}
                provenance[did].append({"srchKey":srch_key,"query":term,"page":page,"request_url":rec['url']})
                if did not in seen_this_query:
                    new_ids.append(did); seen_this_query.add(did)
            query_records.append({"srchKey":srch_key,"query":term,"page":page,"http_status":rec['http'],"official_host":rec['host']==OFFICIAL_HOST,"row_count":len(rows),"new_document_ids":new_ids})
            print('QUERY:', {'srchKey':srch_key,'query':term,'page':page,'http':rec['http'],'rows':len(rows),'new_ids':new_ids[:12]})
            if len(rows) < CNT_PER_PAGE:
                break

    candidates=[]
    for did,row in canonical.items():
        item=dict(row)
        item['provenance']=provenance[did]
        joined=(row.get('title','')+' '+row.get('notice_number','')).strip()
        item['direct_target_in_link_local_evidence']=bool(re.search(r"개발\s*밀도\s*관리\s*구역",joined))
        item['related_term_in_link_local_evidence']='개발밀도' in joined.replace(' ','')
        item['candidate_class']='DIRECT_LINK_LOCAL_CANDIDATE' if item['direct_target_in_link_local_evidence'] else ('RELATED_LINK_LOCAL_CANDIDATE' if item['related_term_in_link_local_evidence'] else 'DISCOVERY_CONTEXT_CANDIDATE')
        candidates.append(item)
    candidates.sort(key=lambda x:int(x['document_id']),reverse=True)

    direct=[c for c in candidates if c['candidate_class']=='DIRECT_LINK_LOCAL_CANDIDATE']
    related=[c for c in candidates if c['candidate_class']=='RELATED_LINK_LOCAL_CANDIDATE']
    summary={"query_page_request_count":counter[0],"canonical_candidate_count":len(candidates),"direct_link_local_candidate_count":len(direct),"related_link_local_candidate_count":len(related),"discovery_context_candidate_count":len(candidates)-len(direct)-len(related)}
    payload={"step":"STEP 17-21-C-16-8-T-35-S77","target_name":TARGET_NAME,"standard_code":STANDARD_CODE,"resolution_type":RESOLUTION_TYPE,"source_family":SOURCE_FAMILY,"query_matrix":[{"srchKey":k,"query":q} for k,q in QUERY_MATRIX],"query_records":query_records,"candidates":candidates,"summary":summary,"attachment_body_download_executed":False,"state_mutation_executed":False,"negative_evidence_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"runtime_registration_allowed":False,"final_positive_promotion_allowed":False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    vals={"search requests executed":counter[0]>0,"request budget respected":counter[0]<=MAX_TOTAL_REQUESTS,"all query transports official":all(r['http_status']==200 and r['official_host'] for r in query_records),"canonical ids unique":len(candidates)==len({c['document_id'] for c in candidates}),"attachment download disabled":not payload['attachment_body_download_executed'],"state mutation disabled":not payload['state_mutation_executed'],"negative evidence disabled":not payload['negative_evidence_allowed'],"unsafe promotion leakage zero":not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),"output written":OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]
    print('DIRECT CANDIDATES:',[(c['document_id'],c['notice_number'],c['title']) for c in direct[:20]])
    print('RELATED CANDIDATES:',[(c['document_id'],c['notice_number'],c['title']) for c in related[:20]])
    print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S77 candidate collection failed')

if __name__=='__main__': main()
