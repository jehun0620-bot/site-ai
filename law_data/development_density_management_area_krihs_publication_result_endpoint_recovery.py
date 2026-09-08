# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_krihs_search_contract_semantic_dedup_hardening.json"
OUT = OUT_DIR / "development_density_management_area_krihs_publication_result_endpoint_recovery.json"

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

PUBLICATION_LABELS = ("발간물", "연구보고서", "정기간행물", "국토정책 Brief", "국토정책Brief")
CONTEXT_RADIUS = 5000
MAX_CONTEXTS = 10
MAX_CANDIDATES = 60


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


def term_variants(term: str):
    variants = {normalize_space(term), re.sub(r"\s+", "", term)}
    if term == "개발밀도관리구역":
        variants.add("개발밀도 관리구역")
    elif term == "개발밀도 관리구역":
        variants.add("개발밀도관리구역")
    return [v for v in variants if v]


def capture_publication_contexts(html: str, term: str):
    text = html or ""
    positions = []
    for label in PUBLICATION_LABELS:
        for m in re.finditer(re.escape(label), text, flags=re.I):
            positions.append((m.start(), f"publication_label:{label}"))
    for variant in term_variants(term):
        for m in re.finditer(re.escape(variant), text, flags=re.I):
            positions.append((m.start(), f"term:{variant}"))

    contexts = []
    seen = set()
    for pos, trigger in sorted(positions):
        left = max(0, pos - CONTEXT_RADIUS)
        right = min(len(text), pos + CONTEXT_RADIUS)
        raw = text[left:right]
        plain = strip_tags(raw)
        if not any(label in plain for label in PUBLICATION_LABELS):
            continue
        key = plain[:1200]
        if not key or key in seen:
            continue
        seen.add(key)
        contexts.append({"trigger": trigger, "raw_html": raw, "text_preview": plain[:3000]})
        if len(contexts) >= MAX_CONTEXTS:
            break
    return contexts


def parse_js_arguments(arg_text: str):
    args = []
    for token in re.findall(r'["\']([^"\']*)["\']|([^,\s\)]+)', arg_text or ""):
        value = token[0] or token[1]
        value = normalize_space(value)
        if value:
            args.append(value)
    return args


def candidate_score(title: str, raw: str):
    text = normalize_space(f"{title} {strip_tags(raw)}")
    score = 0
    for label in PUBLICATION_LABELS:
        if label in text:
            score += 3
    if "저자" in text:
        score += 2
    if "발행일" in text or "등록일" in text:
        score += 2
    if re.search(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}", text):
        score += 2
    if title and len(title) >= 8:
        score += 1
    return score


def extract_endpoint_candidates(context_raw: str):
    candidates = []
    seen = set()

    anchor_re = re.compile(r'<a\b([^>]*)href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>', re.I | re.S)
    for m in anchor_re.finditer(context_raw or ""):
        href = unescape(m.group(2)).strip()
        title = strip_tags(m.group(4))
        attrs = normalize_space(f"{m.group(1)} {m.group(3)}")
        if not href or href.startswith("#"):
            continue
        if href.lower().startswith("javascript:"):
            js = href[len("javascript:"):]
            fm = re.match(r'\s*([A-Za-z_$][\w$\.]*)\s*\((.*)\)\s*;?\s*$', js, re.S)
            function_name = fm.group(1) if fm else None
            function_args = parse_js_arguments(fm.group(2)) if fm else []
            key = ("javascript", title, js)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "candidate_type": "JAVASCRIPT_HREF",
                "title": title[:500],
                "raw_href": href[:1200],
                "absolute_url": None,
                "function_name": function_name,
                "function_args": function_args,
                "onclick": None,
                "attributes": attrs[:1000],
                "query_params": [],
                "publication_score": candidate_score(title, m.group(0)),
            })
        else:
            absolute = urljoin(EXPECTED_ACTION, href)
            parsed = urlparse(absolute)
            if parsed.netloc and parsed.netloc != KRIHS_HOST:
                continue
            key = ("href", title, absolute)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "candidate_type": "DIRECT_HREF",
                "title": title[:500],
                "raw_href": href[:1200],
                "absolute_url": absolute[:1600],
                "function_name": None,
                "function_args": [],
                "onclick": None,
                "attributes": attrs[:1000],
                "query_params": list(parse_qsl(parsed.query, keep_blank_values=True)),
                "publication_score": candidate_score(title, m.group(0)),
            })

    onclick_re = re.compile(r'<([A-Za-z0-9]+)\b([^>]*)\bonclick=["\']([^"\']+)["\']([^>]*)>(.*?)</\1>', re.I | re.S)
    for m in onclick_re.finditer(context_raw or ""):
        onclick = unescape(m.group(3)).strip()
        title = strip_tags(m.group(5))
        fm = re.search(r'([A-Za-z_$][\w$\.]*)\s*\(([^\)]*)\)', onclick, re.S)
        function_name = fm.group(1) if fm else None
        function_args = parse_js_arguments(fm.group(2)) if fm else []
        key = ("onclick", title, onclick)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "candidate_type": "ONCLICK",
            "title": title[:500],
            "raw_href": None,
            "absolute_url": None,
            "function_name": function_name,
            "function_args": function_args,
            "onclick": onclick[:1200],
            "attributes": normalize_space(f"{m.group(2)} {m.group(4)}")[:1000],
            "query_params": [],
            "publication_score": candidate_score(title, m.group(0)),
        })

    candidates.sort(key=lambda x: (-x["publication_score"], x.get("title") or ""))
    return candidates[:MAX_CANDIDATES]


def extract_function_definitions(html: str, function_names: set[str]):
    definitions = []
    for name in sorted(n for n in function_names if n):
        leaf = name.split(".")[-1]
        patterns = [
            rf'function\s+{re.escape(leaf)}\s*\([^\)]*\)\s*\{{',
            rf'{re.escape(leaf)}\s*=\s*function\s*\([^\)]*\)\s*\{{',
        ]
        for pattern in patterns:
            m = re.search(pattern, html or "", flags=re.I | re.S)
            if not m:
                continue
            left = m.start()
            right = min(len(html), m.start() + 4500)
            definitions.append({
                "function_name": name,
                "definition_preview": (html or "")[left:right],
            })
            break
    return definitions


def probe_direct_candidate(session: requests.Session, candidate: dict):
    url = candidate.get("absolute_url")
    if not url or candidate.get("publication_score", 0) < 3:
        return None
    result = {
        "url": url,
        "http": None,
        "final_url": None,
        "content_type": None,
        "title_signal": None,
        "technical_unknown": True,
        "error": None,
    }
    try:
        response = session.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        title_match = re.search(r'<title[^>]*>(.*?)</title>', response.text or "", flags=re.I | re.S)
        result.update({
            "http": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("Content-Type"),
            "title_signal": strip_tags(title_match.group(1))[:500] if title_match else None,
            "technical_unknown": False,
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def run_query(session: requests.Session, csrf: str | None, query_class: str, term: str):
    payload = {EXPECTED_FIELD: term}
    if csrf:
        payload["_csrf"] = csrf

    row = {
        "query_class": query_class,
        "term": term,
        "http": None,
        "final_url": None,
        "context_count": 0,
        "endpoint_candidate_count": 0,
        "endpoint_candidates": [],
        "function_definitions": [],
        "direct_candidate_probes": [],
        "technical_unknown": True,
        "error": None,
    }

    try:
        response = session.post(EXPECTED_ACTION, data=payload, timeout=30)
        response.raise_for_status()
        html = response.text or ""
        contexts = capture_publication_contexts(html, term)

        all_candidates = []
        seen = set()
        for context in contexts:
            for candidate in extract_endpoint_candidates(context["raw_html"]):
                key = (
                    candidate.get("candidate_type"),
                    candidate.get("title"),
                    candidate.get("absolute_url"),
                    candidate.get("onclick"),
                    candidate.get("raw_href"),
                )
                if key in seen:
                    continue
                seen.add(key)
                all_candidates.append(candidate)

        all_candidates.sort(key=lambda x: (-x["publication_score"], x.get("title") or ""))
        all_candidates = all_candidates[:MAX_CANDIDATES]
        function_names = {c.get("function_name") for c in all_candidates if c.get("function_name")}
        function_defs = extract_function_definitions(html, function_names)

        probes = []
        for candidate in all_candidates[:20]:
            probe = probe_direct_candidate(session, candidate)
            if probe is not None:
                probes.append(probe)

        row.update({
            "http": response.status_code,
            "final_url": response.url,
            "context_count": len(contexts),
            "endpoint_candidate_count": len(all_candidates),
            "endpoint_candidates": all_candidates,
            "function_definitions": function_defs,
            "direct_candidate_probes": probes,
            "technical_unknown": False,
        })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main():
    print("=" * 78)
    print("KRIHS PUBLICATION RESULT ENDPOINT RECOVERY")
    print("=" * 78)
    print("Purpose: recover publication result detail href/onclick/function arguments and verify direct endpoints")
    print("Recovered publication endpoint != designation/current validity/site inclusion")
    print("No recovered endpoint != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    contract_qualified = validate_contract(prev)
    if not contract_qualified:
        raise AssertionError("Qualified semantic KRIHS contract prerequisite not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 KRIHS publication endpoint recovery)",
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
    total_candidates = sum(row["endpoint_candidate_count"] for row in runs)
    successful_direct_probes = sum(
        1 for row in runs for probe in row["direct_candidate_probes"]
        if probe.get("technical_unknown") is False and probe.get("http") == 200
    )

    if technical_unknown_count:
        classification = "KRIHS_PUBLICATION_RESULT_ENDPOINT_RECOVERY_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_KRIHS_PUBLICATION_RESULT_STRUCTURE_WITHOUT_LEGAL_INFERENCE"
    elif successful_direct_probes > 0:
        classification = "KRIHS_PUBLICATION_DETAIL_ENDPOINT_RECOVERED_AND_HTTP_VERIFIED"
        next_action = "REVIEW_VERIFIED_KRIHS_PUBLICATION_DOCUMENT_IDENTITIES_AS_NON_DISPOSITIVE_DISCOVERY_LEADS"
    elif total_candidates > 0:
        classification = "KRIHS_PUBLICATION_ENDPOINT_CANDIDATES_RECOVERED_NOT_DIRECTLY_VERIFIED"
        next_action = "RESOLVE_JAVASCRIPT_FUNCTION_OR_PARAMETER_CONTRACT_FOR_PUBLICATION_DETAIL_ACCESS"
    else:
        classification = "KRIHS_PUBLICATION_ENDPOINT_NOT_RECOVERED_FROM_CAPTURED_RESULT_CONTEXT"
        next_action = "INSPECT_PUBLICATION_RESULT_TEMPLATE_OR_CLIENT_SIDE_EVENT_BINDING_WITHOUT_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP 17-KRIHS-PUBLICATION-RESULT-ENDPOINT-RECOVERY",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "contract_qualified": contract_qualified,
        "entry_http": entry_http,
        "entry_csrf_found": bool(csrf),
        "entry_error": entry_error,
        "runs": runs,
        "technical_unknown_count": technical_unknown_count,
        "total_endpoint_candidate_count": total_candidates,
        "successful_direct_probe_count": successful_direct_probes,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "publication_endpoint_equals_designation": False,
            "publication_endpoint_equals_current_validity": False,
            "publication_endpoint_equals_site_inclusion": False,
            "no_endpoint_equals_legal_absence": False,
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
    print("ENDPOINT RECOVERY RESULT")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry_http}")
    print(f"ENTRY CSRF FOUND: {bool(csrf)}")
    for row in runs:
        print(
            f'{row["query_class"]}: term={row["term"]!r} http={row["http"]} '
            f'contexts={row["context_count"]} candidates={row["endpoint_candidate_count"]} '
            f'direct_probes={len(row["direct_candidate_probes"])} technical_unknown={row["technical_unknown"]}'
        )
        for idx, candidate in enumerate(row["endpoint_candidates"][:12], 1):
            print(
                f'  [{idx}] score={candidate["publication_score"]} type={candidate["candidate_type"]} '
                f'title={candidate["title"]!r}'
            )
            if candidate.get("absolute_url"):
                print(f'      url={candidate["absolute_url"]}')
            if candidate.get("function_name"):
                print(f'      function={candidate["function_name"]} args={candidate["function_args"]}')
            if candidate.get("onclick"):
                print(f'      onclick={candidate["onclick"][:500]}')
        for idx, probe in enumerate(row["direct_candidate_probes"][:10], 1):
            print(
                f'      PROBE[{idx}] http={probe["http"]} final={probe["final_url"]} '
                f'title={probe["title_signal"]!r} technical_unknown={probe["technical_unknown"]}'
            )

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Publication endpoint == designation: False")
    print("Publication endpoint == current validity: False")
    print("Publication endpoint == site inclusion: False")
    print("No publication endpoint == legal absence: False")
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
        "publication endpoint not designation": out["summary"]["publication_endpoint_equals_designation"] is False,
        "publication endpoint not validity": out["summary"]["publication_endpoint_equals_current_validity"] is False,
        "publication endpoint not site inclusion": out["summary"]["publication_endpoint_equals_site_inclusion"] is False,
        "no endpoint not legal absence": out["summary"]["no_endpoint_equals_legal_absence"] is False,
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
        raise AssertionError("KRIHS publication result endpoint recovery validation failed")


if __name__ == "__main__":
    main()
