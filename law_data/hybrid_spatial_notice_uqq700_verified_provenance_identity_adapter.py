from __future__ import annotations

from typing import Any, Mapping

from hybrid_spatial_notice_uqq700_designation_document_provenance_verifier import (
    VERIFIED,
    Uqq700DesignationDocumentProvenance,
)
from hybrid_spatial_notice_uqq700_identity_evidence_adapter import (
    Uqq700IdentityEvidenceInput,
    adapt_uqq700_identity_evidence,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


def adapt_verified_uqq700_provenance_to_identity(
    evidence: Uqq700DesignationDocumentProvenance,
    verification: Mapping[str, Any],
    *,
    source_url: str = "",
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Preserve verified same-document provenance into the Gate-1 adapter.

    This adapter accepts only provenance already verified by the UQQ700 designation
    document provenance verifier. Raw notice identity values are taken from the same
    original evidence object whose document-local bindings were verified; they are
    not reconstructed from historical candidate metadata or diagnostics.
    """

    provenance = verification.get("document_local_provenance")
    if not isinstance(provenance, Mapping):
        provenance = {}

    verification_accepted = (
        verification.get("target") == TARGET_NAME
        and verification.get("standard_code") == STANDARD_CODE
        and verification.get("resolution_type") == RESOLUTION_TYPE
        and verification.get("status") == VERIFIED
        and verification.get("official_designation_identity_verified") is True
        and provenance.get("all_identity_fields_same_document") is True
    )

    if verification_accepted:
        identity_input = Uqq700IdentityEvidenceInput(
            candidate_qualified=(evidence.candidate_qualified is True),
            authority_source_qualified=(evidence.official_source_qualified is True),
            target_name_bound=(provenance.get("target_name_bound") is True),
            designation_act_bound=(provenance.get("designation_act_bound") is True),
            notice_number=evidence.notice_number,
            issuing_authority=evidence.issuing_authority,
            effective_or_notice_date=evidence.notice_or_effective_date,
            source_url=source_url,
        )
    else:
        identity_input = Uqq700IdentityEvidenceInput(source_url=source_url)

    identity_result = adapt_uqq700_identity_evidence(
        identity_input,
        diagnostics=diagnostics,
    )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "verification_accepted": verification_accepted,
        "official_designation_identity_verified": identity_result[
            "official_designation_identity_verified"
        ],
        "identity_result": identity_result,
        "preserved_provenance": {
            "document_id": evidence.document_id if verification_accepted else "",
            "notice_number": evidence.notice_number if verification_accepted else "",
            "issuing_authority": (
                evidence.issuing_authority if verification_accepted else ""
            ),
            "effective_or_notice_date": (
                evidence.notice_or_effective_date if verification_accepted else ""
            ),
            "all_identity_fields_same_document": (
                provenance.get("all_identity_fields_same_document") is True
                if verification_accepted
                else False
            ),
        },
        "historical_candidate_metadata_reconstructed": False,
        "cross_document_field_binding_performed": False,
        "legal_inference_performed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
    }
