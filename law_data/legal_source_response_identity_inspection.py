# -*- coding: utf-8 -*-
"""Offline, fail-closed identity checks of an acquired MOLEG JSON response.

The only supported shapes are the fields used by the existing normalization
code for national ``eflaw`` and local ``ordin`` detail responses.  A match is
NOT an official-origin attestation, a law-in-force decision, or SITE admission.
National ``eflaw`` has NO independently established response MST field;
therefore a matched national identity is explicitly LIMITED.

This module never fetches URLs, reads files, constructs receipts, or parses
untrusted response text into any public error or logged field.  Input bytes
remain private inside the HTTP outcome.  Serialize ONLY public_record().
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from law_data.legal_source_http_integrity_bridge import (
    LegalSourceHttpIntegrityBridgeResult,
    inspect_legal_source_http_integrity_bridge,
)
from law_data.legal_source_http_safety_boundary import LegalSourceHttpFetchOutcome
from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference

UPSTREAM_UNRESOLVED = "UPSTREAM_INTEGRITY_UNRESOLVED"
JSON_INVALID = "RESPONSE_JSON_INVALID"
SHAPE_UNKNOWN = "RESPONSE_SHAPE_UNKNOWN"
FIELDS_MISSING = "RESPONSE_IDENTITY_FIELDS_MISSING"
FIELDS_MISMATCH = "RESPONSE_IDENTITY_FIELDS_MISMATCH"
NATIONAL_LIMITED = "RESPONSE_IDENTITY_ALIGNED_LIMITED_UNVERIFIED_ORIGIN"
ORDIN_ALIGNED = "RESPONSE_IDENTITY_ALIGNED_UNVERIFIED_ORIGIN"
NOT_EVALUATED = "NOT_EVALUATED"

_MAX_RESPONSE_BYTES = 10_000_000  # Bounded JSON inspection, not a size-based legal rule.
_KNOWN_STATUSES = frozenset((
    UPSTREAM_UNRESOLVED, JSON_INVALID, SHAPE_UNKNOWN, FIELDS_MISSING,
    FIELDS_MISMATCH, NATIONAL_LIMITED, ORDIN_ALIGNED,
))
_FIELD_STATES = frozenset(("MATCH", "MISSING", "MISMATCH", "NOT_EVALUATED"))
_MST_STATES = frozenset((
    "MATCH", "MISSING", "MISMATCH", "NOT_EVALUATED",
    "NOT_PRESENT_IN_CONFIRMED_NATIONAL_SCHEMA",
))


@dataclass(frozen=True, slots=True)
class LegalSourceResponseIdentityInspection:
    """PRIVATE wrapper with allowlisted safe diagnostics; never serialize wholesale."""

    status: str
    bridge: LegalSourceHttpIntegrityBridgeResult = field(repr=False, compare=False)
    source_id_check: str = "NOT_EVALUATED"
    name_check: str = "NOT_EVALUATED"
    effective_date_check: str = "NOT_EVALUATED"
    response_mst_check: str = "NOT_EVALUATED"

    def __post_init__(self) -> None:
        if type(self.bridge) is not LegalSourceHttpIntegrityBridgeResult:
            raise ValueError("INVALID_BRIDGE_RESULT")
        if type(self.status) is not str or self.status not in _KNOWN_STATUSES:
            raise ValueError("INVALID_IDENTITY_STATUS")
        for value in (self.source_id_check, self.name_check, self.effective_date_check):
            if type(value) is not str or value not in _FIELD_STATES:
                raise ValueError("INVALID_IDENTITY_FIELD_STATUS")
        if type(self.response_mst_check) is not str or self.response_mst_check not in _MST_STATES:
            raise ValueError("INVALID_RESPONSE_MST_STATUS")

    def public_record(self) -> dict[str, object]:
        """No raw metadata, response body, source title, URL or exception."""
        return {
            "record_kind": "LEGAL_RESPONSE_IDENTITY_PUBLIC_DIAGNOSTIC_V1",
            "status": self.status,
            "source_id_check": self.source_id_check,
            "name_check": self.name_check,
            "effective_date_check": self.effective_date_check,
            "response_mst_check": self.response_mst_check,
            "upstream": self.bridge.public_record(),
            "response_identity_basis": "CALLER_SUPPLIED_JSON_FIELDS_UNVERIFIED_ORIGIN",
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys rather than silently taking last-wins values."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


def _text(value: object) -> str | None:
    """Only explicit text and the content wrappers used in existing code."""
    if type(value) is str:
        stripped = value.strip()
        return stripped or None
    if type(value) is dict and len(value) == 1:
        if "content" in value:
            return _text(value["content"])
        if "#text" in value:
            return _text(value["#text"])
    return None


def _date(value: object) -> str | None:
    raw = _text(value)
    if raw is None:
        return None
    try:
        if len(raw) == 8 and raw.isascii() and raw.isdecimal():
            parsed = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        elif len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            parsed = date.fromisoformat(raw)
        else:
            return None
    except ValueError:
        return None
    return parsed.isoformat()


def _compare(actual: str | None, expected: str | None) -> str:
    if actual is None or expected is None:
        return "MISSING"
    return "MATCH" if actual == expected else "MISMATCH"


def inspect_legal_source_response_identity(
    http_outcome: LegalSourceHttpFetchOutcome,
    record: LegalSourceRecord,
    reference: LegalSourceVersionEvidenceReference,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceResponseIdentityInspection:
    """Recompute upstream binding and digest, then compare bounded JSON fields.

    National law: root 법령 / 기본정보 / 법령ID / 법령명_한글 / 시행일자.
    Local ordinance: LawService / 자치법규기본정보 / 자치법규ID /
        자치법규명 / 시행일자 / 자치법규일련번호.
    Expected ID, name and effective date are ALL caller-provided descriptors.
    The request's efYd is NOT assumed equal to the content effective date.
    """
    # Existing bridge revalidates the request MST, declared scope, identity,
    # and SHA256 using actual supplied bytes. A forged caller success flag
    # cannot bypass this recomputation.
    bridge = inspect_legal_source_http_integrity_bridge(
        http_outcome, record, reference, known_references=known_references,
    )

    def result(status: str, *, source_id: str = "NOT_EVALUATED",
               name: str = "NOT_EVALUATED", effective_date: str = "NOT_EVALUATED",
               mst: str = "NOT_EVALUATED") -> LegalSourceResponseIdentityInspection:
        return LegalSourceResponseIdentityInspection(
            status, bridge, source_id, name, effective_date, mst,
        )

    if bridge.status != "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN":
        return result(UPSTREAM_UNRESOLVED)
    payload = http_outcome.payload
    if type(payload) is not bytes or not 0 < len(payload) <= _MAX_RESPONSE_BYTES:
        return result(JSON_INVALID)
    try:
        data = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return result(JSON_INVALID)
    if type(data) is not dict:
        return result(SHAPE_UNKNOWN)

    target = http_outcome.descriptor.target
    if target == "eflaw":
        root = data.get("법령")
        basic = root.get("기본정보") if type(root) is dict else None
        id_key, name_key, mst_key = "법령ID", "법령명_한글", None
    elif target == "ordin":
        root = data.get("LawService")
        basic = root.get("자치법규기본정보") if type(root) is dict else None
        id_key, name_key, mst_key = "자치법규ID", "자치법규명", "자치법규일련번호"
    else:
        return result(SHAPE_UNKNOWN)
    if type(basic) is not dict:
        return result(SHAPE_UNKNOWN)

    source_id = _compare(_text(basic.get(id_key)), record.source_id)
    name = _compare(_text(basic.get(name_key)), record.title)
    effective = _compare(_date(basic.get("시행일자")), record.effective_date)
    mst = (
        "NOT_PRESENT_IN_CONFIRMED_NATIONAL_SCHEMA" if mst_key is None
        else _compare(_text(basic.get(mst_key)), http_outcome.descriptor.mst)
    )
    if "MISMATCH" in (source_id, name, effective, mst):
        state = FIELDS_MISMATCH
    elif "MISSING" in (source_id, name, effective, mst):
        state = FIELDS_MISSING
    elif target == "eflaw":
        state = NATIONAL_LIMITED
    else:
        state = ORDIN_ALIGNED
    return result(state, source_id=source_id, name=name, effective_date=effective, mst=mst)
