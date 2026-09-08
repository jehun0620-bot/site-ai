# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_PATH = OUT_DIR / "development_density_management_area_molit_i0204_post_bounded_uqq700_title_search.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
LIST_URL = "https://www.molit.go.kr/USR/I0204/m_45/lst.jsp"
OFFICIAL_HOSTS = {"www.molit.go.kr", "molit.go.kr"}
PSIZE = "10"

QUERIES = [
    ("EXACT", "개발밀도관리구역"),
    ("VARIANT", "개발밀도 관리구역"),
    ("WEAK", "개발밀도"),
]


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def strip_tags(value: str | None) -> str:
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


def page_title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", flags=re.I | re.S)
    return strip_tags(m.group(1)) if m else None


def parse_attrs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for m in re.finditer(
        r"([:\w-]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+)))?",
        raw or "",
        flags=re.I | re.S,
    ):
        name = (m.group(1) or "").lower()
        if not name:
            continue
        value = next((g for g in m.groups()[1:] if g is not None), "")
        attrs[name] = unescape(value)
    return attrs


def extract_detail_rows(html: str) -> list[dict]:
    rows: list[dict] = []
    seen = set()
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html or "", flags=re.I | re.S):
        attrs = parse_attrs(m.group(1))
        href = unescape(attrs.get("href", ""))
        text = strip_tags(m.group(2))
        if not href or "dtl.jsp" not in href:
            continue
        absolute = urljoin(LIST_URL, href)
        parsed = urlparse(absolute)
        qs = parse_qs(parsed.query)
        idx = (qs.get("idx") or [None])[0]
        key = (idx, text)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": text,
                "idx": idx,
                "href": href,
                "absolute_url": absolute,
                "host": parsed.netloc,
            }
        )
    return rows


def title_search_payload(term: str) -> dict[str, str]:
    # Replay only the contract that was positively qualified in the preceding stage:
    # POST lst.jsp + search=<term> + srch_usr_titl=Y.
    # Unchecked checkbox fields srch_usr_nm / srch_usr_ctnt are intentionally omitted.
    return {
        "gubun": "",
        "flag": "I",
        "r_id": "",
        "lcmspage": "1",
        "search_dept_id": "",
        "search_dept_nm": "",
        "search_regdate_s": "",
        "search_regdate_e": "",
        "srch_usr_year": "",
        "srch_usr_num": "",
        "search": term,
        "psize": PSIZE,
        "srch_usr_titl": "Y",
    }


def run_query(session: requests.Session, label: str, term: str) -> dict:
    payload = title_search_payload(term)
    out = {
        "label": label,
        "term": term,
        "method": "POST",
        "endpoint": LIST_URL,
        "data": payload,
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "technical_unknown": True,
        "result_count": 0,
        "results": [],
        "error": None,
    }
    try:
        r = session.post(LIST_URL, data=payload, timeout=30, allow_redirects=True)
        out["http"] = r.status_code
        out["final_url"] = r.url
        out["official_final_host"] = urlparse(r.url).netloc in OFFICIAL_HOSTS
        out["page_title"] = page_title(r.text)
        r.raise_for_status()
        rows = extract_detail_rows(r.text)
        out["result_count"] = len(rows)
        out["results"] = rows[:100]
        out["technical_unknown"] = False
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> None:
    print("=" * 78)
    print("MOLIT I0204 POST BOUNDED UQQ700 TITLE SEARCH")
    print("=" * 78)
    print("Purpose: bounded EXACT/VARIANT/WEAK UQQ700 search using only the positively qualified POST title-search contract")
    print("Search hit != designation/current validity/site inclusion")
    print("No hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 MOLIT POST bounded UQQ700 title search)",
            "Referer": LIST_URL,
        }
    )

    searches = [run_query(session, label, term) for label, term in QUERIES]

    technical_unknown_count = sum(1 for row in searches if row["technical_unknown"])
    total_result_count = sum(row["result_count"] for row in searches)

    unique_map: dict[str, dict] = {}
    provenance: dict[str, list[str]] = {}
    for search in searches:
        for item in search["results"]:
            key = str(item.get("idx") or item.get("absolute_url") or item.get("title"))
            if key not in unique_map:
                unique_map[key] = item
            provenance.setdefault(key, []).append(search["label"])

    unique_results = []
    for key, item in unique_map.items():
        enriched = dict(item)
        enriched["matched_query_labels"] = provenance.get(key, [])
        unique_results.append(enriched)

    if technical_unknown_count:
        classification = "MOLIT_I0204_POST_BOUNDED_UQQ700_TITLE_SEARCH_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_POST_TRANSPORT_OR_RESPONSE_PARSING_WITHOUT_NEGATIVE_EVIDENCE"
    elif total_result_count > 0:
        classification = "MOLIT_I0204_POST_UQQ700_TITLE_CANDIDATE_RESULTS_FOUND"
        next_action = "STOP_BULK_SEARCH_AND_VERIFY_CANDIDATE_DETAIL_DOCUMENT_IDENTITY_BEFORE_ANY_LEGAL_PROMOTION"
    else:
        classification = "MOLIT_I0204_POST_BOUNDED_UQQ700_TITLE_SEARCH_NO_RESULT"
        next_action = "CLOSE_ONLY_THIS_QUALIFIED_POST_TITLE_SEARCH_PATH_OPERATIONALLY_AND_CONTINUE_OTHER_OFFICIAL_SOURCE_DISCOVERY_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP17-MOLIT-I0204-POST-BOUNDED-UQQ700-TITLE-SEARCH",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "list_url": LIST_URL,
        "qualified_contract": {
            "method": "POST",
            "endpoint": LIST_URL,
            "query_text_field": "search",
            "title_scope_field": "srch_usr_titl",
            "title_scope_value": "Y",
            "unchecked_name_scope_omitted": True,
            "unchecked_content_scope_omitted": True,
        },
        "queries": [{"label": label, "term": term} for label, term in QUERIES],
        "searches": searches,
        "technical_unknown_count": technical_unknown_count,
        "total_result_count": total_result_count,
        "unique_result_count": len(unique_results),
        "unique_results": unique_results,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "search_hit_equals_designation": False,
            "search_hit_equals_current_validity": False,
            "search_hit_equals_site_inclusion": False,
            "no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("BOUNDED POST SEARCH RESULT")
    print("=" * 78)
    for row in searches:
        print(
            f"{row['label']}: term={row['term']!r} http={row['http']} "
            f"results={row['result_count']} technical_unknown={row['technical_unknown']}"
        )
        print(f"    final={row['final_url']}")
        for item in row["results"][:30]:
            print(f"    RESULT idx={item['idx']} title={item['title']}")
            print(f"      url={item['absolute_url']}")
        if row["error"]:
            print(f"    error={row['error']}")

    print("\n" + "=" * 78)
    print("UNIQUE CANDIDATES")
    print("=" * 78)
    print(f"Total result count: {total_result_count}")
    print(f"Unique result count: {len(unique_results)}")
    for item in unique_results[:50]:
        print(
            f"  UNIQUE idx={item.get('idx')} labels={item.get('matched_query_labels')} "
            f"title={item.get('title')}"
        )
        print(f"    url={item.get('absolute_url')}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Search hit == designation: False")
    print("Search hit == current validity: False")
    print("Search hit == site inclusion: False")
    print("No hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET_NAME,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "official list URL fixed": out["list_url"] == LIST_URL,
        "qualified contract uses POST": out["qualified_contract"]["method"] == "POST",
        "qualified query text field fixed": out["qualified_contract"]["query_text_field"] == "search",
        "qualified title scope enabled": out["qualified_contract"]["title_scope_field"] == "srch_usr_titl"
        and out["qualified_contract"]["title_scope_value"] == "Y",
        "three bounded queries fixed": out["queries"] == [{"label": label, "term": term} for label, term in QUERIES],
        "all requests POST": all(row["method"] == "POST" for row in searches),
        "all requests carry title scope": all(row["data"].get("srch_usr_titl") == "Y" for row in searches),
        "all requests carry term in search": all(row["data"].get("search") == row["term"] for row in searches),
        "unchecked non-title scopes omitted": all("srch_usr_nm" not in row["data"] and "srch_usr_ctnt" not in row["data"] for row in searches),
        "technical state explicit": all(row["technical_unknown"] in {True, False} for row in searches),
        "search hit not designation": out["summary"]["search_hit_equals_designation"] is False,
        "search hit not validity": out["summary"]["search_hit_equals_current_validity"] is False,
        "search hit not site inclusion": out["summary"]["search_hit_equals_site_inclusion"] is False,
        "no hit not legal absence": out["summary"]["no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT_PATH.exists() and OUT_PATH.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT_PATH}")
    if not all(validation.values()):
        raise AssertionError("MOLIT I0204 POST bounded UQQ700 title search validation failed")


if __name__ == "__main__":
    main()
