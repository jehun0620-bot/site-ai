# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_krihs_search_contract_semantic_dedup_hardening.json"
OUT = OUT_DIR / "development_density_management_area_krihs_bounded_uqq700_target_search.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
EXPECTED_ACTION = "https://www.krihs.re.kr/aivorySearch.es?mid=a11800000000"
EXPECTED_METHOD = "POST"
EXPECTED_FIELD = "allKeyWord"
ENTRY_URL = "https://www.krihs.re.kr/"
QUERIES = [
    ("EXACT", "개발밀도관리구역"),
    ("VARIANT", "개발밀도 관리구역"),
    ("WEAK", "개발밀도"),
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_space(value: str):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def strip_tags(value: str):
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


def body_signature(text: str):
    normalized = normalize_space(text)
    return {
        "chars": len(text or ""),
        "normalized_chars": len(normalized),
        "sha256": hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest(),
    }


def extract_csrf(html: str):
    patterns = [
        r'<input[^>]+name=["\']_csrf["\'][^>]+value=["\']([^"\']+)',
        r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']_csrf["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "", flags=re.I)
        if match:
            return unescape(match.group(1))
    return None


def extract_result_rows(html: str, limit: int = 30):
    rows = []
    seen = set()
    anchor_re = re.compile(
        r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        flags=re.I | re.S,
    )
    for match in anchor_re.finditer(html or ""):
        href = unescape(match.group(1)).strip()
        title = strip_tags(match.group(2))
        if not href or not title or len(title) < 2:
            continue
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        key = (title, href)
        if key in seen:
            continue
        seen.add(key)
        left = max(0, match.start() - 300)
        right = min(len(html), match.end() + 500)
        snippet = strip_tags(html[left:right])
        rows.append({
            "title": title[:300],
            "url": urljoin(EXPECTED_ACTION, href),
            "snippet": snippet[:700],
        })
        if len(rows) >= limit:
            break
    return rows


def count_term_occurrences(text: str, term: str):
    compact_text = normalize_space(text)
    compact_term = normalize_space(term)
    return compact_text.count(compact_term) if compact_term else 0


def validate_contract(prev: dict):
    contracts = prev.get("canonical_contracts") or []
    return (
        prev.get("contract_qualified") is True
        and prev.get("semantic_unique_contract_count") == 1
        and len(contracts) == 1
        and str(contracts[0].get("method") or "").upper() == EXPECTED_METHOD
        and contracts[0].get("action") == EXPECTED_ACTION
        and contracts[0].get("field") == EXPECTED_FIELD
        and contracts[0].get("all_runs_credible") is True
        and contracts[0].get("run_consistent") is True
    )


def run_query(session: requests.Session, csrf: str | None, query_class: str, term: str):
    payload = {EXPECTED_FIELD: term}
    if csrf:
        payload["_csrf"] = csrf

    row = {
        "query_class": query_class,
        "term": term,
        "method": EXPECTED_METHOD,
        "action": EXPECTED_ACTION,
        "field": EXPECTED_FIELD,
        "csrf_preserved": bool(csrf),
        "http": None,
        "final_url": None,
        "content_type": None,
        "response_signature": None,
        "term_occurrence_count": 0,
        "candidate_result_count": 0,
        "candidate_results": [],
        "parser_status": "NOT_RUN",
        "technical_unknown": True,
        "error": None,
    }

    try:
        response = session.post(EXPECTED_ACTION, data=payload, timeout=30)
        response.raise_for_status()
        text = response.text or ""
        candidates = extract_result_rows(text)
        row.update({
            "http": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("Content-Type"),
            "response_signature": body_signature(text),
            "term_occurrence_count": count_term_occurrences(text, term),
            "candidate_result_count": len(candidates),
            "candidate_results": candidates,
            "parser_status": "PARSED_GENERIC_ANCHOR_CANDIDATES",
            "technical_unknown": False,
        })
    except Exception as exc:
        row["parser_status"] = "TECHNICAL_UNKNOWN"
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main():
    print("=" * 78)
    print("KRIHS BOUNDED UQQ700 TARGET SEARCH")
    print("=" * 78)
    print("Purpose: bounded exact/variant/weak discovery through one qualified KRIHS contract")
    print("Search hit != designation/current validity/site inclusion")
    print("Search no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    contract_qualified = validate_contract(prev)
    if not contract_qualified:
        raise AssertionError("Qualified semantic KRIHS contract prerequisite not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 bounded KRIHS probe)",
        "Referer": ENTRY_URL,
    })

    csrf = None
    entry_http = None
    entry_error = None
    try:
        entry = session.get(ENTRY_URL, timeout=30)
        entry.raise_for_status()
        entry_http = entry.status_code
        csrf = extract_csrf(entry.text)
    except Exception as exc:
        entry_error = f"{type(exc).__name__}: {exc}"

    runs = [run_query(session, csrf, query_class, term) for query_class, term in QUERIES]
    technical_unknown_count = sum(1 for row in runs if row["technical_unknown"] is True)
    executed_count = len(runs)
    all_queries_executed = executed_count == len(QUERIES)
    transport_clean = technical_unknown_count == 0

    classification = (
        "KRIHS_BOUNDED_UQQ700_TARGET_SEARCH_EXECUTED"
        if all_queries_executed and transport_clean
        else "KRIHS_BOUNDED_UQQ700_TARGET_SEARCH_TECHNICAL_UNKNOWN"
    )
    next_action = (
        "REVIEW_ONLY_IDENTIFIABLE_KRIHS_RESULT_DOCUMENTS_AS_NON_DISPOSITIVE_DISCOVERY_LEADS"
        if transport_clean
        else "HARDEN_ONLY_THE_KRIHS_TARGET_SEARCH_TRANSPORT_OR_PARSER_WITHOUT_LEGAL_INFERENCE"
    )

    out = {
        "step": "STEP 17-KRIHS-BOUNDED-UQQ700-TARGET-SEARCH",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "input_semantic_dedup_loaded": True,
        "contract_qualified": contract_qualified,
        "canonical_contract": {
            "method": EXPECTED_METHOD,
            "action": EXPECTED_ACTION,
            "field": EXPECTED_FIELD,
        },
        "bounded_query_order": [row[0] for row in QUERIES],
        "uqq700_target_search_executed": all_queries_executed,
        "entry_http": entry_http,
        "entry_csrf_found": bool(csrf),
        "entry_error": entry_error,
        "runs": runs,
        "technical_unknown_count": technical_unknown_count,
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
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("SEARCH RESULT")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry_http}")
    print(f"ENTRY CSRF FOUND: {bool(csrf)}")
    for row in runs:
        print(
            f'{row["query_class"]}: term={row["term"]!r} http={row["http"]} '
            f'term_occurrences={row["term_occurrence_count"]} '
            f'candidate_results={row["candidate_result_count"]} '
            f'technical_unknown={row["technical_unknown"]}'
        )

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Search hit == designation: False")
    print("Search hit == current validity: False")
    print("Search hit == site inclusion: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "semantic dedup prerequisite loaded": out["input_semantic_dedup_loaded"] is True,
        "canonical contract qualified": out["contract_qualified"] is True,
        "bounded query count exactly three": len(out["runs"]) == 3,
        "bounded query order exact variant weak": [r["query_class"] for r in out["runs"]] == ["EXACT", "VARIANT", "WEAK"],
        "bounded query terms exact": [r["term"] for r in out["runs"]] == ["개발밀도관리구역", "개발밀도 관리구역", "개발밀도"],
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
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("KRIHS bounded UQQ700 target search validation failed")


if __name__ == "__main__":
    main()
