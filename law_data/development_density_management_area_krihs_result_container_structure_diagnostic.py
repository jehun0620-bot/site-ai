# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_krihs_search_contract_semantic_dedup_hardening.json"
OUT = OUT_DIR / "development_density_management_area_krihs_result_container_structure_diagnostic.json"

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

RAW_CONTEXT_RADIUS = 1800
RAW_CONTEXT_LIMIT = 8
TOKEN_LIMIT = 120


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_space(value: str):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def strip_tags(value: str):
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


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


def term_variants(term: str):
    variants = {normalize_space(term), re.sub(r"\s+", "", term)}
    if term == "개발밀도관리구역":
        variants.add("개발밀도 관리구역")
    elif term == "개발밀도 관리구역":
        variants.add("개발밀도관리구역")
    return [v for v in variants if v]


def extract_raw_contexts(html: str, term: str):
    contexts = []
    seen = set()
    for variant in sorted(term_variants(term), key=len, reverse=True):
        for match in re.finditer(re.escape(variant), html or "", flags=re.I):
            left = max(0, match.start() - RAW_CONTEXT_RADIUS)
            right = min(len(html), match.end() + RAW_CONTEXT_RADIUS)
            raw = (html or "")[left:right]
            key = re.sub(r"\s+", " ", raw[:900])
            if key in seen:
                continue
            seen.add(key)
            contexts.append({
                "matched_term": variant,
                "raw_html": raw[:5000],
                "text_preview": strip_tags(raw)[:1800],
            })
            if len(contexts) >= RAW_CONTEXT_LIMIT:
                return contexts
    return contexts


def extract_attribute_tokens(raw_html: str):
    tokens = []
    seen = set()

    patterns = [
        ("id", r'\bid\s*=\s*["\']([^"\']+)["\']'),
        ("class", r'\bclass\s*=\s*["\']([^"\']+)["\']'),
        ("href", r'\bhref\s*=\s*["\']([^"\']+)["\']'),
        ("onclick", r'\bonclick\s*=\s*["\']([^"\']+)["\']'),
        ("action", r'\baction\s*=\s*["\']([^"\']+)["\']'),
        ("name", r'\bname\s*=\s*["\']([^"\']+)["\']'),
        ("value", r'\bvalue\s*=\s*["\']([^"\']+)["\']'),
        ("data", r'\b(data-[A-Za-z0-9_-]+)\s*=\s*["\']([^"\']*)["\']'),
    ]

    for token_type, pattern in patterns:
        for match in re.finditer(pattern, raw_html or "", flags=re.I):
            if token_type == "data":
                value = f"{match.group(1)}={match.group(2)}"
            else:
                value = match.group(1)
            value = normalize_space(value)
            if not value:
                continue
            key = (token_type, value)
            if key in seen:
                continue
            seen.add(key)
            tokens.append({"type": token_type, "value": value[:700]})
            if len(tokens) >= TOKEN_LIMIT:
                return tokens
    return tokens


def extract_function_calls(raw_html: str):
    calls = []
    seen = set()
    patterns = [
        r'([A-Za-z_$][\w$\.]{1,120})\s*\(([^\)]{0,500})\)',
        r'javascript:\s*([^"\'<>]{1,500})',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, raw_html or "", flags=re.I | re.S):
            value = normalize_space(match.group(0))
            if not value or value in seen:
                continue
            seen.add(value)
            calls.append(value[:900])
            if len(calls) >= 80:
                return calls
    return calls


def extract_url_candidates(raw_html: str):
    urls = []
    seen = set()
    patterns = [
        r'https?://[^\s"\'<>]+',
        r'["\'](/[^"\'<>\s]{2,500})["\']',
        r'["\']([^"\']+\.(?:do|es|jsp|json|xml)(?:\?[^"\']*)?)["\']',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, raw_html or "", flags=re.I):
            value = match.group(1) if match.lastindex else match.group(0)
            value = unescape(value).strip()
            if not value:
                continue
            absolute = urljoin(EXPECTED_ACTION, value)
            if absolute in seen:
                continue
            seen.add(absolute)
            urls.append(absolute[:1200])
            if len(urls) >= 80:
                return urls
    return urls


def extract_identifier_candidates(raw_html: str):
    identifiers = []
    seen = set()
    patterns = [
        ("numeric_id", r'\b(?:id|idx|seq|sn|no|key|doc(?:ument)?id|articleid|boardid)\b\s*[:=]\s*["\']?(\d{2,20})'),
        ("named_param", r'\b([A-Za-z][A-Za-z0-9_]{1,60})\s*=\s*["\']?([A-Za-z0-9_-]{2,120})'),
    ]
    for kind, pattern in patterns:
        for match in re.finditer(pattern, raw_html or "", flags=re.I):
            if kind == "numeric_id":
                value = match.group(1)
            else:
                value = f"{match.group(1)}={match.group(2)}"
            value = normalize_space(value)
            key = (kind, value)
            if not value or key in seen:
                continue
            seen.add(key)
            identifiers.append({"type": kind, "value": value[:300]})
            if len(identifiers) >= 120:
                return identifiers
    return identifiers


def diagnose_context(context: dict):
    raw = context.get("raw_html") or ""
    return {
        "matched_term": context.get("matched_term"),
        "text_preview": context.get("text_preview"),
        "attribute_tokens": extract_attribute_tokens(raw),
        "function_calls": extract_function_calls(raw),
        "url_candidates": extract_url_candidates(raw),
        "identifier_candidates": extract_identifier_candidates(raw),
        "raw_html": raw,
    }


def run_query(session: requests.Session, csrf: str | None, query_class: str, term: str):
    payload = {EXPECTED_FIELD: term}
    if csrf:
        payload["_csrf"] = csrf

    row = {
        "query_class": query_class,
        "term": term,
        "http": None,
        "final_url": None,
        "csrf_preserved": bool(csrf),
        "context_count": 0,
        "contexts": [],
        "technical_unknown": True,
        "error": None,
    }

    try:
        response = session.post(EXPECTED_ACTION, data=payload, timeout=30)
        response.raise_for_status()
        contexts = extract_raw_contexts(response.text or "", term)
        row.update({
            "http": response.status_code,
            "final_url": response.url,
            "context_count": len(contexts),
            "contexts": [diagnose_context(c) for c in contexts],
            "technical_unknown": False,
        })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main():
    print("=" * 78)
    print("KRIHS RESULT CONTAINER STRUCTURE DIAGNOSTIC")
    print("=" * 78)
    print("Purpose: inspect result-container/raw-response structure around bounded UQQ700 search terms")
    print("Structural signal != designation/current validity/site inclusion")
    print("No structural signal != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    contract_qualified = validate_contract(prev)
    if not contract_qualified:
        raise AssertionError("Qualified semantic KRIHS contract prerequisite not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 KRIHS structure diagnostic)",
        "Referer": ENTRY_URL,
    })

    entry_http = None
    csrf = None
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
    total_context_count = sum(row["context_count"] for row in runs)

    if technical_unknown_count:
        classification = "KRIHS_RESULT_CONTAINER_STRUCTURE_DIAGNOSTIC_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_KRIHS_TRANSPORT_OR_CONTEXT_EXTRACTION_WITHOUT_LEGAL_INFERENCE"
    elif total_context_count > 0:
        classification = "KRIHS_RESULT_CONTAINER_STRUCTURE_CONTEXTS_CAPTURED"
        next_action = "REVIEW_STRUCTURE_TOKENS_FOR_A_REAL_RESULT_DETAIL_ENDPOINT_OR_RESULT_CONTAINER_IDENTITY"
    else:
        classification = "KRIHS_RESULT_CONTAINER_STRUCTURE_NO_TERM_CONTEXT_CAPTURED"
        next_action = "INSPECT_ALTERNATE_RESPONSE_FIELDS_OR_CLIENT_SIDE_RESULT_LOADING_WITHOUT_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP 17-KRIHS-RESULT-CONTAINER-STRUCTURE-DIAGNOSTIC",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "contract_qualified": contract_qualified,
        "entry_http": entry_http,
        "entry_csrf_found": bool(csrf),
        "entry_error": entry_error,
        "runs": runs,
        "technical_unknown_count": technical_unknown_count,
        "total_context_count": total_context_count,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "structural_signal_equals_designation": False,
            "structural_signal_equals_current_validity": False,
            "structural_signal_equals_site_inclusion": False,
            "no_structural_signal_equals_legal_absence": False,
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
    print("STRUCTURE RESULT")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry_http}")
    print(f"ENTRY CSRF FOUND: {bool(csrf)}")
    for row in runs:
        print(
            f'{row["query_class"]}: term={row["term"]!r} http={row["http"]} '
            f'contexts={row["context_count"]} technical_unknown={row["technical_unknown"]}'
        )
        for idx, context in enumerate(row["contexts"][:3], 1):
            print(
                f'  [{idx}] attrs={len(context["attribute_tokens"])} '
                f'calls={len(context["function_calls"])} '
                f'urls={len(context["url_candidates"])} '
                f'ids={len(context["identifier_candidates"])}'
            )
            print(f'      text={context["text_preview"][:500]}')

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Structural signal == designation: False")
    print("Structural signal == current validity: False")
    print("Structural signal == site inclusion: False")
    print("No structural signal == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "canonical contract qualified": out["contract_qualified"] is True,
        "bounded query count exactly three": len(out["runs"]) == 3,
        "bounded query order exact variant weak": [r["query_class"] for r in out["runs"]] == ["EXACT", "VARIANT", "WEAK"],
        "technical state explicit": all("technical_unknown" in r for r in out["runs"]),
        "structural signal not designation": out["summary"]["structural_signal_equals_designation"] is False,
        "structural signal not validity": out["summary"]["structural_signal_equals_current_validity"] is False,
        "structural signal not site inclusion": out["summary"]["structural_signal_equals_site_inclusion"] is False,
        "no structural signal not legal absence": out["summary"]["no_structural_signal_equals_legal_absence"] is False,
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
        raise AssertionError("KRIHS result container structure diagnostic validation failed")


if __name__ == "__main__":
    main()
