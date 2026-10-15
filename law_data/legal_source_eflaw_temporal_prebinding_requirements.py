# -*- coding: utf-8 -*-
"""Read-only prerequisites boundary BEFORE any EFLAW temporal evidence binding.

Only the response-local paths observed in ONE historical eflaw JSON response
are inspected. A syntactically valid date, unique local pair/triple, or a
matched local digest cannot establish official source origin, canonical item
identity, article/annex legal effect, or parcel applicability.

Every outcome blocks candidate creation, date joining, Rule Engine use and
Production. This does NOT authorize a later approval path; one must be built
from independently verified provenance, legal identity and applicability.
Return ONLY public_record(); never serialize raw input or private results.
No HTTP, file writes, registration, or mutable global state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re

from law_data.legal_source_eflaw_temporal_response_field_extraction import (
    OBSERVED, _read_response, extract_legal_source_eflaw_temporal_response_fields,
)
from law_data.legal_source_eflaw_article_item_ambiguity_guard import (
    inspect_legal_source_eflaw_article_item_ambiguity,
)
from law_data.legal_source_eflaw_annex_item_ambiguity_guard import (
    inspect_legal_source_eflaw_annex_item_ambiguity,
)

NOT_EVALUATED = "NOT_EVALUATED"
COLLISION_BLOCKED = "EFLAW_TEMPORAL_PREBINDING_BLOCKED_RESPONSE_LOCAL_COLLISIONS"
STRUCTURE_BLOCKED = "EFLAW_TEMPORAL_PREBINDING_BLOCKED_STRUCTURE_OR_DATE_SHAPE"
UNATTESTED_BLOCKED = "EFLAW_TEMPORAL_PREBINDING_BLOCKED_UNATTESTED_IDENTITIES"
_SEAL = object()
_DATE = re.compile(r"[0-9]{8}\Z")


def _calendar_shape(value: str) -> bool:
    """Calendar syntax check only; not an effective-law determination."""
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class LegalSourceEflawTemporalPrebindingRequirementsInspection:
    """Sealed, counts-only and always non-admissible observation."""

    status: str
    law_date_fields: int
    article_units_examined: int
    article_date_fields: int
    annex_units_examined: int
    annex_date_fields: int
    supplementary_array_count: int
    date_literals_calendar_shape_valid: int
    date_literals_calendar_shape_invalid: int
    article_collision_groups: int
    article_collision_member_units: int
    article_ineligible_units: int
    annex_collision_groups: int
    annex_collision_member_units: int
    annex_ineligible_units: int
    _extraction_complete_observed: bool = field(repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_PREBINDING_INSPECTION_FORBIDDEN")
        if self.status not in (COLLISION_BLOCKED, STRUCTURE_BLOCKED, UNATTESTED_BLOCKED):
            raise ValueError("INVALID_PREBINDING_STATUS")
        values = (
            self.law_date_fields, self.article_units_examined, self.article_date_fields,
            self.annex_units_examined, self.annex_date_fields,
            self.supplementary_array_count, self.date_literals_calendar_shape_valid,
            self.date_literals_calendar_shape_invalid, self.article_collision_groups,
            self.article_collision_member_units, self.article_ineligible_units,
            self.annex_collision_groups, self.annex_collision_member_units,
            self.annex_ineligible_units,
        )
        if any(type(n) is not int or n < 0 for n in values):
            raise ValueError("INVALID_PREBINDING_COUNTS")
        if type(self._extraction_complete_observed) is not bool:
            raise ValueError("INVALID_PREBINDING_EXTRACTION_FLAG")
        if self.law_date_fields > 1 or self.article_date_fields > self.article_units_examined or (
            self.annex_date_fields > self.annex_units_examined
        ):
            raise ValueError("INCONSISTENT_PREBINDING_FIELD_COUNTS")
        if self.date_literals_calendar_shape_valid + self.date_literals_calendar_shape_invalid != (
            self.law_date_fields + self.article_date_fields + self.annex_date_fields
        ):
            raise ValueError("INCONSISTENT_PREBINDING_DATE_COUNTS")
        if (self.article_collision_member_units > self.article_units_examined
                or self.annex_collision_member_units > self.annex_units_examined
                or self.article_collision_groups * 2 > self.article_collision_member_units
                or self.annex_collision_groups * 2 > self.annex_collision_member_units
                or self.article_ineligible_units > self.article_units_examined
                or self.annex_ineligible_units > self.annex_units_examined):
            raise ValueError("INCONSISTENT_PREBINDING_IDENTIFIER_COUNTS")
        collisions = bool(self.article_collision_groups or self.annex_collision_groups)
        structural = (
            not self._extraction_complete_observed
            or self.law_date_fields != 1
            or self.article_date_fields != self.article_units_examined
            or self.annex_date_fields != self.annex_units_examined
            or self.date_literals_calendar_shape_invalid > 0
            or self.article_ineligible_units > 0 or self.annex_ineligible_units > 0
        )
        expected = (COLLISION_BLOCKED if collisions else
                    STRUCTURE_BLOCKED if structural else UNATTESTED_BLOCKED)
        if expected != self.status:
            raise ValueError("INCONSISTENT_PREBINDING_STATUS")

    def public_record(self) -> dict[str, str | int | bool]:
        """Explicit non-sensitive allowlist; no dates, IDs, bodies, URLs or keys."""
        return {
            "record_kind": "EFLAW_TEMPORAL_PREBINDING_REQUIREMENTS_V1",
            "status": self.status,
            "law_date_fields": self.law_date_fields,
            "article_units_examined": self.article_units_examined,
            "article_date_fields": self.article_date_fields,
            "annex_units_examined": self.annex_units_examined,
            "annex_date_fields": self.annex_date_fields,
            "supplementary_array_count": self.supplementary_array_count,
            "date_literals_calendar_shape_valid": self.date_literals_calendar_shape_valid,
            "date_literals_calendar_shape_invalid": self.date_literals_calendar_shape_invalid,
            "article_collision_groups": self.article_collision_groups,
            "article_collision_member_units": self.article_collision_member_units,
            "article_ineligible_units": self.article_ineligible_units,
            "annex_collision_groups": self.annex_collision_groups,
            "annex_collision_member_units": self.annex_collision_member_units,
            "annex_ineligible_units": self.annex_ineligible_units,
            "date_shape_is_legal_effect": False,
            "local_identifier_uniqueness_is_canonical": False,
            "response_array_position_is_identifier": False,
            "source_origin_attestation": NOT_EVALUATED,
            "response_law_version_identity": NOT_EVALUATED,
            "canonical_article_identity": NOT_EVALUATED,
            "canonical_annex_identity": NOT_EVALUATED,
            "supplementary_and_amendment_effect": NOT_EVALUATED,
            "article_and_annex_legal_effect": NOT_EVALUATED,
            "parcel_applicability": NOT_EVALUATED,
            "current_legal_validity": NOT_EVALUATED,
            "candidate_creation": "NOT_PERFORMED",
            "article_candidate_join": "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY",
            "annex_candidate_join": "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY",
            "collision_merging": "FORBIDDEN",
            "array_index_identifier_promotion": "FORBIDDEN",
            "rule_engine_admission": "FORBIDDEN",
            "production_admission": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_temporal_prebinding_requirements(
    payload: bytes,
) -> LegalSourceEflawTemporalPrebindingRequirementsInspection:
    """Inspect the SAME response bytes; never create a candidate or ID."""
    extraction = extract_legal_source_eflaw_temporal_response_fields(payload)
    article = inspect_legal_source_eflaw_article_item_ambiguity(payload)
    annex = inspect_legal_source_eflaw_annex_item_ambiguity(payload)
    if (
        extraction.article_units_examined != article.article_units_examined
        or extraction.article_count != article.article_date_fields
        or extraction.annex_units_examined != annex.annex_units_examined
        or extraction.annex_count != annex.annex_date_fields
    ):
        raise ValueError("PREBINDING_UPSTREAM_COUNT_MISMATCH")
    law = _read_response(payload)
    counted = 0
    valid = 0
    specs = (
        ("기본정보", None, "시행일자"),
        ("조문", "조문단위", "조문시행일자"),
        ("별표", "별표단위", "별표시행일자"),
    )
    for container, group, key in specs:
        section = law.get(container)
        if section is None:
            continue
        if type(section) is not dict:
            raise ValueError("PREBINDING_DATE_CONTAINER_UNRESOLVED")
        units = (section,) if group is None else section.get(group, [])
        if type(units) not in (tuple, list):
            raise ValueError("PREBINDING_DATE_UNITS_UNRESOLVED")
        for item in units:
            if type(item) is not dict:
                raise ValueError("PREBINDING_DATE_UNIT_UNRESOLVED")
            if key not in item:
                continue
            literal = item[key]
            if type(literal) is not str:
                raise ValueError("PREBINDING_DATE_LITERAL_TYPE_UNRESOLVED")
            counted += 1
            valid += int(_calendar_shape(literal))
    if counted != extraction.law_count + extraction.article_count + extraction.annex_count:
        raise ValueError("PREBINDING_DATE_SCAN_COUNT_MISMATCH")
    collisions = bool(article.triple_collision_groups or annex.collision_groups)
    structural = (
        extraction.status != OBSERVED or extraction.law_count != 1
        or article.article_date_fields != article.article_units_examined
        or annex.annex_date_fields != annex.annex_units_examined
        or valid != counted or article.triple_ineligible_units > 0
        or annex.ineligible_units > 0
    )
    status = (COLLISION_BLOCKED if collisions else
              STRUCTURE_BLOCKED if structural else UNATTESTED_BLOCKED)
    return LegalSourceEflawTemporalPrebindingRequirementsInspection(
        status, extraction.law_count, article.article_units_examined,
        article.article_date_fields, annex.annex_units_examined,
        annex.annex_date_fields, extraction.supplementary_count,
        valid, counted - valid, article.triple_collision_groups,
        article.triple_collision_member_units, article.triple_ineligible_units,
        annex.collision_groups, annex.collision_member_units,
        annex.ineligible_units, extraction.status == OBSERVED, _seal=_SEAL,
    )
