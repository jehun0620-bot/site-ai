from __future__ import annotations

from hybrid_spatial_notice_uqq700_designation_document_provenance_verifier import (
    Uqq700DesignationDocumentProvenance,
    verify_uqq700_designation_document_provenance,
)
from hybrid_spatial_notice_uqq700_production_adapter import (
    Uqq700ProductionAdapterInput,
    adapt_uqq700_production_state,
)
from hybrid_spatial_notice_uqq700_verified_provenance_identity_adapter import (
    adapt_verified_uqq700_provenance_to_identity,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_VERIFIED_IDENTITY_PRODUCTION_CONTRACT_PASS"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_VERIFIED_IDENTITY_PRODUCTION_CONTRACT_REGRESSION"
)


def complete_evidence() -> Uqq700DesignationDocumentProvenance:
    document_id = "official-document-1"
    return Uqq700DesignationDocumentProvenance(
        candidate_qualified=True,
        official_source_qualified=True,
        document_id=document_id,
        target_name="개발밀도관리구역",
        target_name_source_document_id=document_id,
        designation_act_kind="DESIGNATION",
        designation_act_source_document_id=document_id,
        notice_number="성남시고시 제2000-1호",
        notice_number_source_document_id=document_id,
        issuing_authority="성남시장",
        issuing_authority_source_document_id=document_id,
        notice_or_effective_date="2000-01-01",
        notice_or_effective_date_source_document_id=document_id,
    )


def main() -> int:
    checks: list[tuple[str, bool]] = []

    evidence = complete_evidence()
    verification = verify_uqq700_designation_document_provenance(evidence)
    identity_stage = adapt_verified_uqq700_provenance_to_identity(
        evidence,
        verification,
        source_url="https://example.go.kr/notice/1",
    )

    result = adapt_uqq700_production_state(
        Uqq700ProductionAdapterInput(
            designation_identity=identity_stage,
        )
    )

    checks.append(
        (
            "verified provenance reaches production Gate 1",
            result["positive_gates"]["official_designation_identity_verified"] is True,
        )
    )
    checks.append(
        (
            "Gate 2 remains unverified",
            result["positive_gates"]["current_validity_verified"] is False,
        )
    )
    checks.append(
        (
            "Gate 3 remains unverified",
            result["positive_gates"]["site_spatial_inclusion_verified"] is False,
        )
    )
    checks.append(
        (
            "minimum registration gate stays closed",
            result["minimum_registration_gate_satisfied"] is False,
        )
    )
    checks.append(
        (
            "runtime registration stays blocked",
            result["runtime_registration_allowed"] is False,
        )
    )
    checks.append(("resolution stays UNKNOWN", result["resolution"] == "UNKNOWN"))
    checks.append(
        (
            "SITE promotion stays disabled",
            result["site_promotion_allowed"] is False
            and result["site_true_inference_allowed"] is False,
        )
    )
    checks.append(
        (
            "negative/legal-absence/SITE-FALSE inference stays disabled",
            result["negative_evidence_allowed"] is False
            and result["legal_absence_inference_allowed"] is False
            and result["site_false_inference_allowed"] is False,
        )
    )
    checks.append(
        (
            "designation identity payload is preserved as stage result",
            result["stage_results"]["designation_identity"][
                "official_designation_identity_verified"
            ]
            is True,
        )
    )
    checks.append(
        (
            "production adapter remains non-mutating",
            result["production_wiring_applied"] is False
            and result["runtime_registry_mutated"] is False,
        )
    )

    failed_evidence = complete_evidence()
    failed_verification = dict(verification)
    failed_verification["status"] = "NOT_VERIFIED"
    failed_identity_stage = adapt_verified_uqq700_provenance_to_identity(
        failed_evidence,
        failed_verification,
    )
    failed_result = adapt_uqq700_production_state(
        Uqq700ProductionAdapterInput(
            designation_identity=failed_identity_stage,
        )
    )

    checks.append(
        (
            "unverified provenance cannot reach production Gate 1",
            failed_result["positive_gates"][
                "official_designation_identity_verified"
            ]
            is False,
        )
    )
    checks.append(
        (
            "diagnostic-only evidence cannot manufacture Gate 1",
            adapt_uqq700_production_state(
                Uqq700ProductionAdapterInput(),
                search_hit=True,
                http_200=True,
                negative_evidence={"no_hit": True},
            )["positive_gates"]["official_designation_identity_verified"]
            is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE VERIFIED IDENTITY PRODUCTION CONTRACT TEST")
    print("=" * 96)
    print("Production wiring mutation: DISABLED")
    print("Current validity inference: DISABLED")
    print("SITE spatial inclusion inference: DISABLED")
    print("Runtime registration mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
