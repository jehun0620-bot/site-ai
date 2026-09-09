from __future__ import annotations

from copy import deepcopy

from hybrid_spatial_notice_uqq700_designation_document_provenance_verifier import (
    Uqq700DesignationDocumentProvenance,
    verify_uqq700_designation_document_provenance,
)
from hybrid_spatial_notice_uqq700_verified_provenance_identity_adapter import (
    adapt_verified_uqq700_provenance_to_identity,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_VERIFIED_PROVENANCE_IDENTITY_ADAPTER_PASS"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_VERIFIED_PROVENANCE_IDENTITY_ADAPTER_FAIL"
)


def evidence(**overrides) -> Uqq700DesignationDocumentProvenance:
    values = {
        "candidate_qualified": True,
        "official_source_qualified": True,
        "document_id": "OFFICIAL-DOC-001",
        "target_name": "개발밀도관리구역",
        "target_name_source_document_id": "OFFICIAL-DOC-001",
        "designation_act_kind": "DESIGNATION",
        "designation_act_source_document_id": "OFFICIAL-DOC-001",
        "notice_number": "성남시고시 제2000-1호",
        "notice_number_source_document_id": "OFFICIAL-DOC-001",
        "issuing_authority": "성남시장",
        "issuing_authority_source_document_id": "OFFICIAL-DOC-001",
        "notice_or_effective_date": "2000-01-01",
        "notice_or_effective_date_source_document_id": "OFFICIAL-DOC-001",
    }
    values.update(overrides)
    return Uqq700DesignationDocumentProvenance(**values)


def main() -> int:
    checks: list[tuple[str, bool]] = []

    source = evidence()
    verified = verify_uqq700_designation_document_provenance(source)
    source_before = deepcopy(source)
    verified_before = deepcopy(verified)

    result = adapt_verified_uqq700_provenance_to_identity(
        source,
        verified,
        source_url="https://example.go.kr/official/notice/1",
    )

    checks.extend(
        [
            (
                "verified same-document provenance is accepted",
                result["verification_accepted"] is True,
            ),
            (
                "accepted provenance can verify Gate 1 identity",
                result["official_designation_identity_verified"] is True,
            ),
            (
                "raw verified notice identity values are preserved",
                result["preserved_provenance"]["document_id"] == "OFFICIAL-DOC-001"
                and result["preserved_provenance"]["notice_number"]
                == "성남시고시 제2000-1호"
                and result["preserved_provenance"]["issuing_authority"] == "성남시장"
                and result["preserved_provenance"]["effective_or_notice_date"]
                == "2000-01-01",
            ),
            (
                "same-document guarantee survives conversion",
                result["preserved_provenance"]["all_identity_fields_same_document"]
                is True,
            ),
            (
                "historical candidate metadata is not reconstructed",
                result["historical_candidate_metadata_reconstructed"] is False,
            ),
            (
                "no cross-document binding or legal inference",
                result["cross_document_field_binding_performed"] is False
                and result["legal_inference_performed"] is False,
            ),
            (
                "identity success does not open later gates",
                result["identity_result"]["verification"]["current_validity_verified"]
                is False
                and result["identity_result"]["verification"][
                    "site_spatial_inclusion_verified"
                ]
                is False
                and result["identity_result"]["verification"][
                    "runtime_registration_allowed"
                ]
                is False
                and result["identity_result"]["verification"]["site_promotion_allowed"]
                is False,
            ),
            (
                "adapter is pure and does not mutate inputs",
                source == source_before and verified == verified_before,
            ),
            (
                "no production/runtime/SITE mutation",
                result["production_wiring_applied"] is False
                and result["runtime_registry_mutated"] is False
                and result["site_mutated"] is False,
            ),
        ]
    )

    rejected_source = evidence(
        issuing_authority_source_document_id="OTHER-DOC"
    )
    rejected_verification = verify_uqq700_designation_document_provenance(
        rejected_source
    )
    rejected = adapt_verified_uqq700_provenance_to_identity(
        rejected_source,
        rejected_verification,
    )
    checks.append(
        (
            "failed same-document verification fails closed",
            rejected["verification_accepted"] is False
            and rejected["official_designation_identity_verified"] is False
            and rejected["preserved_provenance"]["issuing_authority"] == "",
        )
    )

    tampered = deepcopy(verified)
    tampered["status"] = "VERIFIED_UQQ700_DESIGNATION_DOCUMENT_PROVENANCE_TAMPERED"
    tampered_result = adapt_verified_uqq700_provenance_to_identity(source, tampered)
    checks.append(
        (
            "noncanonical verified status fails closed",
            tampered_result["verification_accepted"] is False
            and tampered_result["official_designation_identity_verified"] is False,
        )
    )

    wrong_target = deepcopy(verified)
    wrong_target["target"] = "OTHER_TARGET"
    wrong_target_result = adapt_verified_uqq700_provenance_to_identity(
        source,
        wrong_target,
    )
    checks.append(
        (
            "wrong target verification fails closed",
            wrong_target_result["verification_accepted"] is False
            and wrong_target_result["official_designation_identity_verified"] is False,
        )
    )

    diagnostics_only = adapt_verified_uqq700_provenance_to_identity(
        source,
        {},
        diagnostics={
            "search_hit": True,
            "http_200": True,
            "negative_evidence": True,
        },
    )
    checks.append(
        (
            "diagnostics cannot substitute for verified provenance",
            diagnostics_only["verification_accepted"] is False
            and diagnostics_only["official_designation_identity_verified"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE VERIFIED PROVENANCE IDENTITY ADAPTER TEST")
    print("=" * 96)
    print("Network access: DISABLED")
    print("Historical candidate reconstruction: DISABLED")
    print("Cross-document field binding: DISABLED")
    print("Legal inference: DISABLED")
    print("Production wiring: DISABLED")
    print("Runtime registration mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
