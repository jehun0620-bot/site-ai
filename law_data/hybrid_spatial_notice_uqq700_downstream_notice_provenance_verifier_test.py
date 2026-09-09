from __future__ import annotations

from hybrid_spatial_notice_current_validity_resolver import (
    ACT_AMEND_CONTINUE,
    ACT_RELEASE,
    CURRENT_RELEASE_VERIFIED,
    CURRENT_VALIDITY_UNKNOWN,
    resolve_current_validity,
)
from hybrid_spatial_notice_uqq700_downstream_notice_provenance_verifier import (
    VERIFIED,
    Uqq700DownstreamNoticeProvenance,
    verify_uqq700_downstream_notice_provenance,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_DOWNSTREAM_NOTICE_PROVENANCE_VERIFIER_PASS"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_DOWNSTREAM_NOTICE_PROVENANCE_VERIFIER_REGRESSION"
)


def evidence(act_kind: str = "AMEND_CONTINUE") -> Uqq700DownstreamNoticeProvenance:
    document_id = "official-downstream-document-1"
    return Uqq700DownstreamNoticeProvenance(
        candidate_qualified=True,
        official_source_qualified=True,
        document_id=document_id,
        target_name="개발밀도관리구역",
        target_name_source_document_id=document_id,
        downstream_act_kind=act_kind,
        downstream_act_source_document_id=document_id,
        notice_number="성남시고시 제2005-2호",
        notice_number_source_document_id=document_id,
        issuing_authority="성남시장",
        issuing_authority_source_document_id=document_id,
        effective_date="2005-02-03",
        effective_date_source_document_id=document_id,
    )


def main() -> int:
    checks: list[tuple[str, bool]] = []

    amend = verify_uqq700_downstream_notice_provenance(evidence())
    amend_act = amend["verified_notice_act"]
    checks.append(
        (
            "same-document explicit amendment provenance is verified",
            amend["status"] == VERIFIED
            and amend["downstream_notice_provenance_verified"] is True,
        )
    )
    checks.append(
        (
            "verified amendment emits AMEND_CONTINUE act",
            amend_act is not None
            and amend_act.act_type == ACT_AMEND_CONTINUE
            and amend_act.official_designation_identity_verified is True,
        )
    )
    checks.append(
        (
            "amendment preserves notice and date",
            amend_act is not None
            and amend_act.notice_number == "성남시고시 제2005-2호"
            and amend_act.effective_date.isoformat() == "2005-02-03",
        )
    )
    checks.append(
        (
            "issuing authority remains preserved provenance",
            amend["document_local_provenance"]["issuing_authority"] == "성남시장",
        )
    )

    amend_validity = resolve_current_validity(
        [amend_act] if amend_act is not None else [],
        downstream_history_complete=False,
    )
    checks.append(
        (
            "verified amendment alone cannot establish current validity",
            amend_validity["status"] == CURRENT_VALIDITY_UNKNOWN
            and amend_validity["current_validity_verified"] is False,
        )
    )

    release = verify_uqq700_downstream_notice_provenance(evidence("RELEASE"))
    release_act = release["verified_notice_act"]
    checks.append(
        (
            "same-document explicit release provenance is verified",
            release["status"] == VERIFIED
            and release_act is not None
            and release_act.act_type == ACT_RELEASE,
        )
    )
    release_validity = resolve_current_validity(
        [release_act] if release_act is not None else [],
        downstream_history_complete=False,
    )
    checks.append(
        (
            "explicit verified release can establish current release only",
            release_validity["status"] == CURRENT_RELEASE_VERIFIED
            and release_validity["current_release_verified"] is True
            and release_validity["current_validity_verified"] is False,
        )
    )

    checks.append(
        (
            "verifier never infers history completeness",
            amend["downstream_history_complete"] is False
            and amend["downstream_history_complete_inferred"] is False
            and release["downstream_history_complete"] is False,
        )
    )
    checks.append(
        (
            "later gates runtime and safety inference remain closed",
            amend["current_validity_verified"] is False
            and amend["site_spatial_inclusion_verified"] is False
            and amend["minimum_registration_gate_satisfied"] is False
            and amend["runtime_registration_allowed"] is False
            and amend["negative_evidence_allowed"] is False
            and amend["legal_absence_inference_allowed"] is False
            and amend["site_false_inference_allowed"] is False
            and amend["site_promotion_allowed"] is False,
        )
    )

    cross_document = evidence()
    cross_document = Uqq700DownstreamNoticeProvenance(
        **{
            **cross_document.__dict__,
            "issuing_authority_source_document_id": "different-document",
        }
    )
    rejected_cross_document = verify_uqq700_downstream_notice_provenance(
        cross_document
    )
    checks.append(
        (
            "cross-document authority binding fails closed",
            rejected_cross_document["downstream_notice_provenance_verified"] is False
            and rejected_cross_document["verified_notice_act"] is None,
        )
    )

    generic_change = evidence("CHANGE")
    rejected_generic_change = verify_uqq700_downstream_notice_provenance(generic_change)
    checks.append(
        (
            "generic change classification cannot become amendment",
            rejected_generic_change["downstream_notice_provenance_verified"] is False
            and rejected_generic_change["verified_notice_act"] is None,
        )
    )

    bad_date = evidence()
    bad_date = Uqq700DownstreamNoticeProvenance(
        **{**bad_date.__dict__, "effective_date": "2005/02/03"}
    )
    rejected_bad_date = verify_uqq700_downstream_notice_provenance(bad_date)
    checks.append(
        (
            "non-ISO effective date fails closed",
            rejected_bad_date["downstream_notice_provenance_verified"] is False
            and rejected_bad_date["verified_notice_act"] is None,
        )
    )

    diagnostic_only = Uqq700DownstreamNoticeProvenance(
        candidate_qualified=False,
        official_source_qualified=False,
        document_id="",
        target_name="",
        target_name_source_document_id="",
        downstream_act_kind="",
        downstream_act_source_document_id="",
        notice_number="",
        notice_number_source_document_id="",
        issuing_authority="",
        issuing_authority_source_document_id="",
        effective_date="",
        effective_date_source_document_id="",
    )
    rejected_diagnostics = verify_uqq700_downstream_notice_provenance(
        diagnostic_only,
        diagnostics={
            "search_hit": True,
            "http_200": True,
            "title_contains_release": True,
            "search_no_hit": False,
        },
    )
    checks.append(
        (
            "diagnostics cannot manufacture downstream legal act",
            rejected_diagnostics["downstream_notice_provenance_verified"] is False
            and rejected_diagnostics["verified_notice_act"] is None
            and rejected_diagnostics["diagnostics_dispositive"] is False,
        )
    )
    checks.append(
        (
            "verifier is pure and non-mutating",
            amend["production_wiring_applied"] is False
            and amend["runtime_registry_mutated"] is False
            and amend["site_mutated"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE DOWNSTREAM NOTICE PROVENANCE VERIFIER TEST")
    print("=" * 96)
    print("Free-text legal-act inference: DISABLED")
    print("Cross-document provenance binding: DISABLED")
    print("History completeness inference: DISABLED")
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
