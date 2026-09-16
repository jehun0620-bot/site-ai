from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence


CONDITION_NAME = "지구단위계획"
IDENTITY_FIELDS = (
    "ANCMNT_MNG_CD",
    "ANCMNT_YMD",
    "ANCMNT_NO",
    "ANCMNT_INST",
    "TTL",
)
POSITIVE_VALIDITY_STATES = {"CURRENT", "IN_FORCE", "VALID"}
INVALIDATING_STATES = {
    "REPEALED",
    "REVOKED",
    "EXPIRED",
    "INVALID",
    "SUPERSEDED",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _identity_matches(
    designation_identity: Mapping[str, Any],
    evidence_identity: Mapping[str, Any],
) -> bool:
    return all(
        _text(designation_identity.get(field))
        and _text(designation_identity.get(field)) == _text(evidence_identity.get(field))
        for field in IDENTITY_FIELDS
    )


def verify_district_unit_plan_current_validity(
    designation_verification: Mapping[str, Any] | None,
    notice_chain_evidence: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Verify current validity from explicit, identity-bound notice-chain evidence.

    This verifier consumes already-verified designation identity and upstream
    notice-chain evidence. It never treats missing/search-failure evidence as
    proof of validity and does not decide SITE truth, parcel applicability,
    promotion, or production/runtime registration authority.
    """

    designation = dict(designation_verification or {})
    designation_identity = designation.get("announcement_identity")
    designation_identity = (
        dict(designation_identity) if isinstance(designation_identity, Mapping) else {}
    )
    identity_verified = (
        designation.get("official_designation_identity_verified") is True
        and designation.get("condition_name") == CONDITION_NAME
        and all(_text(designation_identity.get(field)) for field in IDENTITY_FIELDS)
    )

    evidence_items = list(notice_chain_evidence or [])
    positive_items: list[dict[str, Any]] = []
    invalidating_items: list[dict[str, Any]] = []
    rejected_items: list[dict[str, Any]] = []

    for raw_item in evidence_items:
        if not isinstance(raw_item, Mapping):
            rejected_items.append({"reason": "MALFORMED_EVIDENCE"})
            continue

        item = dict(raw_item)
        bound_identity = item.get("designation_identity")
        bound_identity = dict(bound_identity) if isinstance(bound_identity, Mapping) else {}

        if not identity_verified or not _identity_matches(designation_identity, bound_identity):
            rejected_items.append({"reason": "DESIGNATION_IDENTITY_MISMATCH"})
            continue

        if item.get("query_success") is not True:
            rejected_items.append({"reason": "SOURCE_NOT_VERIFIED"})
            continue

        if item.get("authority_verified") is not True:
            rejected_items.append({"reason": "AUTHORITY_NOT_VERIFIED"})
            continue

        if item.get("notice_chain_verified") is not True:
            rejected_items.append({"reason": "NOTICE_CHAIN_NOT_VERIFIED"})
            continue

        state = _text(item.get("current_validity_state")).upper()
        if state in INVALIDATING_STATES:
            invalidating_items.append(deepcopy(item))
        elif state in POSITIVE_VALIDITY_STATES and item.get("explicit_current_effect_verified") is True:
            positive_items.append(deepcopy(item))
        else:
            rejected_items.append({"reason": "AMBIGUOUS_OR_NONEXPLICIT_VALIDITY"})

    verified = (
        identity_verified
        and bool(positive_items)
        and not invalidating_items
    )

    return {
        "official_designation_identity_verified": identity_verified,
        "condition_name": CONDITION_NAME,
        "announcement_identity": deepcopy(designation_identity) if identity_verified else {},
        "current_validity_verified": verified,
        "validity_state": "VERIFIED_CURRENT" if verified else "UNKNOWN",
        "checks": {
            "identity_verified": identity_verified,
            "positive_evidence_count": len(positive_items),
            "invalidating_evidence_count": len(invalidating_items),
            "rejected_evidence_count": len(rejected_items),
        },
        "verified_current_validity_evidence": positive_items if verified else [],
        "site_spatial_inclusion_verified": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }
