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
OUT_PATH = OUT_DIR / "development_density_management_area_molit_i0204_post_search_contract_positive_control_test.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
LIST_URL = "https://www.molit.go.kr/USR/I0204/m_45/lst.jsp"
OFFICIAL_HOSTS = {"www.molit.go.kr", "molit.go.kr"}

POSITIVE_CONTROL_TITLE = "기존주택등 매입임대주택 업무처리지침 일부개정"
POSITIVE_CONTROL_IDX = "18945"
PSIZE = "10"


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


def baseline_payload() -> dict[str, str]:
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
        "search": "",
        "psize": PSIZE,
    }


def post_title_payload(title: str) -> dict[str, str]:
    payload = baseline_payload()
    payload.update(
        {
            "search": title,
            "srch_usr_titl": "Y",
        }
    )
    return payload


def request_get(session: requests.Session, params: dict[str, str]) -> dict:
    out = {
        "method": "GET",
        "params": params,
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "rows": [],
        "technical_unknown": True,
        "error": None,
    }
    try:
        r = session.get(LIST_URL, params=params, timeout=30, allow_redirects=True)
        out["http"] = r.status_code
        out["final_url"] = r.url
        out["official_final_host"] = urlparse(r.url).netloc in OFFICIAL_HOSTS
        out["page_title"] = page_title(r.text)
        r.raise_for_status()
        out["rows"] = extract_detail_rows(r.text)
        out["technical_unknown"] = False
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def request_post(session: requests.Session, data: dict[str, str]) -> dict:
    out = {
        "method": "POST",
        "data": data,
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "rows": [],
        "technical_unknown": True,
        "error": None,
    }
    try:
        r = session.post(LIST_URL, data=data, timeout=30, allow_redirects=True)
        out["http"] = r.status_code
        out["final_url"] = r.url
        out["official_final_host"] = urlparse(r.url).netloc in OFFICIAL_HOSTS
        out["page_title"] = page_title(r.text)
        r.raise_for_status()
        out["rows"] = extract_detail_rows(r.text)
        out["technical_unknown"] = False
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def idx_set(rows: list[dict]) -> set[str]:
    return {str(row.get("idx")) for row in rows if row.get("idx") is not None}


def main() -> None:
    print("=" * 78)
    print("MOLIT I0204 POST SEARCH CONTRACT POSITIVE CONTROL TEST")
    print("=" * 78)
    print("Purpose: verify the actual POST title-search contract using an off-first-page official positive control")
    print("UQQ700 term is NOT queried in this step")
    print("Positive-control success != designation/current validity/site inclusion")
    print("Positive-control failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 MOLIT POST search qualification)",
            "Referer": LIST_URL,
        }
    )

    baseline = request_get(session, baseline_payload())
    post_search = request_post(session, post_title_payload(POSITIVE_CONTROL_TITLE))

    baseline_ids = idx_set(baseline["rows"])
    post_ids = idx_set(post_search["rows"])

    positive_absent_from_baseline = POSITIVE_CONTROL_IDX not in baseline_ids
    positive_idx_match = POSITIVE_CONTROL_IDX in post_ids
    expected_title = normalize_space(POSITIVE_CONTROL_TITLE)
    positive_title_match = any(
        str(row.get("idx")) == POSITIVE_CONTROL_IDX
        and normalize_space(str(row.get("title") or "")) == expected_title
        for row in post_search["rows"]
    )
    changed_vs_baseline = post_ids != baseline_ids
    narrowed_or_changed = len(post_search["rows"]) != len(baseline["rows"]) or changed_vs_baseline

    contract_qualified = bool(
        baseline["technical_unknown"] is False
        and post_search["technical_unknown"] is False
        and baseline["http"] == 200
        and post_search["http"] == 200
        and baseline["official_final_host"]
        and post_search["official_final_host"]
        and positive_absent_from_baseline
        and positive_idx_match
        and positive_title_match
        and changed_vs_baseline
    )

    if baseline["technical_unknown"] or post_search["technical_unknown"]:
        classification = "MOLIT_I0204_POST_SEARCH_CONTRACT_POSITIVE_CONTROL_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_POST_TRANSPORT_OR_RESPONSE_PARSING_BEFORE_ANY_UQQ700_QUERY"
    elif contract_qualified:
        classification = "MOLIT_I0204_POST_TITLE_SEARCH_CONTRACT_POSITIVE_CONTROL_QUALIFIED"
        next_action = "RUN_BOUNDED_UQQ700_EXACT_VARIANT_WEAK_SEARCH_USING_ONLY_THE_QUALIFIED_POST_TITLE_CONTRACT"
    else:
        classification = "MOLIT_I0204_POST_TITLE_SEARCH_CONTRACT_POSITIVE_CONTROL_NOT_QUALIFIED"
        next_action = "RECOVER_ANY_REMAINING_REQUIRED_POST_FIELDS_OR_CHECKBOX_COMBINATION_BEFORE_ANY_UQQ700_QUERY"

    out = {
        "step": "STEP17-MOLIT-I0204-POST-SEARCH-CONTRACT-POSITIVE-CONTROL",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "list_url": LIST_URL,
        "positive_control": {
            "title": POSITIVE_CONTROL_TITLE,
            "idx": POSITIVE_CONTROL_IDX,
        },
        "uqq700_query_executed": False,
        "baseline": baseline,
        "post_search": post_search,
        "positive_absent_from_baseline": positive_absent_from_baseline,
        "positive_idx_match": positive_idx_match,
        "positive_title_match": positive_title_match,
        "changed_vs_baseline": changed_vs_baseline,
        "narrowed_or_changed": narrowed_or_changed,
        "contract_qualified": contract_qualified,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "positive_control_success_equals_designation": False,
            "positive_control_success_equals_current_validity": False,
            "positive_control_success_equals_site_inclusion": False,
            "positive_control_failure_equals_legal_absence": False,
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
    print("BASELINE")
    print("=" * 78)
    print(
        f"GET http={baseline['http']} rows={len(baseline['rows'])} "
        f"technical_unknown={baseline['technical_unknown']}"
    )
    print(f"final={baseline['final_url']}")
    for row in baseline["rows"][:20]:
        print(f"  BASELINE idx={row['idx']} title={row['title']}")

    print("\n" + "=" * 78)
    print("POST TITLE SEARCH")
    print("=" * 78)
    print(f"POST data={post_title_payload(POSITIVE_CONTROL_TITLE)}")
    print(
        f"http={post_search['http']} rows={len(post_search['rows'])} "
        f"technical_unknown={post_search['technical_unknown']}"
    )
    print(f"final={post_search['final_url']}")
    for row in post_search["rows"][:30]:
        print(f"  RESULT idx={row['idx']} title={row['title']}")
        print(f"    url={row['absolute_url']}")

    print("\n" + "=" * 78)
    print("QUALIFICATION")
    print("=" * 78)
    print(f"Positive absent from baseline: {positive_absent_from_baseline}")
    print(f"Positive idx match: {positive_idx_match}")
    print(f"Positive title match: {positive_title_match}")
    print(f"Changed vs baseline: {changed_vs_baseline}")
    print(f"Narrowed or changed: {narrowed_or_changed}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("UQQ700 query executed: False")
    print("Positive-control success == designation: False")
    print("Positive-control success == current validity: False")
    print("Positive-control success == site inclusion: False")
    print("Positive-control failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET_NAME,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "official list URL fixed": out["list_url"] == LIST_URL,
        "positive control title fixed": out["positive_control"]["title"] == POSITIVE_CONTROL_TITLE,
        "positive control idx fixed": out["positive_control"]["idx"] == POSITIVE_CONTROL_IDX,
        "POST search used": out["post_search"]["method"] == "POST",
        "search carries title text": out["post_search"]["data"].get("search") == POSITIVE_CONTROL_TITLE,
        "title checkbox enabled": out["post_search"]["data"].get("srch_usr_titl") == "Y",
        "UQQ700 not queried": out["uqq700_query_executed"] is False,
        "positive-control success not designation": out["summary"]["positive_control_success_equals_designation"] is False,
        "positive-control success not validity": out["summary"]["positive_control_success_equals_current_validity"] is False,
        "positive-control success not site inclusion": out["summary"]["positive_control_success_equals_site_inclusion"] is False,
        "positive-control failure not legal absence": out["summary"]["positive_control_failure_equals_legal_absence"] is False,
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
        raise AssertionError("MOLIT I0204 POST search contract positive-control validation failed")


if __name__ == "__main__":
    main()
