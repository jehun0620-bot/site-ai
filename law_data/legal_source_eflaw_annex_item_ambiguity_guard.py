# -*- coding: utf-8 -*-
"""Offline, response-local EFLAW ANNEX item ambiguity boundary.

This checks ONLY the user-observed path 법령/별표/별표단위 and the raw
별표번호 + 별표가지번호 strings. A unique pair does not prove an official
annex identity, legal effect, provenance, or candidate binding permission.
Missing/empty/wrong-type fields fail closed; no default branch is invented.
Dates are compared as raw strings ONLY inside repeated pairs, not interpreted.
Serialize only public_record(), never input payloads or private objects.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from law_data.legal_source_eflaw_temporal_response_field_extraction import (
    _read_response,
    extract_legal_source_eflaw_temporal_response_fields,
)

NOT_EVALUATED = "NOT_EVALUATED"
AMBIGUOUS = "EFLAW_ANNEX_RESPONSE_LOCAL_RAW_PAIR_COLLISIONS_UNRESOLVED"
INELIGIBLE = "EFLAW_ANNEX_RESPONSE_LOCAL_RAW_PAIRS_INELIGIBLE"
UNIQUE_LOCAL = "EFLAW_ANNEX_RESPONSE_LOCAL_RAW_PAIRS_DISTINCT_UNVERIFIED_ORIGIN"
_SEAL = object()
_MISSING = object()


@dataclass(frozen=True, slots=True)
class LegalSourceEflawAnnexItemAmbiguityInspection:
    """Sealed numerical diagnostics, never an item-identity certificate."""

    status: str
    annex_units_examined: int
    annex_date_fields: int
    eligible_units: int
    ineligible_units: int
    distinct_local_pairs: int
    collision_groups: int
    collision_member_units: int
    collision_excess_units: int
    collision_date_variation_groups: int
    collision_date_unresolved_groups: int
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_ANNEX_AMBIGUITY_RESULT_FORBIDDEN")
        if type(self.status) is not str or self.status not in (AMBIGUOUS, INELIGIBLE, UNIQUE_LOCAL):
            raise ValueError("INVALID_ANNEX_AMBIGUITY_STATUS")
        counts = (
            self.annex_units_examined, self.annex_date_fields,
            self.eligible_units, self.ineligible_units, self.distinct_local_pairs,
            self.collision_groups, self.collision_member_units,
            self.collision_excess_units, self.collision_date_variation_groups,
            self.collision_date_unresolved_groups,
        )
        if any(type(v) is not int or v < 0 for v in counts):
            raise ValueError("INVALID_ANNEX_AMBIGUITY_COUNTS")
        if self.eligible_units + self.ineligible_units != self.annex_units_examined:
            raise ValueError("INCONSISTENT_ANNEX_ELIGIBILITY_COUNTS")
        if self.annex_date_fields > self.annex_units_examined:
            raise ValueError("INCONSISTENT_ANNEX_DATE_COUNTS")
        if self.distinct_local_pairs + self.collision_excess_units != self.eligible_units:
            raise ValueError("INCONSISTENT_ANNEX_PAIR_COUNTS")
        if (self.collision_groups > self.collision_excess_units or
                self.collision_member_units != self.collision_groups + self.collision_excess_units or
                self.collision_member_units > self.eligible_units):
            raise ValueError("INCONSISTENT_ANNEX_COLLISION_COUNTS")
        if (self.collision_date_variation_groups > self.collision_groups or
                self.collision_date_unresolved_groups > self.collision_groups):
            raise ValueError("INCONSISTENT_ANNEX_COLLISION_DIAGNOSTICS")
        expected = (AMBIGUOUS if self.collision_groups else
                    INELIGIBLE if self.ineligible_units else UNIQUE_LOCAL)
        if self.status != expected:
            raise ValueError("INCONSISTENT_ANNEX_AMBIGUITY_STATUS")

    def public_record(self) -> dict[str, str | int | bool]:
        """Fixed, non-sensitive fields only. No identifiers, date values, prose."""
        return {
            "record_kind": "EFLAW_ANNEX_RESPONSE_LOCAL_AMBIGUITY_GUARD_V1",
            "status": self.status,
            "annex_units_examined": self.annex_units_examined,
            "annex_date_fields": self.annex_date_fields,
            "eligible_units": self.eligible_units,
            "ineligible_units": self.ineligible_units,
            "distinct_local_pairs": self.distinct_local_pairs,
            "collision_groups": self.collision_groups,
            "collision_member_units": self.collision_member_units,
            "collision_excess_units": self.collision_excess_units,
            "collision_date_variation_groups": self.collision_date_variation_groups,
            "collision_date_unresolved_groups": self.collision_date_unresolved_groups,
            "identity_basis": "RAW_RESPONSE_LOCAL_NUMBER_AND_BRANCH_NOT_CANONICAL",
            "missing_branch_auto_normalization": "FORBIDDEN",
            "collision_merging": "FORBIDDEN",
            "array_index_identifier_promotion": "FORBIDDEN",
            "temporal_candidate_creation": "NOT_PERFORMED",
            "annex_date_candidate_join": "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY",
            "official_item_identity_decision": NOT_EVALUATED,
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "annex_legal_effect_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_annex_item_ambiguity(
    payload: bytes,
) -> LegalSourceEflawAnnexItemAmbiguityInspection:
    """Count collisions of exact observed raw pairs; never bind any date."""
    extraction = extract_legal_source_eflaw_temporal_response_fields(payload)
    law = _read_response(payload)
    section = law.get("별표")
    if type(section) is not dict or type(section.get("별표단위")) is not list:
        raise ValueError("ANNEX_AMBIGUITY_UNITS_UNRESOLVED")
    units = section["별표단위"]
    if len(units) != extraction.annex_units_examined:
        raise ValueError("ANNEX_AMBIGUITY_EXTRACTION_COUNT_MISMATCH")

    pairs: dict[tuple[str, str], list[int]] = defaultdict(list)
    ineligible = 0
    for index, unit in enumerate(units):
        if type(unit) is not dict:
            raise ValueError("ANNEX_AMBIGUITY_UNIT_SHAPE_UNRESOLVED")
        primary = unit.get("별표번호", _MISSING)
        branch = unit.get("별표가지번호", _MISSING)
        if type(primary) is not str or not primary or type(branch) is not str or not branch:
            ineligible += 1
            continue
        pairs[(primary, branch)].append(index)

    collisions = [indices for indices in pairs.values() if len(indices) > 1]
    date_changed = date_unresolved = 0
    for indices in collisions:
        dates = [units[i].get("별표시행일자", _MISSING) for i in indices]
        if any(v is _MISSING for v in dates):
            date_unresolved += 1
        elif any(v != dates[0] for v in dates[1:]):
            date_changed += 1
    excess = sum(len(indices) - 1 for indices in collisions)
    members = sum(len(indices) for indices in collisions)
    return LegalSourceEflawAnnexItemAmbiguityInspection(
        AMBIGUOUS if collisions else INELIGIBLE if ineligible else UNIQUE_LOCAL,
        len(units), extraction.annex_count,
        len(units) - ineligible, ineligible, len(pairs),
        len(collisions), members, excess, date_changed, date_unresolved,
        _seal=_SEAL,
    )
