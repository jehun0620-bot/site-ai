# -*- coding: utf-8 -*-
"""Offline response-local article ambiguity BARRIER for one observed EFLAW shape.

The response may contain multiple article units with the same raw
(조문번호, presence + 조문가지번호, 조문키) triple yet different 조문내용.
A unique triple in ONE response would still NOT be an official identifier.
This module NEVER assigns IDs, creates temporal candidates, joins dates,
serializes private literals, fetches data, or admits any Rule Engine input.

Only public_record() is permitted for diagnostics. Never serialize input,
internal local keys, private result objects, or upstream HTTP outcomes.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from law_data.legal_source_eflaw_temporal_response_field_extraction import (
    _read_response, extract_legal_source_eflaw_temporal_response_fields,
)

NOT_EVALUATED = "NOT_EVALUATED"
AMBIGUOUS = "EFLAW_ARTICLE_RESPONSE_LOCAL_TRIPLE_COLLISIONS_UNRESOLVED"
INELIGIBLE = "EFLAW_ARTICLE_RESPONSE_LOCAL_TRIPLES_INELIGIBLE"
UNIQUE_LOCAL = "EFLAW_ARTICLE_RESPONSE_LOCAL_TRIPLES_DISTINCT_UNVERIFIED_ORIGIN"
_SEAL = object()
_MISSING = object()


@dataclass(frozen=True, slots=True)
class LegalSourceEflawArticleItemAmbiguityInspection:
    """Counts-only read-only inspection; cannot grant any binding permission."""
    status: str
    article_units_examined: int
    article_date_fields: int
    raw_pair_repeated_groups: int
    triple_eligible_units: int
    triple_ineligible_units: int
    triple_collision_groups: int
    triple_collision_member_units: int
    triple_collision_excess_units: int
    collision_content_variation_groups: int
    collision_date_variation_groups: int
    collision_content_unresolved_groups: int
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_ARTICLE_AMBIGUITY_RESULT_FORBIDDEN")
        if self.status not in (AMBIGUOUS, INELIGIBLE, UNIQUE_LOCAL):
            raise ValueError("INVALID_ARTICLE_AMBIGUITY_STATUS")
        values = (
            self.article_units_examined, self.article_date_fields,
            self.raw_pair_repeated_groups, self.triple_eligible_units,
            self.triple_ineligible_units, self.triple_collision_groups,
            self.triple_collision_member_units, self.triple_collision_excess_units,
            self.collision_content_variation_groups,
            self.collision_date_variation_groups,
            self.collision_content_unresolved_groups,
        )
        if any(type(x) is not int or x < 0 for x in values):
            raise ValueError("INVALID_ARTICLE_AMBIGUITY_COUNTS")
        if self.triple_eligible_units + self.triple_ineligible_units != self.article_units_examined:
            raise ValueError("INCONSISTENT_ARTICLE_ELIGIBILITY_COUNTS")
        if self.article_date_fields > self.article_units_examined:
            raise ValueError("INCONSISTENT_ARTICLE_DATE_COUNTS")
        if self.raw_pair_repeated_groups > self.article_units_examined:
            raise ValueError("INCONSISTENT_RAW_PAIR_REPETITIONS")
        if self.triple_collision_groups > self.triple_collision_excess_units:
            raise ValueError("INCONSISTENT_ARTICLE_COLLISION_COUNTS")
        if self.triple_collision_member_units != (
            self.triple_collision_groups + self.triple_collision_excess_units
        ) or self.triple_collision_member_units > self.triple_eligible_units:
            raise ValueError("INCONSISTENT_ARTICLE_COLLISION_COUNTS")
        if any(v > self.triple_collision_groups for v in (
            self.collision_content_variation_groups,
            self.collision_date_variation_groups,
            self.collision_content_unresolved_groups,
        )):
            raise ValueError("INCONSISTENT_ARTICLE_COLLISION_DIAGNOSTICS")
        expected = (AMBIGUOUS if self.triple_collision_groups else
                    INELIGIBLE if self.triple_ineligible_units else UNIQUE_LOCAL)
        if self.status != expected:
            raise ValueError("INCONSISTENT_ARTICLE_AMBIGUITY_STATUS")

    def public_record(self) -> dict[str, str | int | bool]:
        """Allowlist only; no raw response, identifiers, text, or date values."""
        return {
            "record_kind": "EFLAW_ARTICLE_RESPONSE_LOCAL_AMBIGUITY_GUARD_V1",
            "status": self.status,
            "article_units_examined": self.article_units_examined,
            "article_date_fields": self.article_date_fields,
            "raw_pair_repeated_groups": self.raw_pair_repeated_groups,
            "triple_eligible_units": self.triple_eligible_units,
            "triple_ineligible_units": self.triple_ineligible_units,
            "triple_collision_groups": self.triple_collision_groups,
            "triple_collision_member_units": self.triple_collision_member_units,
            "triple_collision_excess_units": self.triple_collision_excess_units,
            "collision_content_variation_groups": self.collision_content_variation_groups,
            "collision_date_variation_groups": self.collision_date_variation_groups,
            "collision_content_unresolved_groups": self.collision_content_unresolved_groups,
            "pair_key_basis": "RAW_RESPONSE_LOCAL_FIELDS_NOT_CANONICAL",
            "branch_absence_distinct_from_present_string_zero": True,
            "content_comparison_basis": "RAW_JSON_VALUE_EQUALITY_ONLY_NOT_LEGAL_EQUIVALENCE",
            "temporal_candidate_creation": "NOT_PERFORMED",
            "article_date_candidate_join": "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY",
            "collision_merging": "FORBIDDEN",
            "array_index_identifier_promotion": "FORBIDDEN",
            "official_item_identity_decision": NOT_EVALUATED,
            "source_origin_attestation": NOT_EVALUATED,
            "current_legal_validity": NOT_EVALUATED,
            "legal_applicability": NOT_EVALUATED,
            "production_admission": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_article_item_ambiguity(
    payload: bytes,
) -> LegalSourceEflawArticleItemAmbiguityInspection:
    """Observe exact article-unit path, never bind to legal identifiers/dates."""
    extraction = extract_legal_source_eflaw_temporal_response_fields(payload)
    law = _read_response(payload)
    section = law.get("조문")
    if type(section) is not dict or type(section.get("조문단위")) is not list:
        raise ValueError("ARTICLE_AMBIGUITY_UNITS_UNRESOLVED")
    units = section["조문단위"]
    if len(units) != extraction.article_units_examined:
        raise ValueError("ARTICLE_AMBIGUITY_EXTRACTION_COUNT_MISMATCH")

    pairs: dict[tuple[str, bool, str | None], int] = defaultdict(int)
    triples: dict[tuple[str, bool, str | None, str], list[int]] = defaultdict(list)
    ineligible = 0
    for index, unit in enumerate(units):
        if type(unit) is not dict:
            raise ValueError("ARTICLE_AMBIGUITY_UNIT_SHAPE_UNRESOLVED")
        primary = unit.get("조문번호", _MISSING)
        branch = unit.get("조문가지번호", _MISSING)
        key = unit.get("조문키", _MISSING)
        if (type(primary) is not str or not primary or
            (branch is not _MISSING and (type(branch) is not str or not branch))):
            ineligible += 1
            continue
        pair = (primary, branch is not _MISSING,
                None if branch is _MISSING else branch)
        pairs[pair] += 1
        if type(key) is not str or not key:
            ineligible += 1
            continue
        triples[(*pair, key)].append(index)

    repeated_pairs = sum(n > 1 for n in pairs.values())
    collisions = [indices for indices in triples.values() if len(indices) > 1]
    content_changed = date_changed = content_unresolved = 0
    for indices in collisions:
        group = [units[i] for i in indices]
        contents = [u.get("조문내용", _MISSING) for u in group]
        dates = [u.get("조문시행일자", _MISSING) for u in group]
        # Values remain in local variables only, never returned or exposed.
        if any(value is _MISSING for value in contents):
            content_unresolved += 1
        elif any(v != contents[0] for v in contents[1:]):
            content_changed += 1
        if any(v != dates[0] for v in dates[1:]):
            date_changed += 1

    excess = sum(len(g) - 1 for g in collisions)
    member_count = sum(len(g) for g in collisions)
    status = AMBIGUOUS if collisions else INELIGIBLE if ineligible else UNIQUE_LOCAL
    return LegalSourceEflawArticleItemAmbiguityInspection(
        status, len(units), extraction.article_count,
        repeated_pairs, len(units) - ineligible, ineligible,
        len(collisions), member_count, excess,
        content_changed, date_changed, content_unresolved, _seal=_SEAL,
    )
