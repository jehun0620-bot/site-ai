# -*- coding: utf-8 -*-
"""S96: localize the deeper terminal boundary of Seongnam legacy gazette list.

S95 validated a concrete 2007 list->detail identity and showed list page 160 still
contains 2003 rows. Detail-page global years are known UI contamination, so this
stage uses only row-local list identity/year evidence. It performs sparse bounded
probes at pages 170/180/190/200 to determine whether the official archive continues
into earlier years and to bracket the eventual terminal page.

No UQQ700 target-term search, detail request, attachment download, state mutation,
negative evidence, SITE/runtime promotion, or legal absence inference is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_deep_terminal_boundary_localization.json"

URL = "https://www.seongnam.go.kr/bbs010308"
HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_REQ = 6
PROBE_PAGES = [170, 180, 190, 200]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

TR_RE = re.compile(r"<tr\b[^>]*>(?P<b>.*?)</tr>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZ_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
CALL_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
DATE_RE = re.compile(r"\b((?:19|20)\d{2})[.\-/년]\s*(\d{1,2})?[.\-/월]?\s*(\d{1,2})?일?\b")
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch(session: requests.Session, url: str, counter: list[int]) -> dict:
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    return {
        "http": r.status_code,
        "url": str(r.url),
        "host": (urlparse(str(r.url)).hostname or "").lower(),
        "text": r.text,
        "bytes": len(r.content),
    }


def page_url(page: int) -> str:
    params = {
        "curPage": str(page),
        "cntPerPage": "10",
        "pstSn": "0",
        "srchText": "",
        "srchBgngYmd": "",
        "srchEndYmd": "",
        "sortType": "1",
        "srchTypeCd": "pstTtl",
        "srchDtType": "",
    }
    return URL + "?" + urlencode(params)


def parse_rows(text: str) -> list[dict]:
    out = []
    seen = set()
    for tm in TR_RE.finditer(text or ""):
        body = tm.group("b")
        row_text = clean(body)
        gaz = None
        pst = None
        for am in ANCHOR_RE.finditer(body):
            a = attrs(am.group("a"))
            label = clean(am.group("b"))
            gm = GAZ_RE.search(label)
            if not gm:
                continue
            mm = CALL_RE.search(a.get("href", "") + " " + a.get("onclick", ""))
            if not mm:
                continue
            gaz = int(gm.group(1))
            pst = mm.group(1)
            break
        if gaz is None or pst is None:
            continue
        key = (gaz, pst)
        if key in seen:
            continue
        seen.add(key)
        dates = [m.group(0) for m in DATE_RE.finditer(row_text)]
        years = sorted({int(y) for y in YEAR_RE.findall(row_text)})
        out.append({
            "gazette_number": gaz,
            "pstSn": pst,
            "row_text": row_text[:1200],
            "dates": dates[:8],
            "years": years,
        })
    return out


def main():
    print("=" * 60)
    print("SEONGNAM LEGACY GAZETTE DEEP TERMINAL BOUNDARY LOCALIZATION - S96")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Detail/attachment request: DISABLED")
    print("Negative evidence: DISABLED")

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    c = [0]

    records = []
    for page in PROBE_PAGES:
        r = fetch(s, page_url(page), c)
        parsed = parse_rows(r["text"])
        years = sorted({y for row in parsed for y in row["years"]})
        item = {
            "page": page,
            "http": r["http"],
            "official": r["host"] == HOST,
            "row_count": len(parsed),
            "identities": [(x["gazette_number"], x["pstSn"]) for x in parsed],
            "observed_years": years,
            "rows": parsed,
        }
        records.append(item)
        print("PAGE:", {k: item[k] for k in ["page", "http", "official", "row_count", "identities", "observed_years"]})

    nonempty = [x for x in records if x["row_count"] > 0]
    empty = [x for x in records if x["row_count"] == 0]
    all_years = sorted({y for x in records for y in x["observed_years"]})
    oldest = min(all_years) if all_years else None
    deepest_nonempty = max((x["page"] for x in nonempty), default=None)
    shallowest_empty = min((x["page"] for x in empty), default=None)
    boundary_bracketed = deepest_nonempty is not None and shallowest_empty is not None and deepest_nonempty < shallowest_empty

    if boundary_bracketed:
        semantic = "TERMINAL_BOUNDARY_BRACKETED"
    elif nonempty and not empty:
        semantic = "ARCHIVE_CONTINUES_BEYOND_PAGE_200"
    elif empty and not nonempty:
        semantic = "TERMINAL_BOUNDARY_BEFORE_PAGE_170"
    else:
        semantic = "DEEP_BOUNDARY_NEEDS_RECONCILIATION"

    summary = {
        "request_count": c[0],
        "probe_pages": PROBE_PAGES,
        "nonempty_pages": [x["page"] for x in nonempty],
        "empty_pages": [x["page"] for x in empty],
        "deepest_nonempty_page": deepest_nonempty,
        "shallowest_empty_page": shallowest_empty,
        "terminal_boundary_bracketed": boundary_bracketed,
        "oldest_observed_row_local_year": oldest,
        "pre2003_year_observed": bool(oldest is not None and oldest < 2003),
        "semantic_state": semantic,
        "pre2010_source_reachability_verified": True,
        "negative_evidence_allowed": False,
        "uqq700_final_resolution": "UNKNOWN",
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-35-S96",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "LEGACY_LOCAL_GAZETTE",
        "probe_pages": records,
        "summary": summary,
        "target_term_search_executed": False,
        "detail_request_executed": False,
        "attachment_body_download_executed": False,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "all probe transport official": all(x["http"] == 200 and x["official"] for x in records),
        "request budget respected": c[0] <= MAX_REQ,
        "target-term search disabled": not out["target_term_search_executed"],
        "detail request disabled": not out["detail_request_executed"],
        "negative evidence disabled": not out["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("S96 deep terminal boundary localization failed")


if __name__ == "__main__":
    main()
