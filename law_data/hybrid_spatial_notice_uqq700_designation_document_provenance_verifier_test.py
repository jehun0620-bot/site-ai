from __future__ import annotations

from dataclasses import replace

from hybrid_spatial_notice_uqq700_designation_document_provenance_verifier import (
    REJECTED_DESIGNATION_ACT_BINDING,
    REJECTED_DOCUMENT_ID_MISSING,
    REJECTED_ISSUING_AUTHORITY_BINDING,
    REJECTED_NOTICE_DATE_BINDING,
    REJECTED_NOTICE_NUMBER_BINDING,
    REJECTED_TARGET_BINDING,
    Uqq700DesignationDocumentProvenance,
    VERIFIED,
    verify_uqq700_designation_document_provenance,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_DESIGNATION_DOCUMENT_PROVENANCE_VERIFIER_PASS"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_DESIGNATION_DOCUMENT_PROVENANCE_VERIFIER_REGRESSION"
)


def complete_evidence() -> Uqq700DesignationDocumentProvenance:
    document_id = "official-document-001"
    return Uqq700DesignationDocumentProvenance(
        candidate_qualified=True,
        official_source_qualified=True,
        document_id=document_id,
        target_name="개발밀도관리구역",
        target_name_source_document_id=document_id,
        designation_act_kind="DESIGNATION",
        designation_act_source_document_id=document_id,
        notice_number="성남시 고시 제2000-1호",
        notice_number_source_document_id=document_id,
        issuing_authority="성남시장",
        issuing_authority_source_document_id=document_id,
        notice_or_effective_date="2000-01-01",
        notice_or_effective_date_source_document_id=document_id,
    )


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    verified = verify_uqq700_designation_document_provenance(complete_evidence())
    checks.append(
        (
            "complete same-document provenance can verify identity only",
            (
                verified["status"] == VERIFIED
                and verified["official_designation_identity_verified"] is True
                and verified["current_validity_verified"] is False
                and verified["site_spatial_inclusion_verified"] is False
                and verified["minimum_registration_gate_satisfied"] is False
                and verified["runtime_registration_allowed"] is False
                and verified["site_false_inference_allowed"] is False
                and verified["site_promotion_allowed"] is False
                and verified["legal_absence_inference_allowed"] is False
                and verified["negative_evidence_allowed"] is False
            ),
            verified["status"],
        )
    )

    missing_document = verify_uqq700_designation_document_provenance(
        replace(complete_evidence(), document_id="")
    )
    checks.append(
        (
            "missing qualified document identity fails closed",
            missing_document["status"] == REJECTED_DOCUMENT_ID_MISSING
            and missing_document["official_designation_identity_verified"] is False,
            missing_document["status"],
        )
    )

    mismatches = [
        (
            "target must be document-local",
            replace(
                complete_evidence(),
                target_name_source_document_id="other-document",
            ),
            REJECTED_TARGET_BINDING,
        ),
        (
            "designation act must be document-local",
            replace(
                complete_evidence(),
                designation_act_source_document_id="other-document",
            ),
            REJECTED_DESIGNATION_ACT_BINDING,
        ),
        (
            "notice number must be document-local",
            replace(
                complete_evidence(),
                notice_number_source_document_id="other-document",
            ),
            REJECTED_NOTICE_NUMBER_BINDING,
        ),
        (
            "issuing authority must be document-local",
            replace(
                complete_evidence(),
                issuing_authority_source_document_id="other-document",
            ),
            REJECTED_ISSUING_AUTHORITY_BINDING,
        ),
        (
            "notice date must be document-local",
            replace(
                complete_evidence(),
                notice_or_effective_date_source_document_id="other-document",
            ),
            REJECTED_NOTICE_DATE_BINDING,
        ),
    ]

    for label, evidence, expected_status in mismatches:
        result = verify_uqq700_designation_document_provenance(evidence)
        checks.append(
            (
                label,
                result["status"] == expected_status
                and result["official_designation_identity_verified"] is False,
                result["status"],
            )
        )

    wrong_target = verify_uqq700_designation_document_provenance(
        replace(complete_evidence(), target_name="도시계획시설")
    )
    checks.append(
        (
            "other regulation cannot satisfy UQQ700 target binding",
            wrong_target["status"] == REJECTED_TARGET_BINDING
            and wrong_target["official_designation_identity_verified"] is False,
            wrong_target["status"],
        )
    )

    ambiguous_act = verify_uqq700_designation_document_provenance(
        replace(complete_evidence(), designation_act_kind="AMEND")
    )
    checks.append(
        (
            "generic amendment cannot be inferred as designation act",
            ambiguous_act["status"] == REJECTED_DESIGNATION_ACT_BINDING
            and ambiguous_act["official_designation_identity_verified"] is False,
            ambiguous_act["status"],
        )
    )

    missing_authority = verify_uqq700_designation_document_provenance(
        replace(complete_evidence(), issuing_authority="")
    )
    checks.append(
        (
            "authority name must exist in same document provenance",
            missing_authority["status"] == REJECTED_ISSUING_AUTHORITY_BINDING
            and missing_authority["official_designation_identity_verified"] is False,
            missing_authority["status"],
        )
    )

    diagnostic_only = verify_uqq700_designation_document_provenance(
        replace(
            complete_evidence(),
            designation_act_kind="",
            issuing_authority="",
        ),
        diagnostics={
            "search_hit": True,
            "http_200": True,
            "page_title_mentions_target": True,
            "source_family_authority_name": "성남시장",
            "negative_evidence": True,
        },
    )
    checks.append(
        (
            "diagnostics cannot manufacture document-local legal identity",
            diagnostic_only["official_designation_identity_verified"] is False
            and diagnostic_only["runtime_registration_allowed"] is False
            and diagnostic_only["site_promotion_allowed"] is False
            and diagnostic_only["legal_absence_inference_allowed"] is False,
            diagnostic_only["status"],
        )
    )

    all_pass = all(passed for _, passed, _ in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE DESIGNATION DOCUMENT PROVENANCE VERIFIER TEST")
    print("=" * 96)
    print("Network access: DISABLED")
    print("Discovery: DISABLED")
    print("Heuristic legal-act inference: DISABLED")
    print("Cross-document field binding: DISABLED")
    print("Current validity inference: DISABLED")
    print("SITE promotion: DISABLED")
    print("Runtime registration: DISABLED")
    print()

    for label, passed, status in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'} -> {status}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
