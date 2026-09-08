from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
CURRENT_VALIDITY_VERIFIED = "CURRENT_VALIDITY_VERIFIED"
CURRENT_RELEASE_VERIFIED = "CURRENT_RELEASE_VERIFIED"
CURRENT_VALIDITY_UNKNOWN = "CURRENT_VALIDITY_UNKNOWN"

ACT_DESIGNATE = "DESIGNATE"
ACT_AMEND_CONTINUE = "AMEND_CONTINUE"
ACT_RELEASE = "RELEASE"

VALID_ACT_TYPES = {ACT_DESIGNATE, ACT_AMEND_CONTINUE, ACT_RELEASE}


@dataclass(frozen=True)
class VerifiedNoticeAct:
    act_type: str
    effective_date: date
    official_designation_identity_verified: bool
    notice_number: str = ""


def resolve_current_validity(
    acts: Iterable[VerifiedNoticeAct],
    *,
    search_no_hit: bool | None = None,
    downstream_history_complete: bool = False,
) -> dict[str, object]:
    """Resolve current legal validity from identity-verified notice acts only.

    Negative discovery evidence is never dispositive. A current release can only
    be concluded from an explicit identity-verified RELEASE act. Likewise, the
    designation is treated as currently valid only when the latest verified legal
    act is DESIGNATE or AMEND_CONTINUE and the caller explicitly attests that the
    downstream amendment/release history is complete for the relevant authority.

    This resolver does not establish parcel inclusion or permit runtime registration.
    """

    verified_acts = [
        act
        for act in acts
        if act.official_designation_identity_verified and act.act_type in VALID_ACT_TYPES
    ]
    verified_acts.sort(key=lambda act: act.effective_date)

    latest = verified_acts[-1] if verified_acts else None

    if latest is None:
        status = CURRENT_VALIDITY_UNKNOWN
        current_validity_verified = False
        current_release_verified = False
    elif latest.act_type == ACT_RELEASE:
        status = CURRENT_RELEASE_VERIFIED
        current_validity_verified = False
        current_release_verified = True
    elif downstream_history_complete:
        status = CURRENT_VALIDITY_VERIFIED
        current_validity_verified = True
        current_release_verified = False
    else:
        status = CURRENT_VALIDITY_UNKNOWN
        current_validity_verified = False
        current_release_verified = False

    return {
        "resolution_type": RESOLUTION_TYPE,
        "status": status,
        "current_validity_verified": current_validity_verified,
        "current_release_verified": current_release_verified,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "history": {
            "verified_act_count": len(verified_acts),
            "downstream_history_complete": downstream_history_complete,
            "search_no_hit": search_no_hit,
            "search_no_hit_dispositive": False,
            "latest_verified_act_type": latest.act_type if latest else None,
            "latest_verified_effective_date": (
                latest.effective_date.isoformat() if latest else None
            ),
            "latest_verified_notice_number": latest.notice_number if latest else None,
        },
    }
