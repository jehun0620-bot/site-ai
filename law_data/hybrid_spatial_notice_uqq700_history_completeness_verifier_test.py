from __future__ import annotations

from hybrid_spatial_notice_uqq700_history_completeness_verifier import (
    VERIFIED,
    Uqq700HistoryCompletenessProvenance,
    verify_uqq700_history_completeness,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_HISTORY_COMPLETENESS_VERIFIER_PASS"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_HISTORY_COMPLETENESS_VERIFIER_REGRESSION"
)


def evidence() -> Uqq700HistoryCompletenessProvenance:
    return Uqq700HistoryCompletenessProvenance(
        designation_identity_verified=True,
        issuing_authority="성남시장",
        history_source_id="official-authoritative-history-source-1",
        history_source_official_verified=True,
        history_source_complete_for_authority_verified=True,
        scope_start_date="2000-01-01",
        scope_end_date="2026-09-09",
        authoritative_snapshot_date="2026-09-09",
        downstream_records_exhaustively_enumerated_verified=True,
    )


def main() -> int:
    checks: list[tuple[str, bool]] = []

    complete = verify_uqq700_history_completeness(evidence())
    checks.append(
        (
            "complete positive provenance can verify downstream history completeness",
            complete["status"] == VERIFIED
            and complete["downstream_history_complete"] is True
            and complete["history_completeness_verified"] is True,
        )
    )
    checks.append(
        (
            "verified completeness preserves authority source and scope",
            complete["positive_provenance"]["issuing_authority"] == "성남시장"
            and complete["positive_provenance"]["history_source_id"]
            == "official-authoritative-history-source-1"
            and complete["positive_provenance"]["scope_start_date"] == "2000-01-01"
            and complete["positive_provenance"]["scope_end_date"] == "2026-09-09",
        )
    )
    checks.append(
        (
            "completeness alone does not verify current validity or later gates",
            complete["current_validity_verified"] is False
            and complete["site_spatial_inclusion_verified"] is False
            and complete["minimum_registration_gate_satisfied"] is False
            and complete["runtime_registration_allowed"] is False,
        )
    )
    checks.append(
        (
            "negative and diagnostic evidence remain non-dispositive",
            complete["search_no_hit_dispositive"] is False
            and complete["source_family_exhaustion_dispositive"] is False
            and complete["http_success_dispositive"] is False
            and complete["candidate_count_dispositive"] is False
            and complete["latest_document_dispositive"] is False
            and complete["diagnostics_dispositive"] is False,
        )
    )
    checks.append(
        (
            "safety inference and mutations remain disabled",
            complete["negative_evidence_allowed"] is False
            and complete["legal_absence_inference_allowed"] is False
            and complete["site_false_inference_allowed"] is False
            and complete["site_promotion_allowed"] is False
            and complete["production_wiring_applied"] is False
            and complete["runtime_registry_mutated"] is False
            and complete["site_mutated"] is False,
        )
    )

    missing_source_capability = evidence()
    missing_source_capability = Uqq700HistoryCompletenessProvenance(
        **{
            **missing_source_capability.__dict__,
            "history_source_complete_for_authority_verified": False,
        }
    )
    rejected_source_capability = verify_uqq700_history_completeness(
        missing_source_capability,
        diagnostics={
            "search_no_hit": True,
            "source_family_exhausted": True,
            "http_200": True,
            "candidate_count": 0,
        },
    )
    checks.append(
        (
            "search and source-family exhaustion cannot replace source capability",
            rejected_source_capability["downstream_history_complete"] is False,
        )
    )

    missing_exhaustive_enumeration = evidence()
    missing_exhaustive_enumeration = Uqq700HistoryCompletenessProvenance(
        **{
            **missing_exhaustive_enumeration.__dict__,
            "downstream_records_exhaustively_enumerated_verified": False,
        }
    )
    rejected_enumeration = verify_uqq700_history_completeness(
        missing_exhaustive_enumeration,
        diagnostics={"latest_document_found": True},
    )
    checks.append(
        (
            "latest-looking document cannot replace exhaustive enumeration",
            rejected_enumeration["downstream_history_complete"] is False,
        )
    )

    unverified_identity = evidence()
    unverified_identity = Uqq700HistoryCompletenessProvenance(
        **{**unverified_identity.__dict__, "designation_identity_verified": False}
    )
    rejected_identity = verify_uqq700_history_completeness(unverified_identity)
    checks.append(
        (
            "unverified designation identity fails closed",
            rejected_identity["downstream_history_complete"] is False,
        )
    )

    missing_authority = evidence()
    missing_authority = Uqq700HistoryCompletenessProvenance(
        **{**missing_authority.__dict__, "issuing_authority": ""}
    )
    rejected_authority = verify_uqq700_history_completeness(missing_authority)
    checks.append(
        (
            "missing issuing authority fails closed",
            rejected_authority["downstream_history_complete"] is False,
        )
    )

    bad_scope_start = evidence()
    bad_scope_start = Uqq700HistoryCompletenessProvenance(
        **{**bad_scope_start.__dict__, "scope_start_date": "2000/01/01"}
    )
    rejected_start = verify_uqq700_history_completeness(bad_scope_start)
    checks.append(
        (
            "invalid scope start date fails closed",
            rejected_start["downstream_history_complete"] is False,
        )
    )

    reversed_scope = evidence()
    reversed_scope = Uqq700HistoryCompletenessProvenance(
        **{
            **reversed_scope.__dict__,
            "scope_start_date": "2026-09-09",
            "scope_end_date": "2000-01-01",
        }
    )
    rejected_order = verify_uqq700_history_completeness(reversed_scope)
    checks.append(
        (
            "reversed history scope fails closed",
            rejected_order["downstream_history_complete"] is False,
        )
    )

    snapshot_before_scope_end = evidence()
    snapshot_before_scope_end = Uqq700HistoryCompletenessProvenance(
        **{
            **snapshot_before_scope_end.__dict__,
            "scope_end_date": "2026-09-09",
            "authoritative_snapshot_date": "2026-09-08",
        }
    )
    rejected_snapshot = verify_uqq700_history_completeness(snapshot_before_scope_end)
    checks.append(
        (
            "snapshot before scope end fails closed",
            rejected_snapshot["downstream_history_complete"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE HISTORY COMPLETENESS VERIFIER TEST")
    print("=" * 96)
    print("Negative-evidence completeness inference: DISABLED")
    print("Source-family exhaustion inference: DISABLED")
    print("Current-validity auto-promotion: DISABLED")
    print("Production/runtime mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
