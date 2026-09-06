# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
S220A = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_js_submit_contract_forensic.json"
S221 = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_positive_control_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_exact_js_payload_contract_forensic.json"

TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"

CORE_FIELDS = (
    "query", "keyword", "searchKeyword", "pKeyword", "pQuery_tmp", "old_query",
    "searchGubun", "selectSearchCondition", "pageNo", "sort", "menuControl",
    "researchChk", "resultSearchChk", "editGubun", "organ_code", "organ_name",
    "datepicker_startdate", "datepicker_enddate", "category_num", "category_value",
)

CORE_SELECTORS = tuple(f"#{x}" for x in CORE_FIELDS) + ("#searchForm", "#detail_query", "#txSimpleSearch")
ENDPOINT_MARKERS = ("searchKeyword.do", "searchDetail.do")
SUBMIT_MARKERS = ("submit(", ".submit", "serialize", "action", "location.href", "location.replace", "$.ajax", "$.post", "$.get")

# Keep these deliberately simple and compile them once at import time.  S221A is a
# forensic parser: a malformed regex must fail with its own name before any source
# interpretation is attempted.
_ASSIGNMENT_PATTERN_SPECS = (
    (
        "jquery_val",
        r"(?P<lhs>\$\(\s*['\"]#[^'\"]+['\"]\s*\)\.val)\s*\(\s*(?P<rhs>[^;\n]{0,250})\s*\)",
    ),
    (
        "dom_value",
        r"(?P<lhs>document\.getElementById\(\s*['\"][^'\"]+['\"]\s*\)\.value)\s*=\s*(?P<rhs>[^;\n]{0,250})",
    ),
    (
        "object_action_method",
        r"(?P<lhs>[A-Za-z_$][A-Za-z0-9_$]*\.(?:action|method))\s*=\s*(?P<rhs>[^;\n]{0,250})",
    ),
    (
        "object_key",
        r"(?P<lhs>[A-Za-z_$][A-Za-z0-9_$]*\s*\[\s*['\"][^'\"]+['\"]\s*\])\s*=\s*(?P<rhs>[^;\n]{0,250})",
    ),
)


def _compile_assignment_patterns():
    compiled = []
    for name, pattern in _ASSIGNMENT_PATTERN_SPECS:
        try:
            compiled.append((name, re.compile(pattern, re.I)))
        except re.error as ex:
            raise RuntimeError(f"invalid S221A assignment regex {name}: {ex}") from ex
    return tuple(compiled)


ASSIGNMENT_PATTERNS = _compile_assignment_patterns()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def score_text(text: str) -> tuple[int, list[str]]:
    low = text.lower()
    hits = []
    score = 0
    for ep in ENDPOINT_MARKERS:
        if ep.lower() in low:
            score += 8
            hits.append(ep)
    for sel in CORE_SELECTORS:
        if sel.lower() in low:
            score += 4
            hits.append(sel)
    for field in CORE_FIELDS:
        if re.search(rf"\b{re.escape(field.lower())}\b", low):
            score += 2
            hits.append(field)
    for marker in SUBMIT_MARKERS:
        if marker.lower() in low:
            score += 3
            hits.append(marker)
    return score, sorted(set(hits))


def extract_assignments(text: str):
    out = []
    source = text or ""
    for pattern_name, regex in ASSIGNMENT_PATTERNS:
        for m in regex.finditer(source):
            lhs = norm(m.group("lhs"))
            rhs = norm(m.group("rhs"))
            # A forensic signal is useful only when both sides contain content.
            if not lhs or not rhs:
                continue
            item = {"pattern": pattern_name, "lhs": lhs, "rhs": rhs}
            if item not in out:
                out.append(item)
            if len(out) >= 200:
                return out
    return out


def extract_actions(text: str):
    vals = []
    for m in re.finditer(r"(?:action\s*=|\.attr\s*\(\s*['\"]action['\"]\s*,)\s*['\"]([^'\"]+\.do(?:\?[^'\"]*)?)['\"]", text or "", re.I):
        v = m.group(1)
        if v not in vals:
            vals.append(v)
    return vals[:100]


def extract_methods(text: str):
    vals = []
    for m in re.finditer(r"(?:method\s*=|\.attr\s*\(\s*['\"]method['\"]\s*,)\s*['\"](GET|POST)['\"]", text or "", re.I):
        v = m.group(1).upper()
        if v not in vals:
            vals.append(v)
    return vals


def collect_candidates(s220a: dict):
    raw = []
    agg = s220a.get("aggregated_contract") or {}
    for i, ctx in enumerate(agg.get("submit_contexts") or []):
        raw.append((f"submit_context_{i+1:03d}", ctx))
    for i, fn in enumerate(agg.get("functions") or []):
        name = fn.get("name") or f"anonymous_{i+1:03d}"
        raw.append((f"function:{name}", fn.get("body") or ""))

    ranked = []
    for source, text in raw:
        score, hits = score_text(text)
        if score <= 0:
            continue
        ranked.append({
            "source": source,
            "score": score,
            "hits": hits,
            "actions": extract_actions(text),
            "methods": extract_methods(text),
            "assignments": extract_assignments(text),
            "text": norm(text)[:12000],
        })
    ranked.sort(key=lambda x: (-x["score"], x["source"]))
    return ranked[:80]


def infer_contract(cands):
    endpoint_votes = {}
    method_votes = {}
    field_mentions = {k: 0 for k in CORE_FIELDS}
    action_assignment_seen = False
    submit_seen = False
    serialize_seen = False

    for c in cands:
        text = c["text"]
        low = text.lower()
        for ep in ENDPOINT_MARKERS:
            if ep.lower() in low:
                endpoint_votes[ep] = endpoint_votes.get(ep, 0) + 1
        for m in c["methods"]:
            method_votes[m] = method_votes.get(m, 0) + 1
        for field in CORE_FIELDS:
            if re.search(rf"\b{re.escape(field.lower())}\b", low) or f"#{field.lower()}" in low:
                field_mentions[field] += 1
        if "action" in low and any(ep.lower() in low for ep in ENDPOINT_MARKERS):
            action_assignment_seen = True
        if ".submit" in low or "submit(" in low:
            submit_seen = True
        if "serialize" in low:
            serialize_seen = True

    ranked_fields = [
        {"field": k, "mentions": v}
        for k, v in sorted(field_mentions.items(), key=lambda kv: (-kv[1], kv[0]))
        if v > 0
    ]
    best_endpoint = max(endpoint_votes, key=endpoint_votes.get) if endpoint_votes else None
    best_method = max(method_votes, key=method_votes.get) if method_votes else None

    strong_core = {x["field"] for x in ranked_fields if x["mentions"] >= 2}
    exact_payload_signal = (
        best_endpoint is not None
        and (action_assignment_seen or submit_seen)
        and len(strong_core.intersection({"query", "pQuery_tmp", "searchGubun", "pageNo", "menuControl", "selectSearchCondition"})) >= 2
    )

    return {
        "endpoint_votes": endpoint_votes,
        "method_votes": method_votes,
        "best_endpoint": best_endpoint,
        "best_method": best_method,
        "ranked_field_mentions": ranked_fields,
        "strong_core_fields": sorted(strong_core),
        "action_assignment_seen": action_assignment_seen,
        "submit_seen": submit_seen,
        "serialize_seen": serialize_seen,
        "exact_payload_signal_recovered": exact_payload_signal,
    }


def main():
    print("=" * 78)
    print("E-GAZETTE SEARCH EXACT JS PAYLOAD CONTRACT FORENSIC - S221A")
    print("=" * 78)
    print("Positive control:", POSITIVE_CONTROL)
    print("Target UQQ700 query is NOT replayed in this stage")
    print("Purpose: narrow exact browser JS payload assembly contract")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s220a = json.loads(S220A.read_text(encoding="utf-8"))
    s221 = json.loads(S221.read_text(encoding="utf-8"))

    gate220a = bool((s220a.get("aggregated_contract") or {}).get("contract_recovered_for_positive_control_replay"))
    gate221_unresolved = (s221.get("summary") or {}).get("semantic_state") == "E_GAZETTE_POSITIVE_CONTROL_REPLAY_UNRESOLVED"
    gate221_safe = (s221.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    if not gate220a:
        raise AssertionError("S220A contract gate not satisfied")
    if not gate221_unresolved:
        raise AssertionError("S221A applies only after unresolved S221 positive-control replay")
    if not gate221_safe:
        raise AssertionError("S221 safety state invalid")

    cands = collect_candidates(s220a)
    inferred = infer_contract(cands)

    technical_unknown_count = 0
    contract_recovered = bool(inferred["exact_payload_signal_recovered"])
    semantic = (
        "E_GAZETTE_EXACT_JS_PAYLOAD_CONTRACT_NARROWED_FOR_REPLAY"
        if contract_recovered
        else "E_GAZETTE_EXACT_JS_PAYLOAD_CONTRACT_STILL_UNRESOLVED"
    )
    next_action = (
        "BUILD_S221B_POSITIVE_CONTROL_REPLAY_USING_NARROWED_EXACT_PAYLOAD"
        if contract_recovered
        else "INSPECT_TOP_RANKED_JS_CONTEXTS_MANUALLY_BEFORE_ANY_FURTHER_REPLAY"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-117-S221A",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "input_s220a": str(S220A),
        "input_s221": str(S221),
        "ranked_candidates": cands,
        "inferred_contract": inferred,
        "summary": {
            "technical_unknown_count": technical_unknown_count,
            "exact_payload_contract_recovered": contract_recovered,
            "semantic_state": semantic,
            "next_action": next_action,
            "query_replay_performed": False,
            "uqq700_query_replayed": False,
            "search_hit_equals_designation_fact": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("ASSIGNMENT REGEX COUNT:", len(ASSIGNMENT_PATTERNS))
    print("ASSIGNMENT REGEX COMPILE CHECK: True")
    print("RANKED CANDIDATE COUNT:", len(cands))
    for i, c in enumerate(cands[:12], 1):
        print(f"[{i:02d}] score={c['score']} source={c['source']} hits={c['hits'][:12]}")
        if c["actions"]:
            print("     actions:", c["actions"][:5])
        if c["methods"]:
            print("     methods:", c["methods"])
        if c["assignments"]:
            print("     assignments:", c["assignments"][:5])

    print("\nINFERRED CONTRACT")
    print("Best endpoint:", inferred["best_endpoint"])
    print("Best method:", inferred["best_method"])
    print("Endpoint votes:", inferred["endpoint_votes"])
    print("Method votes:", inferred["method_votes"])
    print("Strong core fields:", inferred["strong_core_fields"])
    print("Action assignment seen:", inferred["action_assignment_seen"])
    print("Submit seen:", inferred["submit_seen"])
    print("Serialize seen:", inferred["serialize_seen"])
    print("Exact payload signal recovered:", inferred["exact_payload_signal_recovered"])

    print("\nSUMMARY")
    print("Exact payload contract recovered:", contract_recovered)
    print("Technical unknown count:", technical_unknown_count)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution:", out["summary"]["uqq700_final_resolution"])
    print("Output:", OUT)

    checks = {
        "assignment regex compile check": len(ASSIGNMENT_PATTERNS) == len(_ASSIGNMENT_PATTERN_SPECS),
        "S220A contract gate": gate220a,
        "S221 unresolved replay gate": gate221_unresolved,
        "ranked candidate contexts emitted": len(cands) > 0,
        "best endpoint observed": inferred["best_endpoint"] is not None,
        "exact payload contract recovered": contract_recovered,
        "query replay not performed": out["summary"]["query_replay_performed"] is False,
        "UQQ700 query not replayed": out["summary"]["uqq700_query_replayed"] is False,
        "search hit not designation fact": out["summary"]["search_hit_equals_designation_fact"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S221A exact e-gazette JS payload contract forensic failed")


if __name__ == "__main__":
    main()
