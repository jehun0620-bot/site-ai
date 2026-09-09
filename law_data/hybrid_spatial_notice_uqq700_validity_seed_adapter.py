from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from hybrid_spatial_notice_current_validity_resolver import (
    ACT_DESIGNATE,
    VerifiedNoticeAct,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _parse_iso_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None
    return parsed


def adapt_verified_uqq700_identity_to_validity_seed(
    identity_stage: Mapping[str, Any],
) -> dict[str, Any]:
    """Create only the original DESIGNATE seed for Gate 2.

    This adapter is intentionally narrower than the current-validity resolver. It
    accepts an already verified UQQ700 Gate-1 identity result and may emit one
    identity-verified DESIGNATE act. It never manufactures amendment/release acts,
    never infers downstream history completeness, and never establishes current
    validity by itself.
    """

    preserved = identity_stage.get("preserved_provenance")
    if not isinstance(preserved, Mapping):
        preserved = {}

    identity_accepted = (
        identity_stage.get("target") == TARGET_NAME
        and identity_stage.get("standard_code") == STANDARD_CODE
        and identity_stage.get("resolution_type") == RESOLUTION_TYPE
        and identity_stage.get("verification_accepted") is True
        and identity_stage.get("official_designation_identity_verified") is True
        and preserved.get("all_identity_fields_same_document") is True
    )

    document_id = _text(preserved.get("document_id"))
    notice_number = _text(preserved.get("notice_number"))
    issuing_authority = _text(preserved.get("issuing_authority"))
    effective_date = _parse_iso_date(preserved.get("effective_or_notice_date"))

    seed_accepted = bool(
        identity_accepted
        and document_id
        and notice_number
        and issuing_authority
        and effective_date is not None
    )

    acts: list[VerifiedNoticeAct] = []
    if seed_accepted and effective_date is not None:
        acts.append(
            VerifiedNoticeAct(
                act_type=ACT_DESIGNATE,
                effective_date=effective_date,
                official_designation_identity_verified=True,
                notice_number=notice_number,
            )
        )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "seed_accepted": seed_accepted,
        "verified_notice_acts": acts,
        "seed_provenance": {
            "document_id": document_id if seed_accepted else "",
            "notice_number": notice_number if seed_accepted else "",
            "issuing_authority": issuing_authority if seed_accepted else "",
            "effective_date": effective_date.isoformat() if seed_accepted else "",
            "act_type": ACT_DESIGNATE if seed_accepted else "",
        },
        "amend_continue_act_inferred": False,
        "release_act_inferred": False,
        "downstream_history_complete_inferred": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
    }
