from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

VERIFIED = "VERIFIED_UQQ700_DOWNSTREAM_HISTORY_COMPLETENESS"
REJECTED_DESIGNATION_IDENTITY = "REJECTED_DESIGNATION_IDENTITY_UNVERIFIED"
REJECTED_ISSUING_AUTHORITY = "REJECTED_ISSUING_AUTHORITY_MISSING"
REJECTED_HISTORY_SOURCE = "REJECTED_HISTORY_SOURCE_UNQUALIFIED"
REJECTED_HISTORY_SOURCE_SCOPE = "REJECTED_HISTORY_SOURCE_SCOPE_UNVERIFIED"
REJECTED_SCOPE_START = "REJECTED_SCOPE_START_DATE"
REJECTED_SCOPE_END = "REJECTED_SCOPE_END_DATE"
REJECTED_SNAPSHOT_DATE = "REJECTED_AUTHORITATIVE_SNAPSHOT_DATE"
REJECTED_SCOPE_ORDER = "REJECTED_SCOPE_DATE_ORDER"
REJECTED_EXHAUSTIVE_ENUMERATION = "REJECTED_DOWNSTREAM_ENUMERATION_UNVERIFIED"


@dataclass(frozen=True)
class Uqq700HistoryCompletenessProvenance:
    designation_identity_verified: bool
    issuing_authority: str

    history_source_id: str
    history_source_official_verified: bool
    history_source_complete_for_authority_verified: bool

    scope_start_date: str
    scope_end_date: str
    authoritative_snapshot_date: str

    downstream_records_exhaustively_enumerated_verified: bool


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _parse_iso_date(value: Any) -> date | None:
    text = _normalized(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def verify_uqq700_history_completeness(
    evidence: Uqq700HistoryCompletenessProvenance,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify positive provenance for downstream legal-history completeness.

    This verifier accepts only an explicitly qualified authoritative history source
    whose capability is positively verified to cover the issuing authority and
    whose downstream records are positively verified as exhaustively enumerated
    across the declared scope. Search no-hit, source-family exhaustion, HTTP success,
    candidate counts, or "latest-looking" documents are never substitutes.

    It does not discover history, infer legal absence, verify parcel inclusion, or
    mutate production/runtime state.
    """

    issuing_authority = _normalized(evidence.issuing_authority)
    history_source_id = _normalized(evidence.history_source_id)
    scope_start = _parse_iso_date(evidence.scope_start_date)
    scope_end = _parse_iso_date(evidence.scope_end_date)
    snapshot_date = _parse_iso_date(evidence.authoritative_snapshot_date)

    scope_order_valid = bool(
        scope_start is not None
        and scope_end is not None
        and snapshot_date is not None
        and scope_start <= scope_end <= snapshot_date
    )

    if evidence.designation_identity_verified is not True:
        status = REJECTED_DESIGNATION_IDENTITY
    elif not issuing_authority:
        status = REJECTED_ISSUING_AUTHORITY
    elif not history_source_id or evidence.history_source_official_verified is not True:
        status = REJECTED_HISTORY_SOURCE
    elif evidence.history_source_complete_for_authority_verified is not True:
        status = REJECTED_HISTORY_SOURCE_SCOPE
    elif scope_start is None:
        status = REJECTED_SCOPE_START
    elif scope_end is None:
        status = REJECTED_SCOPE_END
    elif snapshot_date is None:
        status = REJECTED_SNAPSHOT_DATE
    elif not scope_order_valid:
        status = REJECTED_SCOPE_ORDER
    elif evidence.downstream_records_exhaustively_enumerated_verified is not True:
        status = REJECTED_EXHAUSTIVE_ENUMERATION
    else:
        status = VERIFIED

    verified = status == VERIFIED

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "status": status,
        "downstream_history_complete": verified,
        "history_completeness_verified": verified,
        "positive_provenance": {
            "designation_identity_verified": (
                evidence.designation_identity_verified is True
            ),
            "issuing_authority": issuing_authority if verified else "",
            "history_source_id": history_source_id if verified else "",
            "history_source_official_verified": (
                evidence.history_source_official_verified is True
            ),
            "history_source_complete_for_authority_verified": (
                evidence.history_source_complete_for_authority_verified is True
            ),
            "scope_start_date": scope_start.isoformat() if verified and scope_start else "",
            "scope_end_date": scope_end.isoformat() if verified and scope_end else "",
            "authoritative_snapshot_date": (
                snapshot_date.isoformat() if verified and snapshot_date else ""
            ),
            "downstream_records_exhaustively_enumerated_verified": (
                evidence.downstream_records_exhaustively_enumerated_verified is True
            ),
        },
        "search_no_hit_dispositive": False,
        "source_family_exhaustion_dispositive": False,
        "http_success_dispositive": False,
        "candidate_count_dispositive": False,
        "latest_document_dispositive": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "diagnostics_dispositive": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
        "diagnostics": dict(diagnostics or {}),
    }
