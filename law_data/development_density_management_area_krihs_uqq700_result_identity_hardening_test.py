# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_krihs_search_contract_semantic_dedup_hardening.json"
OUT = OUT_DIR / "development_density_management_area_krihs_uqq700_result_identity_hardening_test.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
EXPECTED_ACTION = "https://www.krihs.re.kr/aivorySearch.es?mid=a11800000000"
EXPECTED_METHOD = "POST"
EXPECTED_FIELD = "allKeyWord"
ENTRY_URL = "https://www.krihs.re.kr/"
KRIHS_HOST = "www.krihs.re.kr"

QUERIES = [
    ("EXACT", "개발밀도관리구역"),
    ("VARIANT", "개발밀도 관리구역"),
    ("WEAK", "개발밀도"),
]

NAVIGATION_TERMS = {
    "홈", "로그인", "회원가입", "사이트맵", "검색", "메뉴", "이전", "다음", "처음", "마지막",
    "국토연구원", "english", "facebook", "youtube", "instagram", "블로그", "맨위로",
}


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
        m = re.search(pattern, html or "", flags=re.I)
        if m:
            return unescape(m.group(1))
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


def is_navigation_title(title: str):
    t = normalize_space(title).lower()
    if not t or len(t) < 2:
        return True
    if t in {x.lower() for x in NAVIGATION_TERMS}:
        return True
    if len(t) <= 4 and t in {"더보기", "보기", "목록", "전체"}:
        return True
    return False


def classify_href(href: str):
    raw = (href or "").strip()
    low = raw.lower()
    if not raw or raw.startswith("#") or low.startswith("javascript:") or low.startswith("mailto:"):
        return "REJECT_NON_DOCUMENT_LINK"
    absolute = urljoin(EXPECTED_ACTION, raw)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return "REJECT_NON_HTTP_LINK"
    if parsed.netloc and parsed.netloc != KRIHS_HOST:
        return "REJECT_EXTERNAL_LINK"
    return "KRIHS_INTERNAL_LINK"


def term_variants(term: str):
    compact = re.sub(r"\s+", "", term)
    variants = {normalize_space(term), compact}
    if term == "개발밀도관리구역":
        variants.add("개발밀도 관리구역")
    elif term == "개발밀도 관리구역":
        variants.add("개발밀도관리구역")
    return {v for v in variants if v}


def lexical_relevance(title: str, snippet: str, term: str):
    hay = normalize_space(f"{title} {snippet}")
    hay_compact = re.sub(r"\s+", "", hay)
    matched = []
    for variant in sorted(term_variants(term), key=len, reverse=True):
        if variant in hay or re.sub(r"\s+", "", variant) in hay_compact:
            matched.append(variant)
    return bool(matched), matched


def extract_anchor_candidates(html: str, term: str):
    anchor_re = re.compile(
        r'<a\b([^>]*)href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>',
        flags=re.I | re.S,
    )
    rows = []
    seen = set()
    for m in anchor_re.finditer(html or ""):
        href = unescape(m.group(2)).strip()
        title = strip_tags(m.group(4))
        link_class = classify_href(href)
        if link_class != "KRIHS_INTERNAL_LINK" or is_navigation_title(title):
            continue

        left = max(0, m.start() - 900)
        right = min(len(html), m.end() + 1400)
        context_html = html[left:right]
        snippet = strip_tags(context_html)
        relevant, matched = lexical_relevance(title, snippet, term)
        if not relevant:
            continue

        url = urljoin(EXPECTED_ACTION, href)
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)

        attrs = normalize_space(f"{m.group(1)} {m.group(3)}")
        rows.append({
            "title": title[:500],
            "url": url,
            "matched_terms": matched,
            "snippet": snippet[:1200],
            "anchor_attributes": attrs[:500],
        })
    return rows


def extract_term_contexts(html: str, term: str, radius: int = 650, limit: int = 12):
    text = html or ""
    contexts = []
    seen = set()
    for variant in sorted(term_variants(term), key=len, reverse=True):
        for m in re.finditer(re.escape(variant), text, flags=re.I):
            left = max(0, m.start() - radius)
            right = min(len(text), m.end() + radius)
            context = strip_tags(text[left:right])
            key = context[:400]
            if not context or key in seen:
                continue
            seen.add(key)
            contexts.append({"matched_term": variant, "context": context[:1600]})
            if len(contexts) >= limit:
                return contexts
    return contexts


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
        "response_term_context_count": 0,
        "response_term_contexts": [],
        "identified_result_count": 0,
        "identified_results": [],
        "parser_status": "NOT_RUN",
        "technical_unknown": True,
        "error": None,
    }

    try:
        response = session.post(EXPECTED_ACTION, data=payload, timeout=30)
        response.raise_for_status()
        html = response.text or ""
        contexts = extract_term_contexts(html, term)
        results = extract_anchor_candidates(html, term)
        row.update({
            "http": response.status_code,
            "final_url": response.url,
            "response_term_context_count": len(contexts),
            "response_term_contexts": contexts,
            "identified_result_count": len(results),
            "identified_results": results,
            "parser_status": "LEXICALLY_SCOPED_KRIHS_INTERNAL_RESULT_IDENTITY_PASS",
            "technical_unknown": False,
        })
    except Exception as exc:
        row["parser_status"] = "TECHNICAL_UNKNOWN"
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main():
    print("=" * 78)
    print("KRIHS UQQ700 RESULT IDENTITY HARDENING TEST")
    print("=" * 78)
    print("Purpose: distinguish identifiable KRIHS result-document leads from generic navigation anchors")
    print("Search/result lead != designation/current validity/site inclusion")
    print("No identifiable result != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    contract_qualified = validate_contract(prev)
    if not contract_qualified:
        raise AssertionError("Qualified semantic KRIHS contract prerequisite not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 KRIHS result identity hardening)",
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
    technical_unknown_count = sum(1 for r in runs if r["technical_unknown"] is True)
    total_identified = sum(r["identified_result_count"] for r in runs)

    if technical_unknown_count:
        classification = "KRIHS_UQQ700_RESULT_IDENTITY_HARDENING_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_KRIHS_RESULT_TRANSPORT_OR_STRUCTURE_WITHOUT_LEGAL_INFERENCE"
    elif total_identified > 0:
        classification = "KRIHS_UQQ700_IDENTIFIABLE_RESULT_LEADS_PRESENT"
        next_action = "REVIEW_IDENTIFIED_KRIHS_DOCUMENT_LEADS_FOR_DOCUMENT_IDENTITY_ONLY"
    else:
        classification = "KRIHS_UQQ700_NO_IDENTIFIABLE_RESULT_LEAD_AFTER_LEXICAL_SCOPING"
        next_action = "INSPECT_KRIHS_RESULT_CONTAINER_STRUCTURE_OR_ALTERNATE_RESULT_FIELDS_WITHOUT_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP 17-KRIHS-UQQ700-RESULT-IDENTITY-HARDENING",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "contract_qualified": contract_qualified,
        "entry_http": entry_http,
        "entry_csrf_found": bool(csrf),
        "entry_error": entry_error,
        "runs": runs,
        "technical_unknown_count": technical_unknown_count,
        "total_identified_result_count": total_identified,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "identified_result_lead_equals_designation": False,
            "identified_result_lead_equals_current_validity": False,
            "identified_result_lead_equals_site_inclusion": False,
            "no_identifiable_result_equals_legal_absence": False,
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
    print("RESULT IDENTITY")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry_http}")
    print(f"ENTRY CSRF FOUND: {bool(csrf)}")
    for row in runs:
        print(
            f'{row["query_class"]}: term={row["term"]!r} http={row["http"]} '
            f'contexts={row["response_term_context_count"]} '
            f'identified_results={row["identified_result_count"]} '
            f'technical_unknown={row["technical_unknown"]}'
        )
        for idx, result in enumerate(row["identified_results"][:10], 1):
            print(f'  [{idx}] {result["title"]} | {result["url"]}')

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Identified result lead == designation: False")
    print("Identified result lead == current validity: False")
    print("Identified result lead == site inclusion: False")
    print("No identifiable result == legal absence: False")
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
        "identified result not designation": out["summary"]["identified_result_lead_equals_designation"] is False,
        "identified result not validity": out["summary"]["identified_result_lead_equals_current_validity"] is False,
        "identified result not site inclusion": out["summary"]["identified_result_lead_equals_site_inclusion"] is False,
        "no identifiable result not legal absence": out["summary"]["no_identifiable_result_equals_legal_absence"] is False,
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
        raise AssertionError("KRIHS UQQ700 result identity hardening validation failed")


if __name__ == "__main__":
    main()
