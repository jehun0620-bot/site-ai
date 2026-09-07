# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_historical_discovery_source_family_reranking_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

# S230A is intentionally non-networked.  It reconciles already-established
# source-family terminal states and promotes only concrete technical unknowns
# or genuinely untried high-value source families to the next queue.

CLOSED_FAMILIES = [
    {
        "family": "SEONGNAM_DYNAMIC_HWP_GAZETTE",
        "terminal_stage": "S72",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Municipal dynamic HWP gazette path operationally closed.",
    },
    {
        "family": "SEONGNAM_POST_HWP5_GAZETTE",
        "terminal_stage": "S133",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "POST-HWP5 municipal gazette path operationally closed.",
    },
    {
        "family": "SEONGNAM_PRE_HWP5_GAZETTE",
        "terminal_stage": "S140",
        "state": "CLOSED_WITH_HWP3_TECHNICAL_UNKNOWN_CARRY_FORWARD",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Family closed; legacy HWP3 technical unknowns are carried as technical unknowns only.",
    },
    {
        "family": "SEONGNAM_PM010301_OFFICIAL_NOTICE",
        "terminal_stage": "PRE_S206",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Official notice family previously operationally exhausted.",
    },
    {
        "family": "SEONGNAM_EMINWON",
        "terminal_stage": "S157",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "EMINWON source family operationally closed.",
    },
    {
        "family": "EUM_METADATA_DETAIL_HTML",
        "terminal_stage": "S188",
        "state": "CLOSED_WITH_LIVE_ATTACHMENT_ACCESS_TECHNICAL_UNKNOWN",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Qualified metadata/detail HTML closed; attachment access guard remains technical only.",
    },
    {
        "family": "NATIONAL_ARCHIVES_OF_KOREA",
        "terminal_stage": "S205",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Qualified search/result identity/org-filter positive controls completed.",
    },
    {
        "family": "NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY",
        "terminal_stage": "S219",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "All historical ordinance versions scanned with no term anchor; ordinance no-hit is not legal absence.",
    },
    {
        "family": "E_GAZETTE",
        "terminal_stage": "S221S_S222",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Full-document review and immutable terminal transition completed; observed term was national regulatory policy-list context only.",
    },
    {
        "family": "GYEONGGI_OFFICIAL_RECORD",
        "terminal_stage": "S224C",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Bounded official-record queries completed without promotion to legal absence.",
    },
    {
        "family": "LOCAL_GOSI_OFFICIAL",
        "terminal_stage": "S225D",
        "state": "CLOSED_SOURCE_ROLE_MISMATCH",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Source classified as exam/recruitment service and excluded by role, not by legal absence.",
    },
    {
        "family": "SEONGNAM_URBAN_PLANNING_COMMITTEE",
        "terminal_stage": "S226Q",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Official board search contract qualified; exact target title queries returned no rows. Historical precursor source only.",
    },
    {
        "family": "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD",
        "terminal_stage": "S228E",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Official council entry/contracts/bounded target search terminally reconciled with no target anchor.",
    },
    {
        "family": "NATIONAL_REGIONAL_PLANNING_RESEARCH_DOCUMENT",
        "terminal_stage": "S229E",
        "state": "CLOSED",
        "repeat_search_allowed": False,
        "legal_absence_established": False,
        "note": "Planning/research entry, canonical contracts, bounded target search and echo hardening completed with no verified result anchor.",
    },
]

PARTIAL_TECHNICAL_UNKNOWNS = [
    {
        "family": "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE",
        "terminal_stage": "S227K",
        "state": "PARTIALLY_CLOSED_TECHNICAL_UNKNOWN",
        "priority": 100,
        "reason": "Six specific legacy PDF binaries have verified ASIS metadata identity but public HTTP retrieval returns 404/HTML.",
        "unresolved_kind": "ARCHIVED_BINARY_ACCESS",
        "unresolved_count": 6,
        "repeat_same_probe_allowed": False,
        "recommended_next_probe": "ARCHIVE_BINARY_RECOVERY_BY_ALTERNATE_OFFICIAL_OR_ARCHIVAL_PATH_ONLY",
        "legal_absence_established": False,
        "items": [
            {"file_no": 58460, "stored_name": "20150902175005097.pdf", "original_name": "산성2 지구단위계획지침도 1-1.pdf", "size": 628561},
            {"file_no": 58461, "stored_name": "20150902175005175.pdf", "original_name": "산성2 지구단위계획지침도 1-2.pdf", "size": 792505},
            {"file_no": 58462, "stored_name": "20150902175005269.pdf", "original_name": "산성2 지구단위계획지침도 2-1.pdf", "size": 1017775},
            {"file_no": 58463, "stored_name": "20150902175005378.pdf", "original_name": "산성2 지구단위계획지침도 2-2.pdf", "size": 1053676},
            {"file_no": 58464, "stored_name": "20150902175005487.pdf", "original_name": "산성2 지구단위계획지침도 2-3.pdf", "size": 940118},
            {"file_no": 58465, "stored_name": "20150902175053177.pdf", "original_name": "산성2 시행지침(2009.07.24).pdf", "size": 791263},
        ],
    },
    {
        "family": "KRIHS_SEARCH_CONTRACT_ACCESS",
        "terminal_stage": "S229B",
        "state": "TECHNICAL_UNKNOWN_NOT_TARGET_NO_HIT",
        "priority": 35,
        "reason": "Official KRIHS publication/search forms were identified but POST replay returned 403.",
        "unresolved_kind": "SEARCH_CONTRACT_ACCESS_GUARD",
        "unresolved_count": 1,
        "repeat_same_probe_allowed": False,
        "recommended_next_probe": "ONLY_IF_HIGHER_VALUE_OFFICIAL_NOTICE_PATHS_ARE_EXHAUSTED",
        "legal_absence_established": False,
    },
    {
        "family": "MOLIT_ENTRY_ACCESS",
        "terminal_stage": "S229A",
        "state": "TECHNICAL_UNKNOWN_ENTRY_FETCH",
        "priority": 25,
        "reason": "MOLIT entry returned redirect/body-zero in S229A; this is an access mechanics issue, not source absence.",
        "unresolved_kind": "ENTRY_REDIRECT_ACCESS",
        "unresolved_count": 1,
        "repeat_same_probe_allowed": False,
        "recommended_next_probe": "ONLY_IF_DIRECT_OFFICIAL_NOTICE_IDENTITY_PATHS_REMAIN_UNAVAILABLE",
        "legal_absence_established": False,
    },
]

# These are not declared as discovered facts.  They are candidate source roles
# that may be considered only after concrete unresolved official/archival paths.
UNTRIED_HIGH_VALUE_CANDIDATES = [
    {
        "family": "SEONGNAM_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP",
        "state": "UNTRIED_HIGH_VALUE",
        "priority": 90,
        "reason": "A notice-number/document-identity reverse lookup is closer to the legal designation identity gate than broad keyword search.",
        "allowed_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_ONLY",
    },
    {
        "family": "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_OR_NOTICE_ARCHIVE_ALTERNATE_ENTRY",
        "state": "UNTRIED_HIGH_VALUE",
        "priority": 70,
        "reason": "Alternate official archival entry may expose historical notice identity or inaccessible municipal binaries without repeating closed search contracts.",
        "allowed_role": "OFFICIAL_ARCHIVAL_IDENTITY_OR_BINARY_RECOVERY_ONLY",
    },
]


def scan_local_terminal_outputs() -> list[dict]:
    rows = []
    if not OUT_DIR.exists():
        return rows
    for p in sorted(OUT_DIR.glob("*terminal_reconciliation.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            rows.append({"file": str(p), "loaded": False, "error": f"{type(exc).__name__}: {exc}"})
            continue
        rows.append({
            "file": str(p),
            "loaded": True,
            "classification": data.get("classification"),
            "source_family": data.get("source_family"),
            "uqq700_final_resolution": (data.get("summary") or {}).get("uqq700_final_resolution"),
            "source_family_operationally_closed": data.get("source_family_operationally_closed"),
            "legal_absence_established": data.get("legal_absence_established"),
        })
    return rows


def main() -> None:
    print("=" * 78)
    print("UQQ700 HISTORICAL DISCOVERY SOURCE FAMILY RERANKING / RECONCILIATION - S230A")
    print("=" * 78)
    print("Purpose: rerank closed, partial-technical-unknown, and untried high-value source families")
    print("HTTP/network search: DISABLED")
    print("Closed source families must not be repeated")
    print("Technical unknown != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    local_terminal_outputs = scan_local_terminal_outputs()

    ranked = []
    for row in PARTIAL_TECHNICAL_UNKNOWNS:
        ranked.append({**row, "rank_group": "PARTIALLY_CLOSED_TECHNICAL_UNKNOWN"})
    for row in UNTRIED_HIGH_VALUE_CANDIDATES:
        ranked.append({**row, "rank_group": "UNTRIED_HIGH_VALUE"})
    ranked.sort(key=lambda x: (-int(x.get("priority") or 0), x["family"]))

    next_candidate = ranked[0] if ranked else None
    next_family = next_candidate["family"] if next_candidate else None
    next_action = (
        "RECOVER_ONLY_THE_SIX_VERIFIED_SEONGNAM_ASIS_LEGACY_PDF_BINARIES_VIA_ALTERNATE_OFFICIAL_OR_ARCHIVAL_ACCESS_PATH_WITHOUT_REPEATING_THE_SAME_404_PROBE"
        if next_family == "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
        else "QUALIFY_THE_TOP_RANKED_NON_CLOSED_SOURCE_WITHOUT_NEGATIVE_INFERENCE"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-166-S230A",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "http_search_executed": False,
        "closed_family_count": len(CLOSED_FAMILIES),
        "closed_families": CLOSED_FAMILIES,
        "partial_technical_unknown_count": len(PARTIAL_TECHNICAL_UNKNOWNS),
        "partial_technical_unknowns": PARTIAL_TECHNICAL_UNKNOWNS,
        "untried_high_value_count": len(UNTRIED_HIGH_VALUE_CANDIDATES),
        "untried_high_value_candidates": UNTRIED_HIGH_VALUE_CANDIDATES,
        "ranked_next_candidates": ranked,
        "next_source_family": next_family,
        "local_terminal_output_observations": local_terminal_outputs,
        "classification": "UQQ700_HISTORICAL_DISCOVERY_SOURCE_FAMILY_RERANKED_WITH_CONCRETE_TECHNICAL_UNKNOWN_PRIORITY",
        "summary": {
            "semantic_state": "CLOSED_SOURCE_FAMILIES_ARE_FROZEN_NON_NEGATIVELY_WHILE_CONCRETE_TECHNICAL_UNKNOWNS_AND_UNTRIED_HIGH_VALUE_OFFICIAL_IDENTITY_PATHS_ARE_RERANKED",
            "next_action": next_action,
            "top_priority_reason": next_candidate.get("reason") if next_candidate else None,
            "closed_source_repeat_search_allowed": False,
            "technical_unknown_equals_legal_absence": False,
            "source_no_hit_equals_legal_absence": False,
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
    print("RERANKING")
    print("=" * 78)
    print(f"CLOSED FAMILY COUNT: {len(CLOSED_FAMILIES)}")
    print(f"PARTIAL TECHNICAL UNKNOWN COUNT: {len(PARTIAL_TECHNICAL_UNKNOWNS)}")
    print(f"UNTRIED HIGH VALUE COUNT: {len(UNTRIED_HIGH_VALUE_CANDIDATES)}")
    for i, row in enumerate(ranked, 1):
        print(json.dumps({
            "rank": i,
            "family": row["family"],
            "group": row["rank_group"],
            "priority": row.get("priority"),
            "unresolved_kind": row.get("unresolved_kind"),
            "reason": row.get("reason"),
        }, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"NEXT SOURCE FAMILY: {next_family}")
    print(f"NEXT ACTION: {next_action}")
    print("CLOSED SOURCE REPEAT SEARCH ALLOWED: False")
    print("TECHNICAL UNKNOWN == LEGAL ABSENCE: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "no HTTP search": out["http_search_executed"] is False,
        "closed families frozen": all(x["repeat_search_allowed"] is False for x in CLOSED_FAMILIES),
        "closed families do not establish legal absence": all(x["legal_absence_established"] is False for x in CLOSED_FAMILIES),
        "partial unknowns do not establish legal absence": all(x["legal_absence_established"] is False for x in PARTIAL_TECHNICAL_UNKNOWNS),
        "six legacy PDFs preserved": PARTIAL_TECHNICAL_UNKNOWNS[0]["unresolved_count"] == 6 and len(PARTIAL_TECHNICAL_UNKNOWNS[0]["items"]) == 6,
        "same 404 probe blocked": PARTIAL_TECHNICAL_UNKNOWNS[0]["repeat_same_probe_allowed"] is False,
        "top priority is concrete Seongnam archived binary unknown": next_family == "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE",
        "technical unknown not legal absence": out["summary"]["technical_unknown_equals_legal_absence"] is False,
        "source no-hit not legal absence": out["summary"]["source_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": out["classification"] == "UQQ700_HISTORICAL_DISCOVERY_SOURCE_FAMILY_RERANKED_WITH_CONCRETE_TECHNICAL_UNKNOWN_PRIORITY",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"LOCAL TERMINAL OUTPUT OBSERVATION COUNT: {len(local_terminal_outputs)}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S230A validation failed")


if __name__ == "__main__":
    main()
