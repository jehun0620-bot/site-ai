# -*- coding: utf-8 -*-
"""Credential-free *description* of two tested MOLEG DRF request shapes.

This module has no HTTP, credential, filesystem, or legal-decision capability.
A public descriptor is NOT the URL of an authenticated request, an acquisition
receipt, proof of origin, a current-law selection, or permission for production.
Only the specifically tested eflaw/MST/efYd and ordin/MST shapes are accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode


SCHEMA_VERSION = "LEGAL_PUBLIC_REQUEST_V1"
SOURCE_SYSTEM = "MOLEG_DRF"
ENDPOINT = "https://www.law.go.kr/DRF/lawService.do"
RECORD_KIND = "PUBLIC_REQUEST_DESCRIPTOR"

_MST = re.compile(r"[0-9]{1,20}\Z")
_EFYD = re.compile(r"[0-9]{8}\Z")
_FIELDS = {
    "eflaw": frozenset(("target", "type", "MST", "efYd")),
    "ordin": frozenset(("target", "type", "MST")),
}


def _validate(target: object, mst: object, efyd: object) -> None:
    """Fail closed without interpolating caller input into exceptions."""
    if type(target) is not str or target not in _FIELDS:
        raise ValueError("INVALID_TARGET")
    if type(mst) is not str or _MST.fullmatch(mst) is None:
        raise ValueError("INVALID_MST")
    if target == "ordin":
        if efyd is not None:
            raise ValueError("EFYD_FORBIDDEN_FOR_ORDIN")
        return
    if type(efyd) is not str or _EFYD.fullmatch(efyd) is None:
        raise ValueError("INVALID_EFYD")
    try:
        date(int(efyd[:4]), int(efyd[4:6]), int(efyd[6:8]))
    except ValueError:
        raise ValueError("INVALID_EFYD") from None


@dataclass(frozen=True, slots=True)
class LegalSourcePublicRequestDescriptor:
    """Immutable credential-free request description, NEVER a fetch receipt."""

    target: str
    mst: str
    efyd: str | None = None

    def __post_init__(self) -> None:
        _validate(self.target, self.mst, self.efyd)

    def public_parameters(self) -> dict[str, str]:
        """A new dict each time, safe for logging as a PUBLIC description."""
        values = {"target": self.target, "type": "JSON", "MST": self.mst}
        if self.efyd is not None:
            values["efYd"] = self.efyd
        return values

    def public_descriptor_url(self) -> str:
        """Credential-free locator; NOT the actual authenticated request URL."""
        return ENDPOINT + "?" + urlencode(self.public_parameters())

    def to_dict(self) -> dict[str, str | bool]:
        """Return only fixed, validated fields; no origin/admission decision."""
        result: dict[str, str | bool] = {
            "schema_version": SCHEMA_VERSION,
            "source_system": SOURCE_SYSTEM,
            "endpoint": ENDPOINT,
            **self.public_parameters(),
            "record_kind": RECORD_KIND,
            "credential_included": False,
        }
        return result


def build_legal_source_public_request_descriptor(
    criteria: dict[str, object],
) -> LegalSourcePublicRequestDescriptor:
    """Build from exact allowlisted fields; never accept a raw URL or secrets.

    All validation errors use fixed codes rather than reflecting sensitive
    unexpected keys/values. The input is not stored on the returned object.
    """
    if type(criteria) is not dict:
        raise ValueError("INVALID_CRITERIA_TYPE")
    if any(type(key) is not str for key in criteria):
        raise ValueError("INVALID_FIELD_NAME")
    target = criteria.get("target")
    if type(target) is not str or target not in _FIELDS:
        raise ValueError("INVALID_TARGET")
    if set(criteria) != _FIELDS[target]:
        raise ValueError("INVALID_FIELD_SET")
    if type(criteria["type"]) is not str or criteria["type"] != "JSON":
        raise ValueError("INVALID_FORMAT")
    return LegalSourcePublicRequestDescriptor(
        target=target,
        mst=criteria["MST"],
        efyd=criteria.get("efYd"),
    )
