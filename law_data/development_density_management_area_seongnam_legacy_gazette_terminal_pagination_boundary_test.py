# -*- coding: utf-8 -*-
"""S94: validate terminal pagination boundary of Seongnam legacy gazette list.

Prior dynamic-HWP processing covered 1,338 canonical gazette-era rows from the same
/bbs010308 source family. With the live list serving 10 rows/page, pages 133-135
are a bounded, high-value boundary probe: page 134 would be the expected terminal
page if the live list aligns with that corpus, and page 135 should be empty.

This stage reads list-row identity only (gazette number, pstSn, row-local dates).
No UQQ700 target-term search, detail request, attachment download, state mutation,
negative evidence, SITE/runtime promotion, or legal absence inference is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_terminal_pagination_boundary.json"

URL = "https://www.seongnam.go.kr/bbs010308"
HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_REQ = 5
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
EXPECTED_DYNAMIC_HWP_ROWS = 1338
ROWS_PER_PAGE = 10
PROBE_PAGES = [133, 134, 135]

FORM_RE = re.compile(r"<form\b(?P<a>[^>]*)>(?P<b>.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b(?P<a>[^>]*)/?>", re.I | re.S)
SELECT_RE = re.compile(r"<select\b(?P<a>[^>]*)>(?P<b>.*?)</select>", re.I | re.S)
OPTION_RE = re.compile(r"<option\b(?P<a>[^>]*)>(?P<b>.*?)</option>", re.I | re.S)
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


def rr(r: requests.Response) -> dict:
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": r.text, "bytes": len(r.content)}


def get(session, url, counter):
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.get(url, timeout=TIMEOUT, allow_redirects=True))


def recover_form_defaults(text: str) -> dict[str, str]:
    candidates = []
    for fm in FORM_RE.finditer(text or ""):
        fa = attrs(fm.group("a")); body = fm.group("b"); defaults = {}
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group("a")); name = ia.get("name", ""); typ = ia.get("type", "text").lower(); checked = "checked" in ia
            if name and not (typ in {"radio", "checkbox"} and not checked):
                defaults[name] = ia.get("value", "")
        for sm in SELECT_RE.finditer(body):
            sa = attrs(sm.group("a")); name = sa.get("name", ""); chosen = ""
            for om in OPTION_RE.finditer(sm.group("b")):
                oa = attrs(om.group("a")); value = oa.get("value", "")
                if "selected" in oa or chosen == "":
                    chosen = value
            if name:
                defaults[name] = chosen
        score = sum(k in defaults for k in ["csrfToken", "srchText", "srchTypeCd", "cntPerPage"])
        candidates.append((fa.get("method", "GET").upper(), score, defaults))
    candidates.sort(key=lambda x: (x[0] == "POST", x[1]), reverse=True)
    if not candidates:
        raise AssertionError("search form missing")
    return candidates[0][2]


def page_url(defaults: dict[str, str], page: int) -> str:
    params = dict(defaults)
    params.update({
        "curPage": str(page),
        "cntPerPage": "10",
        "sortType": params.get("sortType") or "1",
        "pstSn": "0",
        "srchText": "",
        "srchTypeCd": params.get("srchTypeCd") or "pstTtl",
        "srchDtType": "",
        "srchBgngYmd": "",
        "srchEndYmd": "",
    })
    safe_order = ["curPage", "srchDtType", "cntPerPage", "pstSn", "srchText", "srchBgngYmd", "pstTtl", "csrfToken", "sortType", "bbsCrtSn", "srchEndYmd", "srchTypeCd", "pstCn"]
    from urllib.parse import urlencode
    ordered = [(k, params.get(k, "")) for k in safe_order if k in params or k in {"curPage", "cntPerPage"}]
    return URL + "?" + urlencode(ordered)


def parse_rows(text: str) -> list[dict]:
    out = []; seen = set()
    for tm in TR_RE.finditer(text or ""):
        body = tm.group("b"); row_text = clean(body)
        gaz = None; pst = None
        for am in ANCHOR_RE.finditer(body):
            a = attrs(am.group("a")); label = clean(am.group("b")); gm = GAZ_RE.search(label)
            if not gm:
                continue
            mm = CALL_RE.search(a.get("href", "") + " " + a.get("onclick", ""))
            if not mm:
                continue
            gaz = int(gm.group(1)); pst = mm.group(1); break
        if gaz is None or pst is None:
            continue
        key = (gaz, pst)
        if key in seen:
            continue
        seen.add(key)
        dates = []
        for dm in DATE_RE.finditer(row_text):
            dates.append(dm.group(0))
        years = sorted({int(y) for y in YEAR_RE.findall(row_text)})
        out.append({"gazette_number": gaz, "pstSn": pst, "row_text": row_text[:1000], "dates": dates[:8], "years": years})
    return out


def main():
    print("=" * 60)
    print("SEONGNAM LEGACY GAZETTE TERMINAL PAGINATION BOUNDARY - S94")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Detail/attachment request: DISABLED")
    print("Negative evidence: DISABLED")

    s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    c = [0]
    entry = get(s, URL, c)
    defaults = recover_form_defaults(entry["text"])

    records = []
    for page in PROBE_PAGES:
        r = get(s, page_url(defaults, page), c)
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

    p133, p134, p135 = records
    exact_alignment = p133["row_count"] == 10 and p134["row_count"] == 8 and p135["row_count"] == 0
    inferred_count = (134 - 1) * ROWS_PER_PAGE + p134["row_count"] if p134["row_count"] and p135["row_count"] == 0 else None
    terminal_years = sorted({y for row in p134["rows"] for y in row["years"]})
    pre2010_year_observed = any(y < 2010 for y in terminal_years)

    summary = {
        "request_count": c[0],
        "expected_dynamic_hwp_rows": EXPECTED_DYNAMIC_HWP_ROWS,
        "page_133_row_count": p133["row_count"],
        "page_134_row_count": p134["row_count"],
        "page_135_row_count": p135["row_count"],
        "terminal_boundary_observed": p134["row_count"] > 0 and p135["row_count"] == 0,
        "inferred_live_list_row_count": inferred_count,
        "live_list_matches_dynamic_hwp_row_count": inferred_count == EXPECTED_DYNAMIC_HWP_ROWS,
        "terminal_page_observed_years": terminal_years,
        "pre2010_year_observed_on_terminal_page": pre2010_year_observed,
        "semantic_state": "LIVE_LIST_BOUNDARY_ALIGNS_DYNAMIC_HWP_CORPUS" if exact_alignment and inferred_count == EXPECTED_DYNAMIC_HWP_ROWS else "LIVE_LIST_BOUNDARY_NEEDS_FURTHER_RECONCILIATION",
        "pre2010_reachability_conclusion_allowed": bool(pre2010_year_observed),
        "negative_evidence_allowed": False,
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-35-S94",
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
        "entry transport official": entry["http"] == 200 and entry["host"] == HOST,
        "all probe transport official": all(x["http"] == 200 and x["official"] for x in records),
        "request budget respected": c[0] <= MAX_REQ,
        "target-term search disabled": not out["target_term_search_executed"],
        "detail request disabled": not out["detail_request_executed"],
        "negative evidence disabled": not out["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nSUMMARY")
    for k, v in summary.items(): print(f"{k}: {v}")
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items(): print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("S94 terminal pagination boundary probe failed")


if __name__ == "__main__":
    main()
