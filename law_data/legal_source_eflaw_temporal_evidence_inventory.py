# -*- coding: ascii -*-
"""Offline eflaw temporal-field CANDIDATE inventory, never law-in-force logic.

Names below are FIELD LABELS documented in the publicly reviewed MOLEG
'eflaw' guide. Their nested JSON locations have NOT been established here.
Every item is caller-declared and NOT an observed, authenticated API field.
Absence of a caller item is NOT absence of a provision from any legal source.
Article, annex and supplementary-provision dates may follow separate rules;
no precedence, as-of calculation, current validity, provenance, SITE admission,
or history inference is performed. lsHistory is a SEPARATE HTML service.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re

from law_data.legal_source_public_request_descriptor import (
    LegalSourcePublicRequestDescriptor,
)
from law_data.legal_source_eflaw_official_guide_evidence_boundary import (
    ALIGNED as GUIDE_ALIGNED,
    LegalSourceEflawOfficialGuideReference,
    inspect_legal_source_eflaw_official_guide_evidence,
)

NOT_EVALUATED = "NOT_EVALUATED"
INVENTORY_UNVERIFIED = "EFLAW_TEMPORAL_CANDIDATES_UNVERIFIED"
EMPTY_UNVERIFIED = "EFLAW_TEMPORAL_CANDIDATES_NOT_SUPPLIED"
GUIDE_UNRESOLVED = "EFLAW_TEMPORAL_GUIDE_REFERENCE_UNRESOLVED"
CLAIM_CONFLICT = "EFLAW_TEMPORAL_CANDIDATE_CONFLICT_UNRESOLVED"
_KINDS = {
    "LAW_EFFECTIVE": "\uC2DC\uD589\uC77C\uC790",
    "ARTICLE_EFFECTIVE": "\uC870\uBB38\uC2DC\uD589\uC77C\uC790",
    "ANNEX_EFFECTIVE": "\uBCC4\uD45C\uC2DC\uD589\uC77C\uC790",
    "SUPPLEMENTARY_CONTENT": "\uBD80\uCE59\uB0B4\uC6A9",
}
_KNOWN_STATUSES = frozenset((
    INVENTORY_UNVERIFIED, EMPTY_UNVERIFIED, GUIDE_UNRESOLVED, CLAIM_CONFLICT,
))
_LOCATOR = re.compile(r"[A-Za-z0-9_:.\-]{1,64}\Z")
_ASCII_DATE = re.compile(r"[0-9]{8}\Z")
_SEAL = object()


def _check_ymd(value: object) -> None:
    if type(value) is not str or _ASCII_DATE.fullmatch(value) is None:
        raise ValueError("INVALID_DECLARED_DATE")
    try:
        date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        raise ValueError("INVALID_DECLARED_DATE") from None


@dataclass(frozen=True, slots=True)
class LegalSourceEflawTemporalEvidenceCandidate:
    """A private UNVERIFIED caller claim; DO NOT serialize or expose fields.

    For dated fields, None = NOT SUPPLIED BY CALLER (not absent in law).
    For supplementary content, content_declared is only a caller claim of
    presence; neither content nor a supplementary effective date is parsed.
    Locator is an opaque LOCAL key, NOT an official provision identifier.
    """
    kind: str
    field_name: str = field(repr=False)
    locator: str | None = field(default=None, repr=False)
    declared_yyyymmdd: str | None = field(default=None, repr=False)
    content_declared: bool | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in _KINDS:
            raise ValueError("UNSUPPORTED_TEMPORAL_EVIDENCE_KIND")
        if type(self.field_name) is not str or self.field_name != _KINDS[self.kind]:
            raise ValueError("TEMPORAL_FIELD_KIND_MISMATCH")
        if self.kind == "LAW_EFFECTIVE":
            if self.locator is not None:
                raise ValueError("LAW_TEMPORAL_LOCATOR_FORBIDDEN")
        elif type(self.locator) is not str or _LOCATOR.fullmatch(self.locator) is None:
            raise ValueError("INVALID_LOCAL_TEMPORAL_LOCATOR")
        if self.kind == "SUPPLEMENTARY_CONTENT":
            if self.declared_yyyymmdd is not None:
                raise ValueError("SUPPLEMENTARY_DATE_INFERENCE_FORBIDDEN")
            if type(self.content_declared) is not bool:
                raise ValueError("INVALID_SUPPLEMENTARY_CONTENT_CLAIM")
        else:
            if self.content_declared is not None:
                raise ValueError("CONTENT_CLAIM_FOR_DATE_FIELD_FORBIDDEN")
            if self.declared_yyyymmdd is not None:
                _check_ymd(self.declared_yyyymmdd)

    @property
    def local_key(self) -> tuple[str, str | None]:
        """Internal per-scope key. Not evidence of a canonical article/annex."""
        return self.kind, self.locator

    @property
    def claim_value(self) -> str | bool | None:
        return (self.content_declared if self.kind == "SUPPLEMENTARY_CONTENT"
                else self.declared_yyyymmdd)


@dataclass(frozen=True, slots=True)
class LegalSourceEflawTemporalEvidenceInspection:
    """Fixed numeric diagnostics only; cannot attest observed legal facts."""
    status: str
    guide_reference_check: str
    temporal_candidate_count: int
    law_candidate_count: int
    article_candidate_count: int
    annex_candidate_count: int
    supplementary_candidate_count: int
    selector_vs_declared_law_date: str
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_TEMPORAL_INSPECTION_CONSTRUCTION_FORBIDDEN")
        if type(self.status) is not str or self.status not in _KNOWN_STATUSES:
            raise ValueError("INVALID_TEMPORAL_INSPECTION_STATUS")
        if self.guide_reference_check not in ("MATCH", "UNRESOLVED"):
            raise ValueError("INVALID_TEMPORAL_GUIDE_CHECK")
        counts = (self.temporal_candidate_count, self.law_candidate_count,
                  self.article_candidate_count, self.annex_candidate_count,
                  self.supplementary_candidate_count)
        if any(type(x) is not int or x < 0 for x in counts):
            raise ValueError("INVALID_TEMPORAL_COUNTS")
        if self.temporal_candidate_count != sum(counts[1:]):
            raise ValueError("INCONSISTENT_TEMPORAL_COUNTS")
        if self.selector_vs_declared_law_date not in (
            "MATCH_DECLARED_UNVERIFIED", "DIFFERENT_DECLARED_UNVERIFIED",
            "NOT_SUPPLIED_BY_CALLER", NOT_EVALUATED,
        ):
            raise ValueError("INVALID_DECLARED_SELECTOR_RELATION")
        if self.status == GUIDE_UNRESOLVED and self.guide_reference_check != "UNRESOLVED":
            raise ValueError("INCONSISTENT_TEMPORAL_GUIDE_STATUS")
        if self.status != GUIDE_UNRESOLVED and self.guide_reference_check != "MATCH":
            raise ValueError("INCONSISTENT_TEMPORAL_GUIDE_STATUS")
        if self.status == EMPTY_UNVERIFIED and self.temporal_candidate_count != 0:
            raise ValueError("INCONSISTENT_EMPTY_TEMPORAL_INVENTORY")
        if self.status == INVENTORY_UNVERIFIED and self.temporal_candidate_count == 0:
            raise ValueError("INCONSISTENT_NONEMPTY_TEMPORAL_INVENTORY")

    def public_record(self) -> dict[str, str | int]:
        return {
            "record_kind": "LEGAL_EFLAW_TEMPORAL_CANDIDATE_INVENTORY_V1",
            "status": self.status,
            "guide_reference_check": self.guide_reference_check,
            "temporal_candidate_count": self.temporal_candidate_count,
            "law_candidate_count": self.law_candidate_count,
            "article_candidate_count": self.article_candidate_count,
            "annex_candidate_count": self.annex_candidate_count,
            "supplementary_candidate_count": self.supplementary_candidate_count,
            "selector_vs_declared_law_date": self.selector_vs_declared_law_date,
            "item_basis": "CALLER_DECLARED_NOT_RESPONSE_FIELD_OBSERVED",
            "absent_candidate_means": "NOT_SUPPLIED_BY_CALLER_NOT_LEGAL_ABSENCE",
            "supplementary_effective_date_inference": "FORBIDDEN",
            "history_source_boundary": "LSHISTORY_HTML_SEPARATE_UNINSPECTED",
            "api_response_field_paths_verified": NOT_EVALUATED,
            "guide_capture_authenticity": NOT_EVALUATED,
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "article_legal_effect_decision": NOT_EVALUATED,
            "annex_legal_effect_decision": NOT_EVALUATED,
            "supplementary_legal_effect_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_temporal_evidence_inventory(
    descriptor: LegalSourcePublicRequestDescriptor,
    guide_reference: LegalSourceEflawOfficialGuideReference,
    candidates: tuple[LegalSourceEflawTemporalEvidenceCandidate, ...],
) -> LegalSourceEflawTemporalEvidenceInspection:
    """Inventory only; no network, response parsing, authenticity, or date law."""
    if type(descriptor) is not LegalSourcePublicRequestDescriptor or descriptor.target != "eflaw":
        raise TypeError("INVALID_EFLAW_TEMPORAL_DESCRIPTOR")
    if type(guide_reference) is not LegalSourceEflawOfficialGuideReference:
        raise TypeError("INVALID_TEMPORAL_GUIDE_REFERENCE")
    if type(candidates) is not tuple or any(
        type(item) is not LegalSourceEflawTemporalEvidenceCandidate for item in candidates
    ):
        raise TypeError("INVALID_TEMPORAL_CANDIDATE_COLLECTION")
    if len(candidates) > 512:
        raise ValueError("TOO_MANY_TEMPORAL_CANDIDATES")

    guide = inspect_legal_source_eflaw_official_guide_evidence(descriptor, guide_reference)
    if guide.status != GUIDE_ALIGNED:
        return LegalSourceEflawTemporalEvidenceInspection(
            GUIDE_UNRESOLVED, "UNRESOLVED", 0, 0, 0, 0, 0, NOT_EVALUATED, _seal=_SEAL,
        )

    seen: dict[tuple[str, str | None], str | bool | None] = {}
    counts = {kind: 0 for kind in _KINDS}
    for item in candidates:
        key = item.local_key
        if key in seen:
            if seen[key] != item.claim_value or type(seen[key]) is not type(item.claim_value):
                return LegalSourceEflawTemporalEvidenceInspection(
                    CLAIM_CONFLICT, "MATCH", len(seen),
                    counts["LAW_EFFECTIVE"], counts["ARTICLE_EFFECTIVE"],
                    counts["ANNEX_EFFECTIVE"], counts["SUPPLEMENTARY_CONTENT"],
                    NOT_EVALUATED, _seal=_SEAL,
                )
            continue
        seen[key] = item.claim_value
        counts[item.kind] += 1
    # Selector vs caller's law-level claim is descriptive and NOT proof of
    # law-effective-on-date. Article/annex/supplementary claims are independent.
    base = seen.get(("LAW_EFFECTIVE", None))
    relation = (
        "NOT_SUPPLIED_BY_CALLER" if base is None
        else "MATCH_DECLARED_UNVERIFIED" if base == descriptor.efyd
        else "DIFFERENT_DECLARED_UNVERIFIED"
    )
    return LegalSourceEflawTemporalEvidenceInspection(
        INVENTORY_UNVERIFIED if seen else EMPTY_UNVERIFIED,
        "MATCH", len(seen), counts["LAW_EFFECTIVE"],
        counts["ARTICLE_EFFECTIVE"], counts["ANNEX_EFFECTIVE"],
        counts["SUPPLEMENTARY_CONTENT"], relation, _seal=_SEAL,
    )
