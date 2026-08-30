# -*- coding: utf-8 -*-
"""S76: validate f_view(document_id) -> /pm010301/{document_id} detail contract.

Uses a bounded sample of document IDs observed in S75 search rows. Verifies that
constructed official detail URLs resolve and expose structured notice numbers.
No attachment download, cumulative-state mutation, candidate promotion, or legal
negative evidence is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_detail_id_contract_validation.json"

OFFICIAL_HOST = "www.seongnam.go.kr"
DETAIL_PREFIX = "https://www.seongnam.go.kr/pm010301/"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 6
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

SAMPLES = [
    {"document_id": "151718", "expected_notice_number": "성남시 고시 제2026-170호"},
    {"document_id": "150635", "expected_notice_number": "성남시 고시 제2026-138호"},
    {"document_id": "150566", "expected_notice_number": "성남시 고시 제2026-134호"},
    {"document_id": "150498", "expected_notice_number": "성남시 고시 제2026-131호"},
]

TAG_RE = re.compile(r"<[^>]+>", re.S)
NOTICE_NUMBER_RE = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*\d{4}\s*[-－]\s*\d+\s*호")
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def title(raw: str) -> str:
    m = TITLE_RE.search(raw or "")
    return clean(m.group(1)) if m else ""


def fetch(session: requests.Session, url: str, counter: list[int]) -> dict:
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    body = r.content[:MAX_RESPONSE_BYTES]
    text = body.decode(r.encoding or "utf-8", errors="replace")
    page_text = clean(text)
    return {
        "http_status": r.status_code,
        "request_url": url,
        "final_url": str(r.url),
        "final_host": (urlparse(str(r.url)).hostname or "").lower(),
        "title": title(text),
        "notice_numbers": sorted(set(NOTICE_NUMBER_RE.findall(page_text))),
        "body_bytes_read": len(body),
    }


def main():
    print('='*60); print('SEONGNAM NOTICE DETAIL ID CONTRACT VALIDATION - S76'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')

    s=requests.Session(); s.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ko-KR,ko;q=0.9"})
    counter=[0]; records=[]
    for sample in SAMPLES:
        url=DETAIL_PREFIX+sample['document_id']
        rec=fetch(s,url,counter)
        rec.update(sample)
        rec['official_detail_path_matches_id']=urlparse(rec['final_url']).path==f"/pm010301/{sample['document_id']}"
        rec['expected_notice_number_present']=sample['expected_notice_number'] in rec['notice_numbers']
        records.append(rec)
        print('RECORD:',rec)

    summary={
        "sample_count":len(records),
        "all_http_200":all(r['http_status']==200 for r in records),
        "all_official_host":all(r['final_host']==OFFICIAL_HOST for r in records),
        "all_detail_path_matches_id":all(r['official_detail_path_matches_id'] for r in records),
        "all_expected_notice_numbers_present":all(r['expected_notice_number_present'] for r in records),
        "detail_id_contract_validated":all(r['http_status']==200 and r['final_host']==OFFICIAL_HOST and r['official_detail_path_matches_id'] and r['expected_notice_number_present'] for r in records),
        "request_count":counter[0],
    }
    payload={
        "step":"STEP 17-21-C-16-8-T-35-S76",
        "target_name":"개발밀도관리구역",
        "standard_code":"UQQ700",
        "resolution_type":"HYBRID_SPATIAL_NOTICE",
        "source_family":"NOTICE_NUMBER_REVERSE_LOOKUP",
        "detail_url_contract":"https://www.seongnam.go.kr/pm010301/{document_id}",
        "records":records,
        "summary":summary,
        "attachment_body_download_executed":False,
        "state_mutation_executed":False,
        "candidate_promotion_executed":False,
        "negative_evidence_allowed":False,
        "site_positive_allowed":False,
        "site_negative_allowed":False,
        "runtime_registration_allowed":False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={
        "four samples inspected":len(records)==4,
        "detail transport ok":summary['all_http_200'] and summary['all_official_host'],
        "detail path contract exact":summary['all_detail_path_matches_id'],
        "notice identity matches":summary['all_expected_notice_numbers_present'],
        "detail id contract validated":summary['detail_id_contract_validated'],
        "request budget respected":counter[0]<=MAX_TOTAL_REQUESTS,
        "attachment download disabled":not payload['attachment_body_download_executed'],
        "state mutation disabled":not payload['state_mutation_executed'],
        "candidate promotion disabled":not payload['candidate_promotion_executed'],
        "negative evidence disabled":not payload['negative_evidence_allowed'],
        "unsafe promotion leakage zero":not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),
        "output written":OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0,
    }
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S76 detail contract validation failed')

if __name__=='__main__': main()
