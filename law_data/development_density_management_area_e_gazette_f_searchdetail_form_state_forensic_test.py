# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
S220A = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_js_submit_contract_forensic.json"
S221A = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_exact_js_payload_contract_forensic.json"
S221B = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_narrowed_positive_control_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_f_searchdetail_form_state_forensic.json"

TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"

FOCUS_TERMS = (
    "f_searchDetail",
    "searchKeyword.do",
    "searchDetail.do",
    "#searchForm",
    "searchForm",
    "searchKeyword",
    "pKeyword",
    "query",
    "pQuery_tmp",
    "old_query",
    "searchGubun",
    "selectSearchCondition",
    "pageNo",
    "sort",
    "category_num",
    "organ_code",
    "organ_name",
    "serialize",
    ".submit",
    "submit(",
    "action",
    "method",
)

ASSIGNMENT_PATTERNS = (
    re.compile(r"(?P<lhs>\$\(\s*['\"]#[^'\"]+['\"]\s*\)\.val)\s*\(\s*(?P<rhs>[^;\n]{0,400})\s*\)", re.I),
    re.compile(r"(?P<lhs>document\.getElementById\(\s*['\"][^'\"]+['\"]\s*\)\.value)\s*=\s*(?P<rhs>[^;\n]{0,400})", re.I),
    re.compile(r"(?P<lhs>[A-Za-z_$][A-Za-z0-9_$]*\.(?:action|method))\s*=\s*(?P<rhs>[^;\n]{0,400})", re.I),
    re.compile(r"(?P<lhs>[A-Za-z_$][A-Za-z0-9_$]*\s*\[\s*['\"][^'\"]+['\"]\s*\])\s*=\s*(?P<rhs>[^;\n]{0,400})", re.I),
)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def extract_assignments(text: str):
    rows = []
    for rx in ASSIGNMENT_PATTERNS:
        for m in rx.finditer(text or ""):
            item = {"lhs": norm(m.group("lhs")), "rhs": norm(m.group("rhs"))}
            if item not in rows:
                rows.append(item)
    return rows[:300]


def extract_ajax_blocks(text: str):
    blocks = []
    for m in re.finditer(r"\$\.ajax\s*\(\s*\{(?P<body>.{0,5000}?)\}\s*\)", text or "", re.I | re.S):
        body = norm(m.group("body"))
        if body not in blocks:
            blocks.append(body)
    return blocks[:50]


def extract_submit_sequences(text: str):
    sequences = []
    lines = [norm(x) for x in re.split(r"[\r\n]+", text or "") if norm(x)]
    for i, line in enumerate(lines):
        low = line.lower()
        if ".submit" in low or "submit(" in low or "searchkeyword.do" in low or "searchdetail.do" in low:
            start = max(0, i - 4)
            end = min(len(lines), i + 5)
            seq = lines[start:end]
            if seq not in sequences:
                sequences.append(seq)
    return sequences[:100]


def score_context(text: str) -> tuple[int, list[str]]:
    low = (text or "").lower()
    hits = []
    score = 0
    weights = {
        "f_searchdetail": 20,
        "searchkeyword.do": 12,
        "searchdetail.do": 10,
        "#searchform": 8,
        "searchform": 5,
        "pkeyword": 5,
        "searchkeyword": 5,
        "pquery_tmp": 5,
        "query": 3,
        "searchgubun": 3,
        "pageno": 2,
        "serialize": 5,
        ".submit": 5,
        "submit(": 5,
        "action": 3,
        "method": 2,
    }
    for term, weight in weights.items():
        if term in low:
            score += weight
            hits.append(term)
    return score, hits


def collect_focus_contexts(s220a: dict):
    agg = s220a.get("aggregated_contract") or {}
    rows = []
    for i, fn in enumerate(agg.get("functions") or []):
        name = str(fn.get("name") or f"anonymous_{i+1:03d}")
        body = str(fn.get("body") or "")
        score, hits = score_context(name + "\n" + body)
        if score:
            rows.append({
                "kind": "function",
                "source": name,
                "score": score,
                "hits": hits,
                "text": body[:50000],
                "assignments": extract_assignments(body),
                "ajax_blocks": extract_ajax_blocks(body),
                "submit_sequences": extract_submit_sequences(body),
            })
    for i, ctx in enumerate(agg.get("submit_contexts") or []):
        text = str(ctx or "")
        score, hits = score_context(text)
        if score:
            rows.append({
                "kind": "submit_context",
                "source": f"submit_context_{i+1:03d}",
                "score": score,
                "hits": hits,
                "text": text[:50000],
                "assignments": extract_assignments(text),
                "ajax_blocks": extract_ajax_blocks(text),
                "submit_sequences": extract_submit_sequences(text),
            })
    rows.sort(key=lambda x: (-x["score"], x["kind"], x["source"]))
    return rows[:120]


def derive_contract(rows):
    f_rows = [x for x in rows if x["kind"] == "function" and x["source"] == "f_searchDetail"]
    if not f_rows:
        f_rows = [x for x in rows if "f_searchdetail" in {h.lower() for h in x["hits"]}]

    combined = "\n".join(x["text"] for x in (f_rows or rows[:20]))
    low = combined.lower()

    endpoint = None
    if "searchkeyword.do" in low:
        endpoint = "searchKeyword.do"
    elif "searchdetail.do" in low:
        endpoint = "searchDetail.do"

    method = None
    if re.search(r"method\s*[:=]\s*['\"]post['\"]", combined, re.I) or re.search(r"\.method\s*=\s*['\"]post['\"]", combined, re.I):
        method = "POST"
    elif re.search(r"method\s*[:=]\s*['\"]get['\"]", combined, re.I) or re.search(r"\.method\s*=\s*['\"]get['\"]", combined, re.I):
        method = "GET"

    assignments = []
    ajax = []
    submit_sequences = []
    for row in (f_rows or rows[:20]):
        for a in row["assignments"]:
            if a not in assignments:
                assignments.append(a)
        for a in row["ajax_blocks"]:
            if a not in ajax:
                ajax.append(a)
        for s in row["submit_sequences"]:
            if s not in submit_sequences:
                submit_sequences.append(s)

    focus_fields = {}
    for field in ("searchKeyword", "pKeyword", "query", "pQuery_tmp", "old_query", "searchGubun", "pageNo", "sort", "category_num", "organ_code", "organ_name"):
        focus_fields[field] = len(re.findall(re.escape(field), combined, re.I))

    searchkeyword_cleared = bool(re.search(r"#searchKeyword['\"]?\s*\)?\.val\s*\(\s*['\"]['\"]\s*\)", combined, re.I))
    pkeyword_assigned = bool(re.search(r"pKeyword", combined, re.I))
    serialize_seen = "serialize" in low
    submit_seen = ".submit" in low or "submit(" in low
    action_seen = "action" in low and endpoint is not None

    exact_function_state_recovered = bool(
        f_rows
        and endpoint is not None
        and submit_seen
        and (serialize_seen or len(assignments) > 0)
        and (focus_fields.get("pKeyword", 0) > 0 or focus_fields.get("searchKeyword", 0) > 0)
    )

    return {
        "f_searchdetail_context_count": len(f_rows),
        "best_endpoint": endpoint,
        "best_method": method,
        "focus_field_mentions": focus_fields,
        "assignments": assignments[:200],
        "ajax_blocks": ajax[:30],
        "submit_sequences": submit_sequences[:50],
        "searchkeyword_cleared": searchkeyword_cleared,
        "pkeyword_signal_seen": pkeyword_assigned,
        "serialize_seen": serialize_seen,
        "submit_seen": submit_seen,
        "action_seen": action_seen,
        "exact_function_state_recovered": exact_function_state_recovered,
    }


def main():
    print("=" * 78)
    print("E-GAZETTE f_searchDetail FORM STATE FORENSIC - S221C")
    print("=" * 78)
    print("Positive control:", POSITIVE_CONTROL)
    print("Target UQQ700 query is NOT replayed in this stage")
    print("Purpose: recover exact f_searchDetail/form-state transition before replay")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s220a = json.loads(S220A.read_text(encoding="utf-8"))
    s221a = json.loads(S221A.read_text(encoding="utf-8"))
    s221b = json.loads(S221B.read_text(encoding="utf-8"))

    gate220a = bool((s220a.get("aggregated_contract") or {}).get("contract_recovered_for_positive_control_replay"))
    gate221a = bool((s221a.get("inferred_contract") or {}).get("exact_payload_signal_recovered"))
    gate221b = (s221b.get("summary") or {}).get("semantic_state") == "E_GAZETTE_NARROWED_POSITIVE_CONTROL_REPLAY_UNRESOLVED"
    gate_safe = (s221b.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    if not (gate220a and gate221a and gate221b and gate_safe):
        raise AssertionError("S221C prerequisite gate not satisfied")

    rows = collect_focus_contexts(s220a)
    contract = derive_contract(rows)
    technical_unknown_count = 0

    recovered = bool(contract["exact_function_state_recovered"])
    semantic = "E_GAZETTE_F_SEARCHDETAIL_FORM_STATE_RECOVERED" if recovered else "E_GAZETTE_F_SEARCHDETAIL_FORM_STATE_STILL_UNRESOLVED"
    next_action = "BUILD_S221D_EXACT_POSITIVE_CONTROL_REPLAY_FROM_RECOVERED_FORM_STATE" if recovered else "MANUALLY_INSPECT_TOP_F_SEARCHDETAIL_CONTEXTS_BEFORE_ANY_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-119-S221C",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "positive_control": POSITIVE_CONTROL,
        "input_s220a": str(S220A),
        "input_s221a": str(S221A),
        "input_s221b": str(S221B),
        "focus_contexts": rows,
        "recovered_form_state": contract,
        "summary": {
            "technical_unknown_count": technical_unknown_count,
            "exact_form_state_recovered": recovered,
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

    print("FOCUS CONTEXT COUNT:", len(rows))
    print("f_searchDetail context count:", contract["f_searchdetail_context_count"])
    print("Best endpoint:", contract["best_endpoint"])
    print("Best method:", contract["best_method"])
    print("SearchKeyword cleared before submit:", contract["searchkeyword_cleared"])
    print("pKeyword signal seen:", contract["pkeyword_signal_seen"])
    print("Serialize seen:", contract["serialize_seen"])
    print("Submit seen:", contract["submit_seen"])
    print("Action seen:", contract["action_seen"])
    print("Exact function/form state recovered:", contract["exact_function_state_recovered"])

    print("\nFOCUS FIELD MENTIONS")
    for k, v in contract["focus_field_mentions"].items():
        print(f"{k}: {v}")

    print("\nASSIGNMENTS")
    for i, a in enumerate(contract["assignments"][:30], 1):
        print(f"[{i:02d}] {a['lhs']} <- {a['rhs']}")

    print("\nSUBMIT SEQUENCES")
    for i, seq in enumerate(contract["submit_sequences"][:12], 1):
        print(f"--- sequence {i:02d} ---")
        for line in seq:
            print(line)

    print("\nSUMMARY")
    print("Exact form state recovered:", recovered)
    print("Technical unknown count:", technical_unknown_count)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S220A contract gate": gate220a,
        "S221A exact payload gate": gate221a,
        "S221B unresolved replay gate": gate221b,
        "focus contexts emitted": len(rows) > 0,
        "f_searchDetail context observed": contract["f_searchdetail_context_count"] > 0,
        "endpoint recovered": contract["best_endpoint"] is not None,
        "form state recovered": recovered,
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
        raise AssertionError("S221C e-gazette f_searchDetail form state forensic failed")


if __name__ == "__main__":
    main()
