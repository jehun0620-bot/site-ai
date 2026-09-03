# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_eminwon_terminal_reconciliation.json"

INPUTS = {
    "s147_detail": OUT_DIR / "development_density_management_area_seongnam_eminwon_notice_detail_contract_qualification.json",
    "s151_search": OUT_DIR / "development_density_management_area_seongnam_eminwon_notice_search_wire_replay_positive_control.json",
    "s153_year": OUT_DIR / "development_density_management_area_seongnam_eminwon_historical_coverage_boundary_probe.json",
    "s154_2003_2012": OUT_DIR / "development_density_management_area_seongnam_eminwon_uqq700_year_scoped_candidate_search.json",
    "s155_2013_2022": OUT_DIR / "development_density_management_area_seongnam_eminwon_uqq700_year_scoped_candidate_search_2013_2022.json",
    "s156_2023_2026": OUT_DIR / "development_density_management_area_seongnam_eminwon_uqq700_year_scoped_candidate_search_2023_2026.json",
}

EXPECTED_YEARS = [str(y) for y in range(2003, 2027)]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def summary(obj: dict) -> dict:
    s = obj.get("summary")
    if not isinstance(s, dict):
        raise AssertionError("summary missing or invalid")
    return s


def main() -> None:
    print("=" * 60)
    print("SEONGNAM EMINWON HISTORICAL NOTICE TERMINAL RECONCILIATION - S157")
    print("=" * 60)
    print("Network: DISABLED")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    docs = {name: load_json(path) for name, path in INPUTS.items()}

    s147 = summary(docs["s147_detail"])
    s151 = summary(docs["s151_search"])
    s153 = summary(docs["s153_year"])
    s154 = summary(docs["s154_2003_2012"])
    s155 = summary(docs["s155_2013_2022"])
    s156 = summary(docs["s156_2023_2026"])

    tranche_docs = [docs["s154_2003_2012"], docs["s155_2013_2022"], docs["s156_2023_2026"]]
    tranche_summaries = [s154, s155, s156]

    years = []
    request_count = 0
    candidate_count = 0
    direct_count = 0
    related_count = 0
    generic_count = 0
    technical_count = 0

    for obj, s in zip(tranche_docs, tranche_summaries):
        years.extend(str(y) for y in obj.get("years", []))
        request_count += int(s.get("request_count", 0))
        candidate_count += int(s.get("candidate_count", 0))
        direct_count += int(s.get("direct_candidate_count", 0))
        related_count += int(s.get("related_candidate_count", 0))
        generic_count += int(s.get("generic_search_result_candidate_count", 0))
        technical_count += int(s.get("technical_unknown_count", 0))

    unique_years = sorted(set(years), key=int)

    checks = {
        "S147 detail contract qualified": s147.get("semantic_state") == "SEONGNAM_EMINWON_NOTICE_DETAIL_CONTRACT_QUALIFIED",
        "S151 search wire contract qualified": s151.get("semantic_state") == "SEONGNAM_EMINWON_NOTICE_SEARCH_WIRE_CONTRACT_QUALIFIED",
        "S153 explicit year filter qualified": s153.get("semantic_state") == "SEONGNAM_EMINWON_EXPLICIT_YEAR_FILTER_QUALIFIED",
        "historical year coverage exact 2003-2026": unique_years == EXPECTED_YEARS,
        "candidate count zero": candidate_count == 0,
        "direct candidate count zero": direct_count == 0,
        "related candidate count zero": related_count == 0,
        "generic candidate count zero": generic_count == 0,
        "technical unknown zero": technical_count == 0,
        "all tranche negative evidence disabled": all(not bool(s.get("negative_evidence_allowed", True)) for s in tranche_summaries),
        "all tranche legal absence inference disabled": all(not bool(s.get("legal_absence_inference_allowed", True)) for s in tranche_summaries),
        "all tranche final resolution unknown": all(s.get("uqq700_final_resolution") == "UNKNOWN" for s in tranche_summaries),
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-53-S157",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "network_enabled": False,
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "reconciliation": {
            "detail_contract_qualified": checks["S147 detail contract qualified"],
            "search_wire_contract_qualified": checks["S151 search wire contract qualified"],
            "explicit_year_filter_qualified": checks["S153 explicit year filter qualified"],
            "covered_years": unique_years,
            "covered_year_start": unique_years[0] if unique_years else None,
            "covered_year_end": unique_years[-1] if unique_years else None,
            "total_search_request_count": request_count,
            "candidate_count": candidate_count,
            "direct_candidate_count": direct_count,
            "related_candidate_count": related_count,
            "generic_search_result_candidate_count": generic_count,
            "technical_unknown_count": technical_count,
        },
        "summary": {
            "semantic_state": "SEONGNAM_EMINWON_HISTORICAL_NOTICE_SEARCH_SURFACE_TERMINALLY_RECONCILED_NO_CANDIDATE",
            "source_family_operational_state": "CLOSED_FOR_THIS_QUALIFIED_SEARCH_SURFACE",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
            "next_source_family": "OTHER_HISTORICAL_OFFICIAL_SOURCE_FAMILY_OR_NOTICE_NUMBER_REVERSE_LOOKUP",
        },
        "validation": checks,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nRECONCILIATION")
    for k, v in out["reconciliation"].items():
        print(f"{k}: {v}")

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    final_checks = dict(checks)
    final_checks.update({
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "unsafe promotion leakage zero": not any(out["summary"][k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"]),
        "final resolution unknown": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    })

    print("\nVALIDATION")
    for k, v in final_checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(final_checks.values()))
    if not all(final_checks.values()):
        raise AssertionError("S157 eminwon terminal reconciliation failed")


if __name__ == "__main__":
    main()
