# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_krihs_search_contract_access_qualification.json"
OUT = OUT_DIR / "development_density_management_area_krihs_search_contract_semantic_dedup_hardening.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
EXPECTED_ACTION = "https://www.krihs.re.kr/aivorySearch.es?mid=a11800000000"
EXPECTED_METHOD = "POST"
EXPECTED_FIELD = "allKeyWord"
GENERIC_TERMS = ["국토연구원", "도시계획"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def contract_key(row: dict):
    return (
        str(row.get("method") or "").upper(),
        str(row.get("action") or ""),
        str(row.get("field") or ""),
    )


def canonicalize(rows):
    groups = {}
    for row in rows:
        key = contract_key(row)
        groups.setdefault(key, []).append(row)
    out = []
    for key, members in groups.items():
        run_sets = []
        all_runs_credible = True
        for member in members:
            runs = member.get("runs") or []
            run_sets.append(runs)
            by_term = {r.get("term"): r for r in runs}
            for term in GENERIC_TERMS:
                r = by_term.get(term)
                if not r or r.get("http") != 200 or r.get("changed") is not True or r.get("technical_unknown") is not False:
                    all_runs_credible = False
        first_runs = members[0].get("runs") or []
        run_consistent = all((m.get("runs") or []) == first_runs for m in members)
        out.append({
            "method": key[0],
            "action": key[1],
            "field": key[2],
            "duplicate_count": len(members),
            "all_runs_credible": all_runs_credible,
            "run_consistent": run_consistent,
            "runs": first_runs,
        })
    return sorted(out, key=lambda x: (x["method"], x["action"], x["field"]))


def main():
    print("=" * 78)
    print("KRIHS SEARCH CONTRACT SEMANTIC DEDUP HARDENING")
    print("=" * 78)
    print("Purpose: collapse duplicate semantic contracts without new HTTP requests")
    print("UQQ700 target search: DISABLED")
    print("Search hit/no-hit != legal fact")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    assert prev.get("uqq700_target_search_executed") is False

    raw = prev.get("qualified_contracts") or []
    canonical = canonicalize(raw)
    semantic_unique_count = len(canonical)

    semantic_contract_qualified = (
        semantic_unique_count == 1
        and canonical[0]["method"] == EXPECTED_METHOD
        and canonical[0]["action"] == EXPECTED_ACTION
        and canonical[0]["field"] == EXPECTED_FIELD
        and canonical[0]["all_runs_credible"] is True
        and canonical[0]["run_consistent"] is True
    )

    if semantic_contract_qualified:
        classification = "KRIHS_SEARCH_CONTRACT_ACCESS_SEMANTICALLY_DEDUPED_QUALIFIED"
        semantic = "DUPLICATE_FORM_CANDIDATES_COLLAPSED_TO_ONE_POST_AIVORYSEARCH_ALLKEYWORD_CONTRACT_WITH_CONSISTENT_GENERIC_FILTERING_EVIDENCE"
        next_action = "RUN_BOUNDED_UQQ700_EXACT_VARIANT_WEAK_SEARCH_ONLY_THROUGH_THE_SEMANTICALLY_DEDUPED_KRIHS_CONTRACT"
    else:
        classification = "KRIHS_SEARCH_CONTRACT_SEMANTIC_DEDUP_TECHNICAL_UNKNOWN"
        semantic = "DUPLICATE_CANDIDATES_DID_NOT_COLLAPSE_TO_ONE_STABLE_SEMANTIC_SEARCH_CONTRACT_WITH_CONSISTENT_GENERIC_EVIDENCE"
        next_action = "HARDEN_ONLY_THE_REMAINING_KRIHS_CONTRACT_IDENTITY_OR_GENERIC_FILTERING_INCONSISTENCY_WITHOUT_UQQ700_QUERY"

    out = {
        "step": "STEP 17-KRIHS-CONTRACT-DEDUP",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "previous_qualification_loaded": True,
        "no_new_http_search": True,
        "uqq700_target_search_executed": False,
        "raw_qualified_contract_count": len(raw),
        "semantic_unique_contract_count": semantic_unique_count,
        "canonical_contracts": canonical,
        "contract_qualified": semantic_contract_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
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
    print("DEDUP RESULT")
    print("=" * 78)
    print(f"RAW QUALIFIED CONTRACT COUNT: {len(raw)}")
    print(f"SEMANTIC UNIQUE CONTRACT COUNT: {semantic_unique_count}")
    print(f"CONTRACT QUALIFIED: {semantic_contract_qualified}")
    for c in canonical:
        print("CANONICAL_CONTRACT:", json.dumps(c, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("UQQ700 target search executed: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "previous qualification loaded": out["previous_qualification_loaded"] is True,
        "no new HTTP search": out["no_new_http_search"] is True,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "raw duplicates present": len(raw) >= 2,
        "semantic dedup bounded": semantic_unique_count <= len(raw),
        "expected method/action/field": (not semantic_contract_qualified) or (
            canonical[0]["method"] == EXPECTED_METHOD and canonical[0]["action"] == EXPECTED_ACTION and canonical[0]["field"] == EXPECTED_FIELD
        ),
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
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("KRIHS semantic dedup hardening validation failed")


if __name__ == "__main__":
    main()
