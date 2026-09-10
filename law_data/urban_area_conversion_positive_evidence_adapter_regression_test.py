from __future__ import annotations

from law_data.urban_area_conversion_positive_evidence_adapter import (
    adapt_urban_area_conversion_positive_evidence,
)


def _verification(payload: dict) -> dict:
    return adapt_urban_area_conversion_positive_evidence(payload)[
        "positive_verification"
    ]


def main() -> None:
    empty = adapt_urban_area_conversion_positive_evidence({})

    diagnostic_rich = adapt_urban_area_conversion_positive_evidence(
        {
            "checks": {
                "combined_candidate_count": 8,
                "combined_target_candidate_count": 3,
                "direct_notice_hit_count": 2,
                "direct_target_event_count": 1,
                "historic_daechi_notice_chain_confirmed": True,
                "notice_123_identified": True,
                "notice_534_found": True,
                "current_urban_area_confirmed": True,
                "current_greenbelt_absent": True,
                "national_archive_candidate_count": 10,
                "national_archive_candidates_confirmed": True,
            }
        }
    )

    nested_summary = adapt_urban_area_conversion_positive_evidence(
        {
            "summary": {
                "checks": {
                    "notice_123_identified": True,
                    "current_urban_area_confirmed": True,
                    "national_archive_candidate_count": 1,
                }
            }
        }
    )

    empty_verified = empty["positive_verification"]
    rich_verified = diagnostic_rich["positive_verification"]
    nested_verified = nested_summary["positive_verification"]

    checks = {
        "empty payload leaves all positive gates false": (
            empty_verified["positive_gate_count"] == 0
            and empty_verified["verified_qualifying_event_present"] is False
        ),
        "candidate-rich payload cannot verify event identity": (
            rich_verified["positive_evidence"]["verified_event_identity"] is False
        ),
        "current geometry cannot verify historical SITE applicability": (
            rich_verified["positive_evidence"]["historical_site_applicability"]
            is False
        ),
        "document and chain signals cannot verify temporal relation": (
            rich_verified["positive_evidence"]["temporal_relation_verified"]
            is False
        ),
        "all diagnostic signals still fail closed": (
            rich_verified["positive_gate_count"] == 0
            and rich_verified["verified_qualifying_event_present"] is False
        ),
        "candidate evidence remains visible diagnostically": (
            rich_verified["diagnostics"]["candidate_hit"] is True
            and rich_verified["diagnostics"]["dispositive"] is False
        ),
        "notice and chain evidence remains diagnostic only": (
            rich_verified["diagnostics"]["title_match"] is True
            and diagnostic_rich["promotion_guards"][
                "notice_identity_promoted_to_verified_event_identity"
            ]
            is False
            and diagnostic_rich["promotion_guards"][
                "historical_chain_promoted_to_verified_event_identity"
            ]
            is False
        ),
        "current state remains diagnostic only": (
            rich_verified["diagnostics"]["current_geometry_match"] is True
            and diagnostic_rich["promotion_guards"][
                "current_geometry_promoted_to_historical_site_applicability"
            ]
            is False
        ),
        "archive candidate remains diagnostic only": (
            rich_verified["diagnostics"]["official_archive_candidate_present"]
            is True
            and diagnostic_rich["promotion_guards"][
                "archive_candidate_promoted_to_verified_event_identity"
            ]
            is False
        ),
        "nested summary checks are supported without promotion": (
            nested_verified["diagnostics"]["candidate_hit"] is True
            and nested_verified["positive_gate_count"] == 0
            and nested_verified["verified_qualifying_event_present"] is False
        ),
        "adapter remains read-only and production-unwired": (
            empty["output_written"] is False
            and empty["production_wiring_applied"] is False
            and empty["overlay_mutated"] is False
            and empty["runtime_registry_mutated"] is False
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("URBAN AREA CONVERSION POSITIVE EVIDENCE ADAPTER")
    print("=" * 72)
    for label, passed in checks.items():
        print(f"{label}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_POSITIVE_EVIDENCE_ADAPTER_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_POSITIVE_EVIDENCE_ADAPTER_FAIL"
        )
    )

    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
