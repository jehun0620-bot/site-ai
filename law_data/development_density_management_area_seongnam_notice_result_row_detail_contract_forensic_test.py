# -*- coding: utf-8 -*-
"""S75: recover detail navigation contract from Seongnam notice search result rows.

Uses only the official /pm010301 GET search contract recovered in S74.
Inspects row-local HTML around notice-number matches and extracts href/onclick/
data-* / hidden identifiers. No attachments, state mutation, or legal negative evidence.
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
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_result_row_detail_contract_forensic.json"

SEARCH_URL = "https://www.seongnam.go.kr/pm010301"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 4
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

PROBES = [
    {"srchKey": "sj", "srchText": "도시관리계획"},
    {"srchKey": "cn", "srchText": "도시관리계획"},
]

NOTICE_NUMBER_RE = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*\d{4}\s*[-－]\s*\d+\s*호")
ROW_RE = re.compile(r"<(tr|li|div)\b[^>]*>.*?</\1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>", re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
ELEMENT_RE = re.compile(r"<(a|button|input)\b(?P<attrs>[^>]*)>(?P<body>.*?)</\1>|<(input)\b(?P<inputattrs>[^>]*)/?>", re.I | re.S)
NUMERIC_PATH_RE = re.compile(r"/pm010301/(\d+)")
JS_NUMERIC_RE = re.compile(r"(?:pm010301|view|detail|go|fn)[^\n\r]{0,180}?['\"]?(\d{4,})['\"]?", re.I)


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
    base = {"curPage": "1", "cntPerPage": "10", "sortType": "1", **params}
    r = session.get(SEARCH_URL, params=base, timeout=TIMEOUT, allow_redirects=True)
    body = r.content[:MAX_RESPONSE_BYTES]
    text = body.decode(r.encoding or "utf-8", errors="replace")
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": text}


def candidate_blocks(text: str) -> list[str]:
    blocks = []
    for m in ROW_RE.finditer(text or ""):
        block = m.group(0)
        if NOTICE_NUMBER_RE.search(clean(block)):
            blocks.append(block)
    if blocks:
        return blocks
    # Fallback: bounded windows around each notice-number occurrence.
    for m in NOTICE_NUMBER_RE.finditer(clean(text)):
        pass
    raw = text or ""
    for m in re.finditer(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*\d{4}\s*[-－]\s*\d+\s*호", raw):
        lo=max(0,m.start()-1600); hi=min(len(raw),m.end()+1600); blocks.append(raw[lo:hi])
    return blocks


def inspect_block(block: str) -> dict:
    text = clean(block)
    nums = sorted(set(NOTICE_NUMBER_RE.findall(text)))
    element_attrs = []
    numeric_ids = set()
    for em in ELEMENT_RE.finditer(block):
        raw_attrs = em.group("attrs") or em.group("inputattrs") or ""
        aa = attrs(raw_attrs)
        interesting = {k:v for k,v in aa.items() if k in {"href","onclick","value","name","id"} or k.startswith("data-")}
        if interesting:
            element_attrs.append(interesting)
        for value in interesting.values():
            for mm in NUMERIC_PATH_RE.finditer(value): numeric_ids.add(mm.group(1))
            for mm in JS_NUMERIC_RE.finditer(value): numeric_ids.add(mm.group(1))
    for mm in NUMERIC_PATH_RE.finditer(block): numeric_ids.add(mm.group(1))
    return {"notice_numbers": nums, "text_excerpt": text[:1200], "elements": element_attrs[:80], "numeric_detail_id_candidates": sorted(numeric_ids)}


def main():
    print('='*60); print('SEONGNAM NOTICE RESULT ROW DETAIL CONTRACT FORENSIC - S75'); print('='*60)
    print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')
    s=requests.Session(); s.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ko-KR,ko;q=0.9"})
    counter=[0]; records=[]
    for probe in PROBES:
        r=fetch(s,probe,counter)
        blocks=candidate_blocks(r['text'])
        inspected=[inspect_block(b) for b in blocks[:20]]
        rec={"probe":probe,"http_status":r['http'],"request_url":r['url'],"official_host":r['host']==OFFICIAL_HOST,"notice_row_block_count":len(blocks),"rows":inspected}
        records.append(rec)
        print('\nPROBE',probe,'http',r['http'],'blocks',len(blocks))
        for row in inspected[:10]:
            print('ROW:', {'notice_numbers':row['notice_numbers'],'numeric_detail_id_candidates':row['numeric_detail_id_candidates'],'elements':row['elements'][:8]})

    all_rows=[row for rec in records for row in rec['rows']]
    rows_with_ids=[r for r in all_rows if r['numeric_detail_id_candidates']]
    rows_with_navigation_attrs=[r for r in all_rows if any(any(k in e for k in ['href','onclick']) for e in r['elements'])]
    summary={
        "probe_count":len(records),
        "all_probe_http_200":all(r['http_status']==200 and r['official_host'] for r in records),
        "notice_row_count_inspected":len(all_rows),
        "rows_with_navigation_attrs":len(rows_with_navigation_attrs),
        "rows_with_numeric_detail_id_candidates":len(rows_with_ids),
        "detail_navigation_evidence_discovered":bool(rows_with_navigation_attrs or rows_with_ids),
        "request_count":counter[0],
    }
    payload={"step":"STEP 17-21-C-16-8-T-35-S75","target_name":"개발밀도관리구역","standard_code":"UQQ700","resolution_type":"HYBRID_SPATIAL_NOTICE","source_family":"NOTICE_NUMBER_REVERSE_LOOKUP","records":records,"summary":summary,"attachment_body_download_executed":False,"state_mutation_executed":False,"negative_evidence_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False,"runtime_registration_allowed":False}
    OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    vals={"search transport ok":summary['all_probe_http_200'],"notice rows inspected":summary['notice_row_count_inspected']>0,"request budget respected":counter[0]<=MAX_TOTAL_REQUESTS,"attachment download disabled":not payload['attachment_body_download_executed'],"state mutation disabled":not payload['state_mutation_executed'],"negative evidence disabled":not payload['negative_evidence_allowed'],"unsafe promotion leakage zero":not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed']),"output written":OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size>0}
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:',OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:',all(vals.values()))
    if not all(vals.values()): raise AssertionError('S75 validation failed')

if __name__=='__main__': main()
