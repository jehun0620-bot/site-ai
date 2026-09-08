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
OUT_PATH = OUT_DIR / "development_density_management_area_molit_i0204_search_contract_positive_control_test.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

LIST_URL = "https://www.molit.go.kr/USR/I0204/m_45/lst.jsp"
OFFICIAL_HOSTS = {"www.molit.go.kr", "molit.go.kr"}

# Current-list positive control captured from the qualified official entry surface.
POSITIVE_CONTROL_TITLE = "상습체불건설사업자 명단공표 업무처리 지침 제정 고시"
POSITIVE_CONTROL_IDX = "18951"

# Bounded contract candidates only. UQQ700 is deliberately not queried in this step.
SEARCH_CASES = [
    {
        "name": "TITLE_FIELD_EXACT",
        "params": {
            "srch_usr_titl": POSITIVE_CONTROL_TITLE,
            "search": "",
            "lcmspage": "1",
            "psize": "10",
        },
    },
    {
        "name": "SEARCH_FIELD_EXACT",
        "params": {
            "srch_usr_titl": "",
            "search": POSITIVE_CONTROL_TITLE,
            "lcmspage": "1",
            "psize": "10",
        },
    },
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
                "text": text,
                "href": href,
                "absolute_url": absolute,
                "host": parsed.netloc,
                "idx": idx,
            }
        )
    return rows


def title_normalized(value: str) -> str:
    return re.sub(r"\s+", "", normalize_space(value))


def evaluate_case(session: requests.Session, case: dict, base_defaults: dict[str, str], action: str) -> dict:
    params = {
        "gubun": base_defaults.get("gubun", ""),
        "flag": base_defaults.get("flag", ""),
        "r_id": base_defaults.get("r_id", ""),
        "lcmspage": "1",
        "search_dept_id": base_defaults.get("search_dept_id", ""),
        "search_dept_nm": base_defaults.get("search_dept_nm", ""),
        "search_regdate_s": base_defaults.get("search_regdate_s", ""),
        "search_regdate_e": base_defaults.get("search_regdate_e", ""),
        "srch_usr_year": base_defaults.get("srch_usr_year", ""),
        "srch_usr_num": base_defaults.get("srch_usr_num", ""),
        "srch_usr_nm": base_defaults.get("srch_usr_nm", ""),
        "srch_usr_titl": base_defaults.get("srch_usr_titl", ""),
        "srch_usr_ctnt": base_defaults.get("srch_usr_ctnt", ""),
        "search": base_defaults.get("search", ""),
        "psize": base_defaults.get("psize", "10") or "10",
    }
    params.update(case["params"])

    result = {
        "name": case["name"],
        "method": "GET",
        "endpoint": action,
        "params": params,
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "technical_unknown": True,
        "result_detail_count": 0,
        "positive_title_matches": 0,
        "positive_idx_matches": 0,
        "positive_control_resolved": False,
        "matched_rows": [],
        "error": None,
    }

    try:
        r = session.get(action, params=params, timeout=30, allow_redirects=True)
        result["http"] = r.status_code
        result["final_url"] = r.url
        result["official_final_host"] = urlparse(r.url).netloc in OFFICIAL_HOSTS
        result["page_title"] = page_title(r.text)
        r.raise_for_status()

        rows = extract_detail_rows(r.text)
        result["result_detail_count"] = len(rows)
        expected_norm = title_normalized(POSITIVE_CONTROL_TITLE)
        matched_rows = []
        title_matches = 0
        idx_matches = 0
        for row in rows:
            row_title_match = expected_norm in title_normalized(row["text"])
            row_idx_match = row["idx"] == POSITIVE_CONTROL_IDX
            if row_title_match:
                title_matches += 1
            if row_idx_match:
                idx_matches += 1
            if row_title_match or row_idx_match:
                matched_rows.append({**row, "title_match": row_title_match, "idx_match": row_idx_match})

        result["positive_title_matches"] = title_matches
        result["positive_idx_matches"] = idx_matches
        result["matched_rows"] = matched_rows[:20]
        result["positive_control_resolved"] = bool(
            r.status_code == 200
            and result["official_final_host"]
            and title_matches > 0
            and idx_matches > 0
            and any(row["title_match"] and row["idx_match"] for row in matched_rows)
        )
        result["technical_unknown"] = False
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result


def main() -> None:
    print("=" * 78)
    print("MOLIT I0204 SEARCH CONTRACT POSITIVE CONTROL TEST")
    print("=" * 78)
    print("Purpose: qualify the official MOLIT I0204 list search contract using a known current-list document")
    print("Positive-control search != designation/current validity/site inclusion")
    print("Positive-control failure != legal absence")
    print("UQQ700 term is NOT queried in this step")
    print("UQQ700 final resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 MOLIT I0204 contract qualification)",
            "Referer": "https://www.molit.go.kr/",
        }
    )

    entry = {
        "url": LIST_URL,
        "http": None,
        "final_url": None,
        "official_final_host": False,
        "page_title": None,
        "form_contract": {},
        "technical_unknown": True,
        "error": None,
    }

    cases: list[dict] = []
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
        cases = [evaluate_case(session, case, defaults, action) for case in SEARCH_CASES]
    except Exception as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"

    title_case = next((row for row in cases if row["name"] == "TITLE_FIELD_EXACT"), None)
    search_case = next((row for row in cases if row["name"] == "SEARCH_FIELD_EXACT"), None)

    contract_qualified = bool(
        entry["technical_unknown"] is False
        and entry["http"] == 200
        and entry["official_final_host"]
        and entry["form_contract"].get("method") == "GET"
        and urlparse(entry["form_contract"].get("action", "")).path.endswith("/USR/I0204/m_45/lst.jsp")
        and "srch_usr_titl" in entry["form_contract"].get("fields", [])
    )

    title_field_qualified = bool(title_case and title_case["positive_control_resolved"])
    search_field_qualified = bool(search_case and search_case["positive_control_resolved"])

    if any(row.get("technical_unknown") for row in cases) or entry["technical_unknown"]:
        classification = "MOLIT_I0204_SEARCH_CONTRACT_POSITIVE_CONTROL_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_THE_OFFICIAL_SEARCH_REPLAY_TRANSPORT_OR_PARSING_BEFORE_ANY_UQQ700_QUERY"
    elif contract_qualified and title_field_qualified:
        classification = "MOLIT_I0204_TITLE_SEARCH_CONTRACT_POSITIVE_CONTROL_QUALIFIED"
        next_action = "RUN_BOUNDED_UQQ700_EXACT_VARIANT_WEAK_SEARCH_USING_ONLY_THE_QUALIFIED_TITLE_CONTRACT"
    elif contract_qualified and search_field_qualified:
        classification = "MOLIT_I0204_GENERIC_SEARCH_FIELD_POSITIVE_CONTROL_QUALIFIED"
        next_action = "REVIEW_GENERIC_SEARCH_FIELD_SEMANTICS_BEFORE_ANY_BOUNDED_UQQ700_QUERY"
    elif contract_qualified:
        classification = "MOLIT_I0204_FORM_CONTRACT_QUALIFIED_BUT_POSITIVE_CONTROL_UNRESOLVED"
        next_action = "RECOVER_SUBMIT_SEMANTICS_OR_REQUIRED_DEFAULT_FIELDS_WITHOUT_LEGAL_INFERENCE"
    else:
        classification = "MOLIT_I0204_SEARCH_CONTRACT_NOT_QUALIFIED"
        next_action = "INSPECT_ONLY_THE_OFFICIAL_LIST_FORM_CONTRACT_WITHOUT_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP17-MOLIT-I0204-SEARCH-CONTRACT-POSITIVE-CONTROL",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "list_url": LIST_URL,
        "positive_control": {
            "title": POSITIVE_CONTROL_TITLE,
            "idx": POSITIVE_CONTROL_IDX,
        },
        "uqq700_query_executed": False,
        "entry": entry,
        "cases": cases,
        "contract_qualified": contract_qualified,
        "title_field_qualified": title_field_qualified,
        "search_field_qualified": search_field_qualified,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "search_contract_equals_designation": False,
            "search_contract_equals_current_validity": False,
            "search_contract_equals_site_inclusion": False,
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
    print("SEARCH CONTRACT RESULT")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry['http']}")
    print(f"ENTRY FINAL: {entry['final_url']}")
    print(f"FORM METHOD: {entry['form_contract'].get('method')}")
    print(f"FORM ACTION: {entry['form_contract'].get('action')}")
    print(f"FORM FIELDS: {entry['form_contract'].get('fields')}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    for row in cases:
        print(
            f"{row['name']}: http={row['http']} details={row['result_detail_count']} "
            f"title_matches={row['positive_title_matches']} idx_matches={row['positive_idx_matches']} "
            f"resolved={row['positive_control_resolved']} technical_unknown={row['technical_unknown']}"
        )
        print(f"    final={row['final_url']}")
        for matched in row["matched_rows"][:5]:
            print(
                f"    MATCH idx={matched['idx']} title_match={matched['title_match']} "
                f"idx_match={matched['idx_match']} text={matched['text']}"
            )
            print(f"      url={matched['absolute_url']}")
        if row["error"]:
            print(f"    error={row['error']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"Title field qualified: {title_field_qualified}")
    print(f"Generic search field qualified: {search_field_qualified}")
    print("UQQ700 query executed: False")
    print("Search contract == designation: False")
    print("Search contract == current validity: False")
    print("Search contract == site inclusion: False")
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
        "UQQ700 not queried": out["uqq700_query_executed"] is False,
        "technical state explicit": entry["technical_unknown"] in {True, False}
        and all(row["technical_unknown"] in {True, False} for row in cases),
        "search contract not designation": out["summary"]["search_contract_equals_designation"] is False,
        "search contract not validity": out["summary"]["search_contract_equals_current_validity"] is False,
        "search contract not site inclusion": out["summary"]["search_contract_equals_site_inclusion"] is False,
        "positive control failure not legal absence": out["summary"]["positive_control_failure_equals_legal_absence"] is False,
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
        raise AssertionError("MOLIT I0204 search contract positive-control validation failed")


if __name__ == "__main__":
    main()
