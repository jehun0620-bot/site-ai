# -*- coding: utf-8 -*-
"""S85: bounded pre-2010 reachability probe for Seongnam legacy gazette.

Uses the S84 recovered POST search contract for /bbs010308 and explicit date
ranges to determine whether pre-2010 gazette records are technically reachable.
This stage does not search UQQ700 terms, download attachments, mutate state,
allow legal negative evidence, or promote SITE/runtime conclusions.
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
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_legacy_gazette_pre2010_reachability.json"

URL = "https://www.seongnam.go.kr/bbs010308"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 8
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

PROBES = [
    ("2009", "20090101", "20091231"),
    ("2008", "20080101", "20081231"),
    ("2005-2007", "20050101", "20071231"),
    ("2000-2004", "20000101", "20041231"),
]

TAG_RE = re.compile(r"<[^>]+>", re.S)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
PSTSN_RE = re.compile(r"(?:pstSn|f_view)\s*(?:=|\()\s*['\"]?(\d{3,})", re.I)
ONCLICK_RE = re.compile(r"(?:f_view|fn_view|goView|view)\s*\(\s*['\"]?(\d{3,})", re.I)
ROW_RE = re.compile(r"<(?:tr|li)\b[^>]*>.*?</(?:tr|li)>", re.I | re.S)


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session, data, counter):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.post(URL, data=data, timeout=TIMEOUT, allow_redirects=True)
    return {
        "http_status": r.status_code,
        "final_url": str(r.url),
        "final_host": (urlparse(str(r.url)).hostname or "").lower(),
        "text": r.text,
    }


def inspect(text: str):
    page_text = clean(text)
    years = sorted({int(y) for y in YEAR_RE.findall(page_text)})
    ids = list(dict.fromkeys(ONCLICK_RE.findall(text) + PSTSN_RE.findall(text)))
    row_count = 0
    row_samples = []
    for rm in ROW_RE.finditer(text or ""):
        rt = clean(rm.group(0))
        if re.search(r"\b(?:19|20)\d{2}\b", rt) and len(rt) > 20:
            row_count += 1
            if len(row_samples) < 8:
                row_samples.append(rt[:300])
    return {"observed_years": years, "document_id_hints": ids[:50], "row_count_hint": row_count, "row_samples": row_samples}


def main():
    print('='*60); print('SEONGNAM LEGACY GAZETTE PRE-2010 REACHABILITY - S85'); print('='*60)
    print('Target-term search: DISABLED'); print('Attachment download: DISABLED'); print('State mutation: DISABLED'); print('Negative evidence: DISABLED')

    s = requests.Session(); s.headers.update({'User-Agent': USER_AGENT, 'Accept-Language': 'ko-KR,ko;q=0.9'})
    counter = [0]; records = []

    for label, bg, end in PROBES:
        data = {
            'cntPerPage': '30',
            'sortType': '1',
            'srchTypeCd': 'pstTtl',
            'srchText': '',
            'srchDtType': '',
            'srchBgngYmd': bg,
            'srchEndYmd': end,
            'curPage': '1',
        }
        rec = fetch(s, data, counter); ins = inspect(rec['text'])
        item = {
            'label': label,
            'date_from': bg,
            'date_to': end,
            'http_status': rec['http_status'],
            'official_host': rec['final_host'] == OFFICIAL_HOST,
            **ins,
            'pre2010_year_visible': any(y < 2010 for y in ins['observed_years']),
        }
        records.append(item)
        print('PROBE:', {k:item[k] for k in ['label','http_status','official_host','row_count_hint','observed_years','pre2010_year_visible']})
        if item['row_samples']:
            print('  ROW SAMPLE:', item['row_samples'][:2])

    summary = {
        'probe_count': len(records),
        'request_count': counter[0],
        'any_pre2010_year_visible': any(r['pre2010_year_visible'] for r in records),
        'any_document_id_hint': any(r['document_id_hints'] for r in records),
        'any_row_hint': any(r['row_count_hint'] > 0 for r in records),
        'reachable_probe_labels': [r['label'] for r in records if r['pre2010_year_visible'] or r['document_id_hints'] or r['row_count_hint'] > 0],
    }
    payload = {
        'step': 'STEP 17-21-C-16-8-T-35-S85',
        'target_name': '개발밀도관리구역',
        'standard_code': 'UQQ700',
        'resolution_type': 'HYBRID_SPATIAL_NOTICE',
        'source_family': 'LEGACY_LOCAL_GAZETTE',
        'records': records,
        'summary': summary,
        'target_term_search_executed': False,
        'attachment_body_download_executed': False,
        'state_mutation_executed': False,
        'negative_evidence_allowed': False,
        'site_positive_allowed': False,
        'site_negative_allowed': False,
        'runtime_registration_allowed': False,
        'final_positive_promotion_allowed': False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    vals = {
        'all probes official': all(r['http_status'] == 200 and r['official_host'] for r in records),
        'request budget respected': counter[0] <= MAX_TOTAL_REQUESTS,
        'target-term search disabled': not payload['target_term_search_executed'],
        'attachment download disabled': not payload['attachment_body_download_executed'],
        'state mutation disabled': not payload['state_mutation_executed'],
        'negative evidence disabled': not payload['negative_evidence_allowed'],
        'unsafe promotion leakage zero': not any(payload[k] for k in ['site_positive_allowed','site_negative_allowed','runtime_registration_allowed','final_positive_promotion_allowed']),
        'output written': OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }
    print('\nSUMMARY'); [print(f'{k}: {v}') for k,v in summary.items()]; print('Output:', OUTPUT_PATH)
    print('\nVALIDATION'); [print(f'{k}: {v}') for k,v in vals.items()]; print('all_pass:', all(vals.values()))
    if not all(vals.values()): raise AssertionError('S85 pre-2010 reachability failed')

if __name__ == '__main__': main()
