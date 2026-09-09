from __future__ import annotations

from hybrid_spatial_notice_current_validity_resolver import (
    CURRENT_RELEASE_VERIFIED,
    CURRENT_VALIDITY_UNKNOWN,
    CURRENT_VALIDITY_VERIFIED,
    resolve_current_validity,
)
from hybrid_spatial_notice_uqq700_downstream_notice_provenance_verifier import (
    Uqq700DownstreamNoticeProvenance,
    verify_uqq700_downstream_notice_provenance,
)
from hybrid_spatial_notice_uqq700_history_completeness_verifier import (
    Uqq700HistoryCompletenessProvenance,
    verify_uqq700_history_completeness,
)
from hybrid_spatial_notice_uqq700_validity_seed_adapter import (
    adapt_verified_uqq700_identity_to_validity_seed,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_GATE2_COMPOSITION_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_GATE2_COMPOSITION_REGRESSION"


def verified_identity_stage() -> dict[str, object]:
    return {
        "target": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "verification_accepted": True,
        "official_designation_identity_verified": True,
        "preserved_provenance": {
            "document_id": "official-designation-document-1",
            "notice_number": "성남시고시 제2000-1호",
            "issuing_authority": "성남시장",
            "effective_or_notice_date": "2000-01-01",
            "all_identity_fields_same_document": True,
        },
    }


def downstream_evidence(act_kind: str, document_id: str, notice_number: str, effective_date: str):
    return Uqq700DownstreamNoticeProvenance(
        candidate_qualified=True,
        official_source_qualified=True,
        document_id=document_id,
        target_name="개발밀도관리구역",
        target_name_source_document_id=document_id,
        downstream_act_kind=act_kind,
        downstream_act_source_document_id=document_id,
        notice_number=notice_number,
        notice_number_source_document_id=document_id,
        issuing_authority="성남시장",
        issuing_authority_source_document_id=document_id,
        effective_date=effective_date,
        effective_date_source_document_id=document_id,
    )


def complete_history() -> dict[str, object]:
    return verify_uqq700_history_completeness(
        Uqq700HistoryCompletenessProvenance(
            designation_identity_verified=True,
            issuing_authority="성남시장",
            history_source_id="official-history-source-1",
            history_source_official_verified=True,
            history_source_complete_for_authority_verified=True,
            scope_start_date="2000-01-01",
            scope_end_date="2026-09-09",
            authoritative_snapshot_date="2026-09-09",
            downstream_records_exhaustively_enumerated_verified=True,
        )
    )


def main() -> int:
    checks: list[tuple[str, bool]] = []

    seed_result = adapt_verified_uqq700_identity_to_validity_seed(verified_identity_stage())
    seed_acts = seed_result["verified_notice_acts"]
    seed_act = seed_acts[0] if len(seed_acts) == 1 else None
    checks.append(
        (
            "verified Gate 1 produces exactly one DESIGNATE seed",
            seed_result["seed_accepted"] is True and seed_act is not None,
        )
    )

    amend_result = verify_uqq700_downstream_notice_provenance(
        downstream_evidence(
            "AMEND_CONTINUE",
            "official-amend-document-1",
            "성남시고시 제2005-2호",
            "2005-02-03",
        )
    )
    amend_act = amend_result["verified_notice_act"]
    checks.append(("verified downstream amendment produces act", amend_act is not None))

    completeness = complete_history()
    checks.append(
        (
            "positive provenance verifies downstream history completeness",
            completeness["downstream_history_complete"] is True,
        )
    )

    validity = resolve_current_validity(
        [act for act in [seed_act, amend_act] if act is not None],
        downstream_history_complete=completeness["downstream_history_complete"] is True,
    )
    checks.append(
        (
            "latest AMEND_CONTINUE plus complete history verifies current validity",
            validity["status"] == CURRENT_VALIDITY_VERIFIED
            and validity["current_validity_verified"] is True
            and validity["current_release_verified"] is False,
        )
    )
    checks.append(
        (
            "Gate 2 validity alone never opens Gate 3 or runtime",
            validity["site_spatial_inclusion_verified"] is False
            and validity["minimum_registration_gate_satisfied"] is False
            and validity["runtime_registration_allowed"] is False
            and validity["site_promotion_allowed"] is False
            and validity["site_false_inference_allowed"] is False,
        )
    )

    incomplete_validity = resolve_current_validity(
        [act for act in [seed_act, amend_act] if act is not None],
        downstream_history_complete=False,
        search_no_hit=True,
    )
    checks.append(
        (
            "same verified acts without completeness remain UNKNOWN",
            incomplete_validity["status"] == CURRENT_VALIDITY_UNKNOWN
            and incomplete_validity["current_validity_verified"] is False
            and incomplete_validity["history"]["search_no_hit_dispositive"] is False,
        )
    )

    release_result = verify_uqq700_downstream_notice_provenance(
        downstream_evidence(
            "RELEASE",
            "official-release-document-1",
            "성남시고시 제2010-3호",
            "2010-04-05",
        )
    )
    release_act = release_result["verified_notice_act"]
    release_resolution = resolve_current_validity(
        [act for act in [seed_act, amend_act, release_act] if act is not None],
        downstream_history_complete=False,
    )
    checks.append(
        (
            "latest explicit RELEASE verifies current release not current validity",
            release_resolution["status"] == CURRENT_RELEASE_VERIFIED
            and release_resolution["current_release_verified"] is True
            and release_resolution["current_validity_verified"] is False,
        )
    )
    checks.append(
        (
            "verified release still cannot infer SITE FALSE or legal absence",
            release_resolution["negative_evidence_allowed"] is False
            and release_resolution["legal_absence_inference_allowed"] is False
            and release_resolution["site_false_inference_allowed"] is False
            and release_resolution["site_promotion_allowed"] is False,
        )
    )

    bad_completeness = verify_uqq700_history_completeness(
        Uqq700HistoryCompletenessProvenance(
            designation_identity_verified=True,
            issuing_authority="성남시장",
            history_source_id="official-history-source-1",
            history_source_official_verified=True,
            history_source_complete_for_authority_verified=False,
            scope_start_date="2000-01-01",
            scope_end_date="2026-09-09",
            authoritative_snapshot_date="2026-09-09",
            downstream_records_exhaustively_enumerated_verified=True,
        ),
        diagnostics={"search_no_hit": True, "source_family_exhausted": True},
    )
    bad_resolution = resolve_current_validity(
        [act for act in [seed_act, amend_act] if act is not None],
        downstream_history_complete=bad_completeness["downstream_history_complete"] is True,
        search_no_hit=True,
    )
    checks.append(
        (
            "negative discovery cannot manufacture completeness or current validity",
            bad_completeness["downstream_history_complete"] is False
            and bad_completeness["diagnostics_dispositive"] is False
            and bad_resolution["status"] == CURRENT_VALIDITY_UNKNOWN
            and bad_resolution["current_validity_verified"] is False,
        )
    )

    checks.append(
        (
            "composition remains pure and production-unwired",
            seed_result["production_wiring_applied"] is False
            and amend_result["production_wiring_applied"] is False
            and completeness["production_wiring_applied"] is False
            and amend_result["runtime_registry_mutated"] is False
            and completeness["runtime_registry_mutated"] is False
            and amend_result["site_mutated"] is False
            and completeness["site_mutated"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE GATE 2 COMPOSITION REGRESSION TEST")
    print("=" * 96)
    print("Synthetic positive Gate 2 composition: TEST-ONLY")
    print("Real UQQ700 production Gate 2 wiring: DISABLED")
    print("Negative-evidence completeness inference: DISABLED")
    print("Gate 3/runtime promotion: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
