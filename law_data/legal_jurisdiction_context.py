# -*- coding: utf-8 -*-
"""PNU-based descriptive jurisdiction identity; NOT a legal authority resolver.

This module only splits the 19-character canonical parcel identifier into
administrative-code components. It does not independently verify the parcel,
a legal source, an ordinance's current validity, or SITE applicability.

Production ordinance admission remains the responsibility of the existing
fail-closed boundary; importing this module must not change that boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_PNU_PATTERN = re.compile(r"[0-9]{10}[12][0-9]{8}\Z")
_CODE_WIDTHS = {
    "sido_code": 2,
    "sigungu_code": 5,
    "bjdong_code": 5,
}


class JurisdictionIdentityMismatchError(ValueError):
    """The PNU's descriptive code disagrees with explicitly supplied identity."""


@dataclass(frozen=True, slots=True)
class LegalJurisdictionContext:
    """Immutable PNU structure, never evidence that any ordinance applies."""

    pnu: str
    sido_code: str
    sigungu_code: str
    bjdong_code: str
    land_division_code: str
    main_no: str
    sub_no: str

    def to_dict(self) -> dict[str, str]:
        """Expose only descriptive identity and an explicit non-decision state."""
        return {
            "pnu": self.pnu,
            "sido_code": self.sido_code,
            "sigungu_code": self.sigungu_code,
            "bjdong_code": self.bjdong_code,
            "land_division_code": self.land_division_code,
            "main_no": self.main_no,
            "sub_no": self.sub_no,
            "identity_basis": "PNU_STRUCTURE_ONLY",
            "legal_authority_decision": "NOT_EVALUATED",
            "legal_applicability_decision": "NOT_EVALUATED",
        }


def parse_legal_jurisdiction_context(
    pnu: str,
    *,
    expected_sido_code: str | None = None,
    expected_sigungu_code: str | None = None,
    expected_bjdong_code: str | None = None,
) -> LegalJurisdictionContext:
    """Parse a PNU and reject mismatching supplied administrative identities.

    Expected codes are exact caller-supplied identity checks, not proof of
    official administrative boundaries or legal authority. Caller must obtain
    any parcel verification and legal provenance independently.
    """
    if not isinstance(pnu, str):
        raise ValueError("PNU must be a 19-character ASCII-digit string")
    normalized = pnu.strip()
    if _PNU_PATTERN.fullmatch(normalized) is None:
        raise ValueError("PNU must contain 10 code digits, land 1/2, and 8 lot digits")

    context = LegalJurisdictionContext(
        pnu=normalized,
        sido_code=normalized[:2],
        sigungu_code=normalized[:5],
        bjdong_code=normalized[5:10],
        land_division_code=normalized[10],
        main_no=normalized[11:15],
        sub_no=normalized[15:19],
    )

    expectations = {
        "sido_code": expected_sido_code,
        "sigungu_code": expected_sigungu_code,
        "bjdong_code": expected_bjdong_code,
    }
    for name, expected in expectations.items():
        if expected is None:
            continue
        width = _CODE_WIDTHS[name]
        if (
            not isinstance(expected, str)
            or len(expected) != width
            or not expected.isascii()
            or not expected.isdigit()
        ):
            raise ValueError(f"{name} must be exactly {width} ASCII digits")
        actual = getattr(context, name)
        if actual != expected:
            raise JurisdictionIdentityMismatchError(
                f"PNU {name} mismatch: {actual} != {expected}"
            )

    return context
