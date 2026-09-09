from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hybrid_spatial_notice_designation_identity_verifier import (
    DesignationIdentityEvidence,
    verify_designation_identity,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

VERIFIED = "VERIFIED_UQQ700_DESIGNATION_DOCUMENT_PROVENANCE"
REJECTED_DOCUMENT_UNQUALIFIED = "REJECTED_DOCUMENT_UNQUALIFIED"
REJECTED_OFFICIAL_SOURCE_UNQUALIFIED = "REJECTED_OFFICIAL_SOURCE_UNQUALIFIED"
REJECTED_DOCUMENT_ID_MISSING = "REJECTED_DOCUMENT_ID_MISSING"
REJECTED_TARGET_BINDING = "REJECTED_TARGET_DOCUMENT_LOCAL_BINDING"
REJECTED_DESIGNATION_ACT_BINDING = "REJECTED_DESIGNATION_ACT_DOCUMENT_LOCAL_BINDING"
REJECTED_NOTICE_NUMBER_BINDING = "REJECTED_NOTICE_NUMBER_DOCUMENT_LOCAL_BINDING"
REJECTED_ISSUING_AUTHORITY_BINDING = "REJECTED_ISSUING_AUTHORITY_DOCUMENT_LOCAL_BINDING"
REJECTED_NOTICE_DATE_BINDING = "REJECTED_NOTICE_DATE_DOCUMENT_LOCAL_BINDING"
REJECTED_GENERAL_IDENTITY = "REJECTED_GENERAL_DESIGNATION_IDENTITY"

# Upstream must explicitly classify the legal act. This verifier does not infer an
# act from free text. A generic change/amendment classification is intentionally
# excluded because it does not, by itself, establish the original designation act.
ALLOWED_DESIGNATION_ACT_KINDS = {
    "DESIGNATION",
    "URBAN_PLANNING_DECISION",
}


@dataclass(frozen=True)
class Uqq700DesignationDocumentProvenance:
    """Structured, document-local evidence for UQQ700 designation identity.

    Every legal-identity field carries the source document id from which it was
    extracted. The verifier accepts a binding only when that id exactly matches the
    qualified official document id. It never promotes based on search terms, page
    titles, HTTP status, source-family authority metadata, or negative evidence.
    """

    candidate_qualified: bool
    official_source_qualified: bool
    document_id: str

    target_name: str
    target_name_source_document_id: str

    designation_act_kind: str
    designation_act_source_document_id: str

    notice_number: str
    notice_number_source_document_id: str

    issuing_authority: str
    issuing_authority_source_document_id: str

    notice_or_effective_date: str
    notice_or_effective_date_source_document_id: str


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _same_document(document_id: str, source_document_id: str) -> bool:
    document = _normalized(document_id)
    source = _normalized(source_document_id)
    return bool(document and source and document == source)


def _field_bound(document_id: str, value: Any, source_document_id: str) -> bool:
    return bool(_normalized(value)) and _same_document(document_id, source_document_id)


def verify_uqq700_designation_document_provenance(
    evidence: Uqq700DesignationDocumentProvenance,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify UQQ700 designation identity using only same-document provenance.

    This is a fail-closed bridge into the generalized designation identity verifier.
    It does not establish current validity, parcel inclusion, SITE truth, legal
    absence, or runtime registration eligibility.
    """

    document_id = _normalized(evidence.document_id)
    target_name = _normalized(evidence.target_name)
    designation_act_kind = _normalized(evidence.designation_act_kind).upper()

    target_name_bound = (
        target_name == TARGET_NAME
        and _same_document(document_id, evidence.target_name_source_document_id)
    )
    designation_act_bound = (
        designation_act_kind in ALLOWED_DESIGNATION_ACT_KINDS
        and _same_document(document_id, evidence.designation_act_source_document_id)
    )
    notice_number_bound = _field_bound(
        document_id,
        evidence.notice_number,
        evidence.notice_number_source_document_id,
    )
    issuing_authority_bound = _field_bound(
        document_id,
        evidence.issuing_authority,
        evidence.issuing_authority_source_document_id,
    )
    notice_date_bound = _field_bound(
        document_id,
        evidence.notice_or_effective_date,
        evidence.notice_or_effective_date_source_document_id,
    )

    generalized = verify_designation_identity(
        DesignationIdentityEvidence(
            candidate_qualified=evidence.candidate_qualified,
            authority_source_qualified=evidence.official_source_qualified,
            target_name_bound=target_name_bound,
            designation_act_bound=designation_act_bound,
            notice_number_bound=notice_number_bound,
            issuing_authority_bound=issuing_authority_bound,
            effective_or_notice_date_bound=notice_date_bound,
        ),
        diagnostics=diagnostics,
    )

    if not evidence.candidate_qualified:
        status = REJECTED_DOCUMENT_UNQUALIFIED
    elif not evidence.official_source_qualified:
        status = REJECTED_OFFICIAL_SOURCE_UNQUALIFIED
    elif not document_id:
        status = REJECTED_DOCUMENT_ID_MISSING
    elif not target_name_bound:
        status = REJECTED_TARGET_BINDING
    elif not designation_act_bound:
        status = REJECTED_DESIGNATION_ACT_BINDING
    elif not notice_number_bound:
        status = REJECTED_NOTICE_NUMBER_BINDING
    elif not issuing_authority_bound:
        status = REJECTED_ISSUING_AUTHORITY_BINDING
    elif not notice_date_bound:
        status = REJECTED_NOTICE_DATE_BINDING
    elif generalized["official_designation_identity_verified"] is not True:
        status = REJECTED_GENERAL_IDENTITY
    else:
        status = VERIFIED

    verified = status == VERIFIED

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "status": status,
        "official_designation_identity_verified": verified,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "legal_absence_inference_allowed": False,
        "negative_evidence_allowed": False,
        "document_local_provenance": {
            "document_id_present": bool(document_id),
            "target_name_bound": target_name_bound,
            "designation_act_bound": designation_act_bound,
            "notice_number_bound": notice_number_bound,
            "issuing_authority_bound": issuing_authority_bound,
            "effective_or_notice_date_bound": notice_date_bound,
            "all_identity_fields_same_document": all(
                [
                    target_name_bound,
                    designation_act_bound,
                    notice_number_bound,
                    issuing_authority_bound,
                    notice_date_bound,
                ]
            ),
        },
        "generalized_identity": generalized,
        "diagnostics": dict(diagnostics or {}),
    }
