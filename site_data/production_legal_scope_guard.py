# -*- coding: utf-8 -*-
"""Fail-closed jurisdiction boundary for the current Seoul-only rule corpus.

This is a temporary scope gate, not a nationwide ordinance resolver and not
proof that every Seoul rule is legally applicable to an individual parcel.
"""
from __future__ import annotations

import re

SUPPORTED_SIDO_CODES = frozenset({"11"})
_PNU_PATTERN = re.compile(r"[0-9]{10}[12][0-9]{8}\Z")


class UnsupportedLegalJurisdictionError(RuntimeError):
    """Current production ordinance corpus is not qualified for this region."""


def require_supported_legal_jurisdiction(pnu: str) -> str:
    """Admit only a structurally valid Seoul PNU to the current rule engine.

    PNU is constructed or verified at the existing parcel identity boundaries.
    Checking its first two digits only limits this legacy Seoul ordinance
    corpus; it does not certify all underlying parcel facts or legal rules.
    """
    value = str(pnu or "").strip()
    if _PNU_PATTERN.fullmatch(value) is None:
        raise ValueError("Verified 19-digit PNU is required for legal jurisdiction gating")
    if value[:2] not in SUPPORTED_SIDO_CODES:
        raise UnsupportedLegalJurisdictionError(
            "Production legal corpus is not qualified for requested PNU jurisdiction"
        )
    return value
