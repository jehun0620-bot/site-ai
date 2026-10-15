# -*- coding: utf-8 -*-
"""Offline EFLAW list/detail SAME-PROVIDER, response-local correspondence BARRIER.

The only list JSON row path inspected is LawSearch/law, observed in ONE
2026-10-15 user's local live audit. This is an observation, not a certified
provider schema, fetch receipt, independent provenance or legal version ID.
An exact trio of raw strings is stronger than converted-string equality,
but NEITHER form establishes a canonical law version or law in force.

Inputs are in-memory response bytes and a PUBLIC EFLAW request descriptor.
No file/network I/O, date candidates, source registry updates, Rule Engine,
production admission, IDs returned, URLs, headers or credentials.
Only public_record() can be logged; never serialize original payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
import re

from law_data.legal_source_public_request_descriptor import LegalSourcePublicRequestDescriptor
from law_data.legal_source_eflaw_temporal_response_field_extraction import _read_response
from law_data.legal_source_eflaw_temporal_prebinding_requirements import (
    inspect_legal_source_eflaw_temporal_prebinding_requirements,
)

NOT_EVALUATED = "NOT_EVALUATED"
PATH_UNRESOLVED = "EFLAW_LIST_DETAIL_LOCAL_ROW_PATH_UNRESOLVED"
NO_MATCH = "EFLAW_LIST_DETAIL_LOCAL_NO_TRIPLE_MATCH_UNRESOLVED"
NORMALIZED_ONLY = "EFLAW_LIST_DETAIL_LOCAL_NORMALIZED_ONLY_MATCH_UNATTESTED"
EXACT_ONE = "EFLAW_LIST_DETAIL_LOCAL_EXACT_STRING_TRIPLE_MATCH_UNATTESTED"
MULTIPLE = "EFLAW_LIST_DETAIL_LOCAL_MULTIPLE_TRIPLE_MATCHES_UNRESOLVED"
_PATH_OBJECT = "OBSERVED_OBJECT_UNATTESTED"
_PATH_ARRAY = "OBSERVED_ARRAY_UNATTESTED"
_PATH_MISSING = "NOT_OBSERVED"
_PATH_UNSUPPORTED = "UNSUPPORTED_MEMBER_SHAPE"
_ALLOWED = frozenset((PATH_UNRESOLVED, NO_MATCH, NORMALIZED_ONLY, EXACT_ONE, MULTIPLE))
_MISSING = object()
_SEAL = object()
_DIGITS = re.compile(r"[0-9]{1,20}\Z")
_DATE = re.compile(r"[0-9]{8}\Z")
_LIST_MAX_BYTES = 4_000_000  # Only after bytes were received, NOT transfer bound.
_MAX_ROWS = 1000
_FIELDS = ("법령ID", "법령일련번호", "시행일자")


def _calendar(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return False
    return True


def _normal_text(value: object) -> str | None:
    """For a separate DIAGNOSTIC only; never use it to promote identity."""
    if type(value) is str:
        return value.strip() or None
    if type(value) is int and value >= 0:
        return str(value)
    if type(value) is dict and len(value) == 1:
        if "content" in value:
            return _normal_text(value["content"])
        if "#text" in value:
            return _normal_text(value["#text"])
    return None


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("CORRESPONDENCE_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("CORRESPONDENCE_NONSTANDARD_JSON_CONSTANT")


def _list_rows(payload: bytes) -> tuple[str, list[dict[str, object]]]:
    if type(payload) is not bytes or not 0 < len(payload) <= _LIST_MAX_BYTES:
        raise ValueError("CORRESPONDENCE_LIST_BYTE_BOUNDS_UNRESOLVED")
    try:
        root = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("CORRESPONDENCE_LIST_JSON_UNRESOLVED") from None
    if type(root) is not dict:
        raise ValueError("CORRESPONDENCE_LIST_ROOT_UNRESOLVED")
    section = root.get("LawSearch", _MISSING)
    if section is _MISSING:
        return _PATH_MISSING, []
    if type(section) is not dict:
        return _PATH_UNSUPPORTED, []
    member = section.get("law", _MISSING)
    if member is _MISSING:
        return _PATH_MISSING, []
    if type(member) is dict:
        return _PATH_OBJECT, [member]
    if type(member) is list and all(type(row) is dict for row in member):
        if len(member) > _MAX_ROWS:
            raise ValueError("CORRESPONDENCE_LIST_ROW_BOUNDS_UNRESOLVED")
        return _PATH_ARRAY, member
    return _PATH_UNSUPPORTED, []


@dataclass(frozen=True, slots=True)
class LegalSourceEflawListDetailLocalCorrespondenceInspection:
    """Private origin-free aggregate; never an identity or admission certificate."""

    status: str
    path_state: str
    rows_examined: int
    triple_fields_present: int
    triple_rows_all_plain_string: int
    triple_rows_any_integer: int
    triple_rows_any_whitespace: int
    triple_rows_unsupported_normalized_text: int
    normalized_triple_matches: int
    exact_unmodified_string_matches: int
    normalized_only_matches: int
    selector_vs_detail_day: str
    prebinding_status: str
    article_collision_groups: int
    article_collision_member_units: int
    annex_collision_groups: int
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("CORRESPONDENCE_DIRECT_RESULT_FORBIDDEN")
        if self.status not in _ALLOWED:
            raise ValueError("CORRESPONDENCE_INVALID_STATUS")
        if self.path_state not in (_PATH_OBJECT, _PATH_ARRAY, _PATH_MISSING, _PATH_UNSUPPORTED):
            raise ValueError("CORRESPONDENCE_INVALID_PATH_STATE")
        if self.selector_vs_detail_day not in ("SAME_RAW_DAY", "DIFFERENT_RAW_DAY"):
            raise ValueError("CORRESPONDENCE_INVALID_SELECTOR_RELATION")
        fields = (self.rows_examined, self.triple_fields_present,
                  self.triple_rows_all_plain_string, self.triple_rows_any_integer,
                  self.triple_rows_any_whitespace,
                  self.triple_rows_unsupported_normalized_text,
                  self.normalized_triple_matches, self.exact_unmodified_string_matches,
                  self.normalized_only_matches, self.article_collision_groups,
                  self.article_collision_member_units, self.annex_collision_groups)
        if any(type(v) is not int or v < 0 for v in fields):
            raise ValueError("CORRESPONDENCE_INVALID_COUNTS")
        if (self.triple_fields_present > self.rows_examined
            or any(v > self.triple_fields_present for v in (
                self.triple_rows_all_plain_string, self.triple_rows_any_integer,
                self.triple_rows_any_whitespace,
                self.triple_rows_unsupported_normalized_text,
                self.normalized_triple_matches, self.exact_unmodified_string_matches,
            ))
            or self.normalized_only_matches != (
                self.normalized_triple_matches - self.exact_unmodified_string_matches
            ) or self.normalized_only_matches < 0
            or self.article_collision_groups * 2 > self.article_collision_member_units):
            raise ValueError("CORRESPONDENCE_INCONSISTENT_COUNTS")
        if self.path_state in (_PATH_MISSING, _PATH_UNSUPPORTED) and self.rows_examined != 0:
            raise ValueError("CORRESPONDENCE_INCONSISTENT_PATH")
        expected = (
            PATH_UNRESOLVED if self.path_state in (_PATH_MISSING, _PATH_UNSUPPORTED)
            else MULTIPLE if self.normalized_triple_matches > 1
            else EXACT_ONE if self.exact_unmodified_string_matches == 1
            else NORMALIZED_ONLY if self.normalized_triple_matches == 1
            else NO_MATCH
        )
        if self.status != expected:
            raise ValueError("CORRESPONDENCE_INCONSISTENT_STATUS")
        if self.prebinding_status not in (
            "EFLAW_TEMPORAL_PREBINDING_BLOCKED_RESPONSE_LOCAL_COLLISIONS",
            "EFLAW_TEMPORAL_PREBINDING_BLOCKED_STRUCTURE_OR_DATE_SHAPE",
            "EFLAW_TEMPORAL_PREBINDING_BLOCKED_UNATTESTED_IDENTITIES",
        ):
            raise ValueError("CORRESPONDENCE_INVALID_PREBINDING_STATUS")

    def public_record(self) -> dict[str, str | int | bool]:
        return {
            "record_kind": "EFLAW_LIST_DETAIL_RESPONSE_LOCAL_CORRESPONDENCE_V1",
            "status": self.status,
            "row_path_state": self.path_state,
            "row_path_basis": "LAWSEARCH_LAW_ONE_RESPONSE_HYPOTHESIS_UNATTESTED",
            "rows_examined": self.rows_examined,
            "triple_fields_present": self.triple_fields_present,
            "triple_rows_all_plain_string": self.triple_rows_all_plain_string,
            "triple_rows_any_integer": self.triple_rows_any_integer,
            "triple_rows_any_whitespace": self.triple_rows_any_whitespace,
            "triple_rows_unsupported_normalized_text": self.triple_rows_unsupported_normalized_text,
            "normalized_triple_matches": self.normalized_triple_matches,
            "exact_unmodified_string_matches": self.exact_unmodified_string_matches,
            "normalized_only_matches": self.normalized_only_matches,
            "selector_vs_detail_day": self.selector_vs_detail_day,
            "prebinding_status": self.prebinding_status,
            "article_collision_groups": self.article_collision_groups,
            "article_collision_member_units": self.article_collision_member_units,
            "annex_collision_groups": self.annex_collision_groups,
            "exact_match_confirms_canonical_version": False,
            "no_match_proves_legal_absence": False,
            "list_filter_enforcement": NOT_EVALUATED,
            "list_page_completeness": NOT_EVALUATED,
            "cross_endpoint_provider_independence": False,
            "official_origin_attestation": NOT_EVALUATED,
            "canonical_law_version_identity": NOT_EVALUATED,
            "current_legal_validity": NOT_EVALUATED,
            "article_and_annex_legal_effect": NOT_EVALUATED,
            "parcel_applicability": NOT_EVALUATED,
            "candidate_creation": "NOT_PERFORMED",
            "date_candidate_join": "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY",
            "collision_merging": "FORBIDDEN",
            "array_index_identifier_promotion": "FORBIDDEN",
            "rule_engine_admission": "FORBIDDEN",
            "production_admission": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_list_detail_local_correspondence(
    detail_payload: bytes,
    list_payload: bytes,
    descriptor: LegalSourcePublicRequestDescriptor,
) -> LegalSourceEflawListDetailLocalCorrespondenceInspection:
    """Read-only inspect existing private bytes; NEVER fetch or declare provenance."""
    if type(descriptor) is not LegalSourcePublicRequestDescriptor or descriptor.target != "eflaw":
        raise ValueError("CORRESPONDENCE_INVALID_DESCRIPTOR")
    prebinding = inspect_legal_source_eflaw_temporal_prebinding_requirements(detail_payload)
    law = _read_response(detail_payload)
    basic = law.get("기본정보")
    if type(basic) is not dict:
        raise ValueError("CORRESPONDENCE_DETAIL_BASIC_UNRESOLVED")
    lid, day, title = (basic.get("법령ID"), basic.get("시행일자"), basic.get("법령명_한글"))
    if (type(lid) is not str or not _DIGITS.fullmatch(lid)
        or type(day) is not str or not _calendar(day)
        or type(title) is not str or not title.strip()):
        raise ValueError("CORRESPONDENCE_DETAIL_IDENTITY_SHAPE_UNRESOLVED")
    path, rows = _list_rows(list_payload)
    fields_present = plain = ints = whitespaces = unsupported = normal = exact = 0
    for row in rows:
        if not all(k in row for k in _FIELDS):
            continue
        fields_present += 1
        raw = tuple(row[k] for k in _FIELDS)
        if all(type(v) is str for v in raw):
            plain += 1
        if any(type(v) is int for v in raw):
            ints += 1
        if any(type(v) is str and v != v.strip() for v in raw):
            whitespaces += 1
        normal_values = tuple(_normal_text(v) for v in raw)
        if any(v is None for v in normal_values):
            unsupported += 1
        if normal_values == (lid, descriptor.mst, day):
            normal += 1
        if (all(type(v) is str for v in raw)
            and raw == (lid, descriptor.mst, day)):
            exact += 1
    status = (PATH_UNRESOLVED if path in (_PATH_MISSING, _PATH_UNSUPPORTED)
              else MULTIPLE if normal > 1
              else EXACT_ONE if exact == 1
              else NORMALIZED_ONLY if normal == 1
              else NO_MATCH)
    return LegalSourceEflawListDetailLocalCorrespondenceInspection(
        status, path, len(rows), fields_present, plain, ints, whitespaces,
        unsupported, normal, exact, normal - exact,
        "SAME_RAW_DAY" if day == descriptor.efyd else "DIFFERENT_RAW_DAY",
        prebinding.status, prebinding.article_collision_groups,
        prebinding.article_collision_member_units, prebinding.annex_collision_groups,
        _seal=_SEAL,
    )
