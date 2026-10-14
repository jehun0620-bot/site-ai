# -*- coding: utf-8 -*-
"""External official API guide REFERENCE boundary for eflaw MST+efYd.

The documentary facts in this module were transcribed from the public MOLEG
Open API '현행법령(시행일) 본문 조회 API' guide reviewed 2026-10-14. This module
DOES NOT download, authenticate, pin the bytes of, or continuously recheck
that guide. A matching URL is not proof of an authoritative HTTP response.

Guide scope: target=eflaw; OC required; MST identifies lsi_seq; efYd selects
an effective-date request; type=JSON supported. ID-mode ignores efYd and is
not the MST+efYd request variant implemented in this project. The guide lists
response fields for law ID, Korean title, effective date and promulgation
metadata, but does not independently establish a NATIONAL response MST field.

Only documentary request-shape compatibility can be reported here. This is
NEVER current-law, official-origin, acquisition, effective-law, authoritative
source, parcel applicability or Production permission.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from law_data.legal_source_public_request_descriptor import (
    ENDPOINT,
    LegalSourcePublicRequestDescriptor,
)

NOT_EVALUATED = "NOT_EVALUATED"
GUIDE_URI = "https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=lsEfYdInfoGuide"
GUIDE_REVIEW_DATE = "2026-10-14"  # Manual review date; NOT a witnessed immutable capture.
GUIDE_REQUEST_PATH = "/DRF/lawService.do"
GUIDE_REQUEST_MODE = "MST_EFYD_JSON"

ALIGNED = "EFLAW_API_GUIDE_REQUEST_SHAPE_ALIGNED_REFERENCE_ONLY"
REFERENCE_MISSING = "EFLAW_API_GUIDE_REFERENCE_MISSING"
REFERENCE_MISMATCH = "EFLAW_API_GUIDE_REFERENCE_MISMATCH"
REQUEST_OUT_OF_SCOPE = "EFLAW_API_GUIDE_REQUEST_OUT_OF_SCOPE"
REQUEST_SHAPE_MISMATCH = "EFLAW_API_GUIDE_REQUEST_SHAPE_MISMATCH"

_STATUSES = frozenset((
    ALIGNED, REFERENCE_MISSING, REFERENCE_MISMATCH,
    REQUEST_OUT_OF_SCOPE, REQUEST_SHAPE_MISMATCH,
))
_SEAL = object()


@dataclass(frozen=True, slots=True)
class LegalSourceEflawOfficialGuideReference:
    """Caller-supplied documentary URL assertion, not a verified capture.

    Do NOT submit a raw authenticated API request URL to this model.
    The URL is never echoed in public diagnostics or exceptions.
    """

    guide_uri: str | None

    def __post_init__(self) -> None:
        if self.guide_uri is not None:
            if type(self.guide_uri) is not str or len(self.guide_uri) > 512:
                raise ValueError("INVALID_GUIDE_REFERENCE")
            if any(ord(ch) < 32 or ord(ch) == 127 for ch in self.guide_uri):
                raise ValueError("UNSAFE_GUIDE_REFERENCE")
            if re.search(r"(?:[?&]|^)oc=", self.guide_uri, re.IGNORECASE):
                raise ValueError("UNSAFE_GUIDE_REFERENCE")


@dataclass(frozen=True, slots=True)
class LegalSourceEflawOfficialGuideEvidenceInspection:
    """Limited safe diagnostic. Constructor success cannot be self-minted."""

    status: str
    guide_reference_check: str
    requested_mode_check: str
    guide_request_fields_check: str
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in _STATUSES:
            raise ValueError("INVALID_GUIDE_EVIDENCE_STATUS")
        for name in (
            "guide_reference_check", "requested_mode_check",
            "guide_request_fields_check",
        ):
            if type(getattr(self, name)) is not str or getattr(self, name) not in (
                "MATCH", "MISMATCH", "MISSING", "UNSUPPORTED", NOT_EVALUATED,
            ):
                raise ValueError("INVALID_GUIDE_EVIDENCE_CHECK")
        if self.status == ALIGNED and (
            self.guide_reference_check != "MATCH"
            or self.requested_mode_check != "MATCH"
            or self.guide_request_fields_check != "MATCH"
        ):
            raise ValueError("INCONSISTENT_GUIDE_EVIDENCE_SUCCESS")
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_GUIDE_EVIDENCE_RESULT_FORBIDDEN")

    def public_record(self) -> dict[str, str]:
        """No original URLs, identifiers, source bytes, credentials or dates."""
        return {
            "record_kind": "LEGAL_EFLAW_OFFICIAL_API_GUIDE_SCOPE_V1",
            "status": self.status,
            "guide_reference_check": self.guide_reference_check,
            "requested_mode_check": self.requested_mode_check,
            "guide_request_fields_check": self.guide_request_fields_check,
            "documentation_scope": "EFLAW_MST_EFYD_JSON_REQUEST_ONLY",
            "guide_reference_basis": "CALLER_SUPPLIED_URL_VS_MANUALLY_REVIEWED_OFFICIAL_GUIDE",
            "guide_capture_authenticity": NOT_EVALUATED,
            "guide_currentness": NOT_EVALUATED,
            "guide_transport_https_provenance": NOT_EVALUATED,
            "national_response_mst_field_verified": NOT_EVALUATED,
            "actual_authenticated_request_observed": NOT_EVALUATED,
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_official_guide_evidence(
    descriptor: LegalSourcePublicRequestDescriptor,
    reference: LegalSourceEflawOfficialGuideReference,
) -> LegalSourceEflawOfficialGuideEvidenceInspection:
    """Reconcile one public MST+efYd descriptor with a documented guide mode.

    This is OFFLINE, and does NOT verify that reference.guide_uri was fetched
    or that an official-looking guide URL is evidence of source authenticity.
    """
    if type(descriptor) is not LegalSourcePublicRequestDescriptor:
        raise TypeError("INVALID_PUBLIC_DESCRIPTOR")
    if type(reference) is not LegalSourceEflawOfficialGuideReference:
        raise TypeError("INVALID_GUIDE_REFERENCE")

    def outcome(status: str, guide: str = NOT_EVALUATED,
                mode: str = NOT_EVALUATED,
                fields: str = NOT_EVALUATED) -> LegalSourceEflawOfficialGuideEvidenceInspection:
        return LegalSourceEflawOfficialGuideEvidenceInspection(
            status, guide, mode, fields, _seal=_SEAL,
        )

    if reference.guide_uri is None or not reference.guide_uri:
        return outcome(REFERENCE_MISSING, "MISSING")
    if reference.guide_uri != GUIDE_URI:
        return outcome(REFERENCE_MISMATCH, "MISMATCH")
    if descriptor.target != "eflaw" or descriptor.efyd is None:
        return outcome(REQUEST_OUT_OF_SCOPE, "MATCH", "UNSUPPORTED")
    # Validate what is in the public descriptor; the authenticated wire URL
    # with OC is deliberately inaccessible and never checked here.
    expected = {
        "target": "eflaw", "type": "JSON",
        "MST": descriptor.mst, "efYd": descriptor.efyd,
    }
    if (descriptor.public_parameters() != expected
            or ENDPOINT != "https://www.law.go.kr" + GUIDE_REQUEST_PATH):
        return outcome(REQUEST_SHAPE_MISMATCH, "MATCH", "MATCH", "MISMATCH")
    return outcome(ALIGNED, "MATCH", "MATCH", "MATCH")
