# -*- coding: utf-8 -*-
"""Offline extraction of four eflaw field shapes OBSERVED IN ONE RESPONSE.

Only paths seen in the 2026-10-15 user-local one-response shape audit
are inspected. No schema-generalization, law-version identity binding, network,
file access, raw URL, original-text attestation or legal-effect decision.

The three date-field strings are retained privately as *literal response text*,
NOT parsed calendar dates or verified temporal-evidence candidates. The
supplementary content's observed ARRAY TYPE is counted; its contents are not
inspected or retained. No candidate registry or Rule Engine is mutated.

Do not serialize instances or use dataclasses.asdict. Only public_record()
provides allowlisted non-sensitive diagnostics. A matching shape does not
verify a response's source, currentness, authority, or legal applicability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

NOT_EVALUATED = "NOT_EVALUATED"
OBSERVED = "EFLAW_TEMPORAL_LOCAL_FIELD_SHAPES_OBSERVED_UNVERIFIED_ORIGIN"
PARTIAL = "EFLAW_TEMPORAL_LOCAL_FIELD_SHAPES_PARTIAL_UNVERIFIED_ORIGIN"
_MAX_BYTES = 10_000_000  # After bytes are received; not a transfer limit.
_MAX_UNITS_PER_GROUP = 20_000
_MAX_TOTAL_UNITS = 50_000
_SEAL = object()

# These exact container paths, not arbitrary recursive occurrences, were
# observed in the single historical eflaw response from the user's probe.
_FIELDS = (
    ("LAW_EFFECTIVE", "기본정보", None, "시행일자", str),
    ("ARTICLE_EFFECTIVE", "조문", "조문단위", "조문시행일자", str),
    ("ANNEX_EFFECTIVE", "별표", "별표단위", "별표시행일자", str),
    ("SUPPLEMENTARY_CONTENT", "부칙", "부칙단위", "부칙내용", list),
)


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("TEMPORAL_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    raise ValueError("TEMPORAL_NONSTANDARD_JSON_CONSTANT")


def _read_response(payload: object) -> dict[str, object]:
    if type(payload) is not bytes or not 0 < len(payload) <= _MAX_BYTES:
        raise ValueError("TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED")
    try:
        root = json.loads(
            payload.decode("utf-8-sig"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_invalid_constant,
        )
    except (UnicodeError, RecursionError, OverflowError):
        raise ValueError("TEMPORAL_RESPONSE_JSON_UNRESOLVED") from None
    except ValueError as exc:
        if str(exc) in ("TEMPORAL_DUPLICATE_JSON_KEY", "TEMPORAL_NONSTANDARD_JSON_CONSTANT"):
            raise ValueError(str(exc)) from None
        raise ValueError("TEMPORAL_RESPONSE_JSON_UNRESOLVED") from None
    if type(root) is not dict or type(root.get("법령")) is not dict:
        raise ValueError("TEMPORAL_EFLAW_ROOT_UNRESOLVED")
    return root["법령"]


@dataclass(frozen=True, slots=True)
class LegalSourceEflawTemporalResponseFieldExtraction:
    """Private response-local field literals; public output exposes COUNTS only.

    The date literal indices refer to list position in this one JSON response,
    never a canonical article, annex, amendment or legal source identifier.
    """
    status: str
    law_count: int
    article_count: int
    annex_count: int
    supplementary_count: int
    article_units_examined: int
    annex_units_examined: int
    supplementary_units_examined: int
    _date_literals: tuple[tuple[str, int | None, str], ...] = field(repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_TEMPORAL_EXTRACTION_RESULT_FORBIDDEN")
        if self.status not in (OBSERVED, PARTIAL):
            raise ValueError("INVALID_TEMPORAL_EXTRACTION_STATUS")
        counts = (self.law_count, self.article_count, self.annex_count,
                  self.supplementary_count, self.article_units_examined,
                  self.annex_units_examined, self.supplementary_units_examined)
        if any(type(x) is not int or x < 0 for x in counts):
            raise ValueError("INVALID_TEMPORAL_EXTRACTION_COUNTS")
        if self.law_count > 1 or self.article_count > self.article_units_examined or (
            self.annex_count > self.annex_units_examined
            or self.supplementary_count > self.supplementary_units_examined
        ):
            raise ValueError("INCONSISTENT_TEMPORAL_EXTRACTION_COUNTS")
        all_present = all(x > 0 for x in counts[:4])
        if (self.status == OBSERVED) != all_present:
            raise ValueError("INCONSISTENT_TEMPORAL_EXTRACTION_STATUS")
        if type(self._date_literals) is not tuple or len(self._date_literals) != sum(counts[:3]):
            raise ValueError("INCONSISTENT_PRIVATE_DATE_LITERALS")
        for kind, index, text in self._date_literals:
            if kind not in ("LAW_EFFECTIVE", "ARTICLE_EFFECTIVE", "ANNEX_EFFECTIVE"):
                raise ValueError("INVALID_PRIVATE_DATE_KIND")
            if (index is not None and (type(index) is not int or index < 0)) or type(text) is not str:
                raise ValueError("INVALID_PRIVATE_DATE_LITERAL")
            if (kind == "LAW_EFFECTIVE" and index is not None) or (
                kind != "LAW_EFFECTIVE" and index is None
            ):
                raise ValueError("INVALID_PRIVATE_DATE_INDEX")

    def public_record(self) -> dict[str, str | int | bool]:
        """Explicit allowlist: no dates, source identifiers, URL or body."""
        return {
            "record_kind": "EFLAW_TEMPORAL_RESPONSE_LOCAL_FIELD_SHAPES_V1",
            "status": self.status,
            "law_date_string_count": self.law_count,
            "article_date_string_count": self.article_count,
            "annex_date_string_count": self.annex_count,
            "supplementary_array_count": self.supplementary_count,
            "article_units_examined": self.article_units_examined,
            "annex_units_examined": self.annex_units_examined,
            "supplementary_units_examined": self.supplementary_units_examined,
            "path_basis": "ONE_PRIOR_LIVE_RESPONSE_OBSERVATION_NOT_GENERAL_SCHEMA",
            "value_basis": "CALLER_PROVIDED_RESPONSE_BYTES_UNATTESTED",
            "date_values_parsed_or_verified": False,
            "supplementary_content_interpreted": False,
            "inventory_candidate_admission": NOT_EVALUATED,
            "response_source_identity_decision": NOT_EVALUATED,
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "article_legal_effect_decision": NOT_EVALUATED,
            "annex_legal_effect_decision": NOT_EVALUATED,
            "supplementary_legal_effect_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def extract_legal_source_eflaw_temporal_response_fields(
    payload: bytes,
) -> LegalSourceEflawTemporalResponseFieldExtraction:
    """Read-only literal extraction for four EXACT response-local JSON paths.

    Missing paths are PARTIAL, not legal absence. Wrong types or inconsistent
    container structures raise fixed fail-closed codes without echoing values.
    Caller must separately verify the request, response, origin and legal law.
    """
    law = _read_response(payload)
    counts: dict[str, int] = {spec[0]: 0 for spec in _FIELDS}
    examined: dict[str, int] = {spec[0]: 0 for spec in _FIELDS}
    literals: list[tuple[str, int | None, str]] = []
    total_units = 0

    for kind, container, collection, key, expected_type in _FIELDS:
        section = law.get(container)
        if section is None and container not in law:
            continue  # No supplied field, not proof of absence in a legal text.
        if type(section) is not dict:
            raise ValueError("TEMPORAL_SECTION_SHAPE_UNRESOLVED")
        if collection is None:
            if key in section:
                text = section[key]
                if type(text) is not expected_type:
                    raise ValueError("TEMPORAL_FIELD_TYPE_UNRESOLVED")
                counts[kind] = 1
                literals.append((kind, None, text))
            continue

        if collection not in section:
            continue
        units = section[collection]
        if type(units) is not list or len(units) > _MAX_UNITS_PER_GROUP:
            raise ValueError("TEMPORAL_UNIT_COLLECTION_UNRESOLVED")
        total_units += len(units)
        if total_units > _MAX_TOTAL_UNITS:
            raise ValueError("TEMPORAL_TOTAL_UNIT_BOUND_EXCEEDED")
        examined[kind] = len(units)
        for index, unit in enumerate(units):
            if type(unit) is not dict:
                raise ValueError("TEMPORAL_UNIT_SHAPE_UNRESOLVED")
            if key not in unit:
                continue
            value = unit[key]
            if type(value) is not expected_type:
                raise ValueError("TEMPORAL_FIELD_TYPE_UNRESOLVED")
            counts[kind] += 1
            if kind != "SUPPLEMENTARY_CONTENT":
                literals.append((kind, index, value))
            # Never traverse/store contents of supplementary arrays.

    four = tuple(counts[k] for k in (
        "LAW_EFFECTIVE", "ARTICLE_EFFECTIVE", "ANNEX_EFFECTIVE", "SUPPLEMENTARY_CONTENT"
    ))
    return LegalSourceEflawTemporalResponseFieldExtraction(
        OBSERVED if all(four) else PARTIAL,
        *four,
        examined["ARTICLE_EFFECTIVE"], examined["ANNEX_EFFECTIVE"],
        examined["SUPPLEMENTARY_CONTENT"], tuple(literals), _seal=_SEAL,
    )
