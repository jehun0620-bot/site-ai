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
OUT_PATH = OUT_DIR / "development_density_management_area_molit_i0204_bounded_uqq700_title_search.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
LIST_URL = "https://www.molit.go.kr/USR/I0204/m_45/lst.jsp"
OFFICIAL_HOSTS = {"www.molit.go.kr", "molit.go.kr"}

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
        r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
        raw or "",
        flags=re.I | re.S,
    ):
        name = m.group(1).lower()
        value = next((g for g in m.groups()[1:] if g is not None), "")
        attrs[name] = unescape(value)
    return attrs


def extract_form_contract(html: str) -> dict:
    forms = []
    for fm in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html or "", flags=re.I | re.S):
        attrs = parse_attrs(fm.group(1))
        body = fm.group(2)
        fields = []
        defaults: dict[str, str] = {}
        for im in re.finditer(r"<(?:input|select|textarea)\b([^>]*)>", body, flags=re.I | re.S):
            iattrs = parse_attrs(im.group(1))
            name = iattrs.get("name")
            if not name:
                continue
            fields.append(name)
            defaults.setdefault(name, iattrs.get("value", ""))
        action = urljoin(LIST_URL, attrs.get("action") or LIST_URL)
        method = (attrs.get("method") or "GET").upper()
        score = 0
        if urlparse(action).path.endswith("/USR/I0204/m_45/lst.jsp"):
            score += 5
        if "srch_usr_titl" in fields:
            score += 4
        if method == "GET":
            score += 2
        forms.append(
            {
                "method": method,
                "action": action,
                "fields": fields,
                "defaults": defaults,
                "score": score,
            }
        )
    forms.sort(key=lambda row: row["score"], reverse=True)
    return forms[0] if forms else {}


def extract_detail_rows(html: str) -> list[dict]:
    rows: list[dict] = []
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


def run_query(session: requests.Session, label: str, term: str, action: str, defaults: dict[str, str]) -> dict:
    params = {
        "gubun": defaults.get("gubun", ""),
        "flag": defaults.get("flag", "I") or "I",
        "r_id": defaults.get("r_id", ""),
        "lcmspage": "1",
        "search_dept_id": defaults.get("search_dept_id", ""),
        "search_dept_nm": defaults.get("search_dept_nm", ""),
        "search_regdate_s": defaults.get("search_regdate_s", ""),
        "search_regdate_e": defaults.get("search_regdate_e", ""),
        "srch_usr_year": defaults.get("srch_usr_year", ""),
        "srch_usr_num": defaults.get("srch_usr_num", ""),
        "srch_usr_nm": defaults.get("srch_usr_nm", "Y") or "Y",
        "srch_usr_titl": term,
        "srch_usr_ctnt": defaults.get("srch_usr_ctnt", "Y") or "Y",
        "search": "",
        "psize": defaults.get("psize", "10") or "10",
    }

    out = {
        "label": label,
        "term": term,
        "method": "GET",
        "endpoint": action,
        "params": params,
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
        r = session.get(action, params=params, timeout=30, allow_redirects=True)
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
    print("MOLIT I0204 BOUNDED UQQ700 TITLE SEARCH")
    print("=" * 78)
    print("Purpose: bounded EXACT/VARIANT/WEAK UQQ700 title search using only the qualified MOLIT I0204 title contract")
    print("Search hit != designation/current validity/site inclusion")
    print("No hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 MOLIT bounded UQQ700 title search)",
            "Referer": "https://www.molit.go.kr/",
        }
    )

    entry = {
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "form_contract": {},
        "technical_unknown": True,
        "error": None,
    }
    searches: list[dict] = []

    try:
        r = session.get(LIST_URL, timeout=30, allow_redirects=True)
        entry["http"] = r.status_code
        entry["final_url"] = r.url
        entry["official_final_host"] = urlparse(r.url).netloc in OFFICIAL_HOSTS
        entry["page_title"] = page_title(r.text)
        r.raise_for_status()
        contract = extract_form_contract(r.text)
        entry["form_contract"] = contract
        entry["technical_unknown"] = False

        action = contract.get("action") or LIST_URL
        defaults = contract.get("defaults") or {}
        searches = [run_query(session, label, term, action, defaults) for label, term in QUERIES]
    except Exception as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"

    contract_qualified = bool(
        entry["technical_unknown"] is False
        and entry["http"] == 200
        and entry["official_final_host"]
        and entry["form_contract"].get("method") == "GET"
        and urlparse(entry["form_contract"].get("action", "")).path.endswith("/USR/I0204/m_45/lst.jsp")
        and "srch_usr_titl" in entry["form_contract"].get("fields", [])
    )

    technical_unknown_count = sum(1 for row in searches if row["technical_unknown"])
    total_result_count = sum(row["result_count"] for row in searches)
    unique = {}
    for row in searches:
        for item in row["results"]:
            key = item.get("idx") or item.get("absolute_url") or item.get("title")
            unique.setdefault(key, item)
    unique_results = list(unique.values())

    if entry["technical_unknown"] or technical_unknown_count:
        classification = "MOLIT_I0204_BOUNDED_UQQ700_TITLE_SEARCH_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_THE_QUALIFIED_TITLE_SEARCH_REPLAY_WITHOUT_NEGATIVE_EVIDENCE"
    elif not contract_qualified:
        classification = "MOLIT_I0204_QUALIFIED_TITLE_CONTRACT_NOT_RECONFIRMED"
        next_action = "RECONFIRM_ONLY_THE_POSITIVE_CONTROL_SEARCH_CONTRACT_BEFORE_FURTHER_UQQ700_SEARCH"
    elif total_result_count > 0:
        classification = "MOLIT_I0204_UQQ700_TITLE_CANDIDATE_RESULTS_FOUND"
        next_action = "STOP_BULK_SEARCH_AND_VERIFY_EACH_CANDIDATE_DETAIL_DOCUMENT_IDENTITY_BEFORE_ANY_LEGAL_PROMOTION"
    else:
        classification = "MOLIT_I0204_BOUNDED_UQQ700_TITLE_SEARCH_NO_RESULT"
        next_action = "CLOSE_ONLY_THIS_QUALIFIED_TITLE_SEARCH_PATH_OPERATIONALLY_AND_CONTINUE_OTHER_OFFICIAL_SOURCE_DISCOVERY_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP17-MOLIT-I0204-BOUNDED-UQQ700-TITLE-SEARCH",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "list_url": LIST_URL,
        "queries": [{"label": label, "term": term} for label, term in QUERIES],
        "contract_qualified": contract_qualified,
        "entry": entry,
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
    print("BOUNDED SEARCH RESULT")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry['http']}")
    for row in searches:
        print(
            f"{row['label']}: term={row['term']!r} http={row['http']} "
            f"results={row['result_count']} technical_unknown={row['technical_unknown']}"
        )
        print(f"    final={row['final_url']}")
        for item in row["results"][:20]:
            print(f"    RESULT idx={item['idx']} title={item['title']}")
            print(f"      url={item['absolute_url']}")
        if row["error"]:
            print(f"    error={row['error']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"Total result count: {total_result_count}")
    print(f"Unique result count: {len(unique_results)}")
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
        "three bounded queries fixed": out["queries"] == [{"label": label, "term": term} for label, term in QUERIES],
        "technical state explicit": entry["technical_unknown"] in {True, False}
        and all(row["technical_unknown"] in {True, False} for row in searches),
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
        raise AssertionError("MOLIT I0204 bounded UQQ700 title search validation failed")


if __name__ == "__main__":
    main()
