from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from hybrid_spatial_notice_current_validity_resolver import (
    ACT_AMEND_CONTINUE,
    ACT_RELEASE,
    VerifiedNoticeAct,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

VERIFIED = "VERIFIED_UQQ700_DOWNSTREAM_NOTICE_PROVENANCE"
REJECTED_DOCUMENT_UNQUALIFIED = "REJECTED_DOCUMENT_UNQUALIFIED"
REJECTED_OFFICIAL_SOURCE_UNQUALIFIED = "REJECTED_OFFICIAL_SOURCE_UNQUALIFIED"
REJECTED_DOCUMENT_ID_MISSING = "REJECTED_DOCUMENT_ID_MISSING"
REJECTED_TARGET_BINDING = "REJECTED_TARGET_DOCUMENT_LOCAL_BINDING"
REJECTED_ACT_BINDING = "REJECTED_DOWNSTREAM_ACT_DOCUMENT_LOCAL_BINDING"
REJECTED_NOTICE_NUMBER_BINDING = "REJECTED_NOTICE_NUMBER_DOCUMENT_LOCAL_BINDING"
REJECTED_ISSUING_AUTHORITY_BINDING = "REJECTED_ISSUING_AUTHORITY_DOCUMENT_LOCAL_BINDING"
REJECTED_EFFECTIVE_DATE_BINDING = "REJECTED_EFFECTIVE_DATE_DOCUMENT_LOCAL_BINDING"
REJECTED_EFFECTIVE_DATE_FORMAT = "REJECTED_EFFECTIVE_DATE_FORMAT"

ALLOWED_DOWNSTREAM_ACT_KINDS = {
    "AMEND_CONTINUE": ACT_AMEND_CONTINUE,
    "RELEASE": ACT_RELEASE,
}


@dataclass(frozen=True)
class Uqq700DownstreamNoticeProvenance:
    candidate_qualified: bool
    official_source_qualified: bool
    document_id: str

    target_name: str
    target_name_source_document_id: str

    downstream_act_kind: str
    downstream_act_source_document_id: str

    notice_number: str
    notice_number_source_document_id: str

    issuing_authority: str
    issuing_authority_source_document_id: str

    effective_date: str
    effective_date_source_document_id: str


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _same_document(document_id: str, source_document_id: str) -> bool:
    document = _normalized(document_id)
    source = _normalized(source_document_id)
    return bool(document and source and document == source)


def _field_bound(document_id: str, value: Any, source_document_id: str) -> bool:
    return bool(_normalized(value)) and _same_document(document_id, source_document_id)


def _parse_iso_date(value: Any) -> date | None:
    text = _normalized(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def verify_uqq700_downstream_notice_provenance(
    evidence: Uqq700DownstreamNoticeProvenance,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify one UQQ700 downstream amendment/release notice fail-closed.

    A downstream act is accepted only when the target, explicit legal-act
    classification, notice number, issuing authority, and effective date are all
    bound to the same qualified official document. Search/title/HTTP/negative
    diagnostics are never substitutes for document-local legal provenance.

    This verifier emits at most one identity-verified validity act. It never infers
    downstream history completeness and never verifies current validity by itself.
    """

    document_id = _normalized(evidence.document_id)
    target_name = _normalized(evidence.target_name)
    downstream_act_kind = _normalized(evidence.downstream_act_kind).upper()
    act_type = ALLOWED_DOWNSTREAM_ACT_KINDS.get(downstream_act_kind)

    target_name_bound = (
        target_name == TARGET_NAME
        and _same_document(document_id, evidence.target_name_source_document_id)
    )
    downstream_act_bound = (
        act_type is not None
        and _same_document(document_id, evidence.downstream_act_source_document_id)
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
    effective_date_bound = _field_bound(
        document_id,
        evidence.effective_date,
        evidence.effective_date_source_document_id,
    )
    parsed_effective_date = _parse_iso_date(evidence.effective_date)

    if not evidence.candidate_qualified:
        status = REJECTED_DOCUMENT_UNQUALIFIED
    elif not evidence.official_source_qualified:
        status = REJECTED_OFFICIAL_SOURCE_UNQUALIFIED
    elif not document_id:
        status = REJECTED_DOCUMENT_ID_MISSING
    elif not target_name_bound:
        status = REJECTED_TARGET_BINDING
    elif not downstream_act_bound:
        status = REJECTED_ACT_BINDING
    elif not notice_number_bound:
        status = REJECTED_NOTICE_NUMBER_BINDING
    elif not issuing_authority_bound:
        status = REJECTED_ISSUING_AUTHORITY_BINDING
    elif not effective_date_bound:
        status = REJECTED_EFFECTIVE_DATE_BINDING
    elif parsed_effective_date is None:
        status = REJECTED_EFFECTIVE_DATE_FORMAT
    else:
        status = VERIFIED

    verified = status == VERIFIED
    verified_notice_act = None
    if verified and act_type is not None and parsed_effective_date is not None:
        verified_notice_act = VerifiedNoticeAct(
            act_type=act_type,
            effective_date=parsed_effective_date,
            official_designation_identity_verified=True,
            notice_number=_normalized(evidence.notice_number),
        )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "status": status,
        "downstream_notice_provenance_verified": verified,
        "verified_notice_act": verified_notice_act,
        "document_local_provenance": {
            "document_id_present": bool(document_id),
            "target_name_bound": target_name_bound,
            "downstream_act_bound": downstream_act_bound,
            "notice_number_bound": notice_number_bound,
            "issuing_authority_bound": issuing_authority_bound,
            "effective_date_bound": effective_date_bound,
            "all_required_fields_same_document": all(
                [
                    target_name_bound,
                    downstream_act_bound,
                    notice_number_bound,
                    issuing_authority_bound,
                    effective_date_bound,
                ]
            ),
            "document_id": document_id if verified else "",
            "notice_number": _normalized(evidence.notice_number) if verified else "",
            "issuing_authority": (
                _normalized(evidence.issuing_authority) if verified else ""
            ),
            "effective_date": (
                parsed_effective_date.isoformat()
                if verified and parsed_effective_date is not None
                else ""
            ),
            "act_type": act_type if verified else "",
        },
        "downstream_history_complete": False,
        "downstream_history_complete_inferred": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "diagnostics_dispositive": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
        "diagnostics": dict(diagnostics or {}),
    }
