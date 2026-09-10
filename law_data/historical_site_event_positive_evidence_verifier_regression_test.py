from __future__ import annotations

from law_data.historical_site_event_positive_evidence_verifier import (
    HistoricalSiteEventPositiveEvidence,
    verify_historical_site_event_positive_evidence,
)


def _verify(
    identity: bool,
    applicability: bool,
    temporal: bool,
    *,
    diagnostics: bool = False,
) -> dict:
    return verify_historical_site_event_positive_evidence(
        HistoricalSiteEventPositiveEvidence(
            verified_event_identity=identity,
            historical_site_applicability=applicability,
            temporal_relation_verified=temporal,
        ),
        candidate_hit=True if diagnostics else None,
        title_match=True if diagnostics else None,
        http_200=True if diagnostics else None,
        current_geometry_match=True if diagnostics else None,
        official_archive_candidate_present=True if diagnostics else None,
        diagnostic_evidence={"candidate_count": 10} if diagnostics else None,
    )


def main() -> None:
    all_three = _verify(True, True, True)
    missing_identity = _verify(False, True, True)
    missing_applicability = _verify(True, False, True)
    missing_temporal = _verify(True, True, False)
    diagnostics_only = _verify(False, False, False, diagnostics=True)

    checks = {
        "all three positive gates verify qualifying event": (
            all_three["verified_qualifying_event_present"] is True
            and all_three["positive_gate_count"] == 3
        ),
        "missing event identity fails closed": (
            missing_identity["verified_qualifying_event_present"] is False
            and missing_identity["positive_gate_count"] == 2
        ),
        "missing historical SITE applicability fails closed": (
            missing_applicability["verified_qualifying_event_present"] is False
            and missing_applicability["positive_gate_count"] == 2
        ),
        "missing temporal relation fails closed": (
            missing_temporal["verified_qualifying_event_present"] is False
            and missing_temporal["positive_gate_count"] == 2
        ),
        "diagnostic signals cannot manufacture qualifying event": (
            diagnostics_only["verified_qualifying_event_present"] is False
            and diagnostics_only["positive_gate_count"] == 0
        ),
        "candidate discovery remains non-promoting": (
            diagnostics_only[
                "candidate_discovery_promoted_to_verified_event"
            ]
            is False
        ),
        "title match remains non-promoting": (
            diagnostics_only["title_match_promoted_to_verified_event"] is False
        ),
        "HTTP 200 remains non-promoting": (
            diagnostics_only["http_200_promoted_to_verified_event"] is False
        ),
        "current geometry cannot prove historical applicability": (
            diagnostics_only[
                "current_geometry_promoted_to_historical_site_applicability"
            ]
            is False
        ),
        "archive candidate remains non-promoting": (
            diagnostics_only["archive_candidate_promoted_to_verified_event"]
            is False
        ),
        "diagnostics are explicitly non-dispositive": (
            diagnostics_only["diagnostics"]["dispositive"] is False
        ),
        "verifier remains production-unwired": (
            all_three["production_wiring_applied"] is False
            and all_three["runtime_registry_mutated"] is False
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("HISTORICAL SITE EVENT POSITIVE EVIDENCE VERIFIER")
    print("=" * 72)
    for label, passed in checks.items():
        print(f"{label}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "HISTORICAL_SITE_EVENT_POSITIVE_EVIDENCE_VERIFIER_PASS"
            if all_pass
            else "HISTORICAL_SITE_EVENT_POSITIVE_EVIDENCE_VERIFIER_FAIL"
        )
    )

    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
