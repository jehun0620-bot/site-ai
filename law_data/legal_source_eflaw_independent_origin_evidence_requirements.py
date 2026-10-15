# -*- coding: utf-8 -*-
"""Offline, fail-closed EFLAW independent-origin EVIDENCE-GAP inventory.

Combines already unverified diagnostics; it NEVER authenticates a fetch, an
original law text, a canonical version, effective legal dates, or parcel use.
The list/detail comparison and the official-guide URL share a provider and
are not independent official-origin evidence. A claimed receipt, even if its
local digest matches, is NOT a witnessed/authenticated acquisition.

Engineering review requirements here are NOT statutory proof requirements.
No network, disk, request construction, evidence registration, Rule Engine,
source promotion, or Production permission. Log ONLY public_record().
"""
from __future__ import annotations

from dataclasses import dataclass, field

from law_data.legal_source_evidence_inspection import INDEPENDENT_CHECKS_REQUIRED
from law_data.legal_source_eflaw_list_detail_local_correspondence import (
    EXACT_ONE, NORMALIZED_ONLY,
    LegalSourceEflawListDetailLocalCorrespondenceInspection,
)
from law_data.legal_source_eflaw_official_guide_evidence_boundary import (
    ALIGNED as GUIDE_ALIGNED,
    LegalSourceEflawOfficialGuideEvidenceInspection,
)
from law_data.legal_source_eflaw_local_acquisition_observation import (
    LOCAL_SUCCESS,
    LegalSourceEflawLocalAcquisitionObservation,
)
from law_data.legal_source_acquisition_receipt_inspection import (
    LegalSourceAcquisitionReceiptInspection,
)

NOT_EVALUATED = "NOT_EVALUATED"
COLLISION_BLOCKED = "EFLAW_INDEPENDENT_ORIGIN_EVIDENCE_BLOCKED_LOCAL_COLLISIONS"
STRUCTURE_BLOCKED = "EFLAW_INDEPENDENT_ORIGIN_EVIDENCE_BLOCKED_STRUCTURE"
UNATTESTED_BLOCKED = "EFLAW_INDEPENDENT_ORIGIN_EVIDENCE_BLOCKED_UNATTESTED"
_PREBINDING_COLLISIONS = "EFLAW_TEMPORAL_PREBINDING_BLOCKED_RESPONSE_LOCAL_COLLISIONS"
_PREBINDING_STRUCTURE = "EFLAW_TEMPORAL_PREBINDING_BLOCKED_STRUCTURE_OR_DATE_SHAPE"
_PREBINDING_UNATTESTED = "EFLAW_TEMPORAL_PREBINDING_BLOCKED_UNATTESTED_IDENTITIES"
_REQUIRED = tuple(INDEPENDENT_CHECKS_REQUIRED) + (
    "EFLAW_INDEPENDENT_ACQUISITION_ORIGIN_ATTESTATION",
    "EFLAW_ARTICLE_LOCAL_COLLISION_INDEPENDENT_RESOLUTION",
    "EFLAW_ANNEX_AND_SUPPLEMENTARY_PROVISION_LEGAL_EFFECT",
)
_SEAL = object()

_CORRESPONDENCE = frozenset((
    "EXACT_TRIPLE_SAME_PROVIDER_UNATTESTED",
    "NORMALIZED_ONLY_SAME_PROVIDER_UNATTESTED",
    "SAME_PROVIDER_RELATION_UNRESOLVED",
))
_GUIDE = frozenset(("NOT_SUPPLIED", "GUIDE_REFERENCE_ONLY", "GUIDE_UNRESOLVED"))
_FETCH = frozenset(("NOT_SUPPLIED", "LOCAL_HTTP_200_UNVERIFIED_ORIGIN", "LOCAL_FETCH_UNRESOLVED"))
_RECEIPT = frozenset(("NOT_SUPPLIED", "DECLARED_RECEIPT_CONSISTENT_UNATTESTED", "DECLARED_RECEIPT_UNRESOLVED"))


@dataclass(frozen=True, slots=True)
class LegalSourceEflawIndependentOriginEvidenceRequirementsInspection:
    """Counts and safe fixed labels ONLY; no provenance credentials or IDs."""

    status: str
    same_provider_signal: str
    official_guide_signal: str
    local_fetch_signal: str
    declared_receipt_signal: str
    temporal_prebinding_status: str
    article_collision_groups: int
    article_collision_member_units: int
    annex_collision_groups: int
    outstanding_requirement_codes: tuple[str, ...]
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("ORIGIN_GAP_DIRECT_RESULT_FORBIDDEN")
        if (self.same_provider_signal not in _CORRESPONDENCE
            or self.official_guide_signal not in _GUIDE
            or self.local_fetch_signal not in _FETCH
            or self.declared_receipt_signal not in _RECEIPT):
            raise ValueError("ORIGIN_GAP_INVALID_SIGNAL")
        if self.temporal_prebinding_status not in (
            _PREBINDING_COLLISIONS, _PREBINDING_STRUCTURE, _PREBINDING_UNATTESTED,
        ):
            raise ValueError("ORIGIN_GAP_INVALID_PREBINDING")
        counts = (
            self.article_collision_groups, self.article_collision_member_units,
            self.annex_collision_groups,
        )
        if (any(type(v) is not int or v < 0 for v in counts)
            or self.article_collision_groups * 2 > self.article_collision_member_units):
            raise ValueError("ORIGIN_GAP_INVALID_COLLISION_COUNTS")
        if self.outstanding_requirement_codes != _REQUIRED:
            raise ValueError("ORIGIN_GAP_INCONSISTENT_REQUIREMENTS")
        expected = (
            COLLISION_BLOCKED if (self.article_collision_groups or self.annex_collision_groups
                                  or self.temporal_prebinding_status == _PREBINDING_COLLISIONS)
            else STRUCTURE_BLOCKED if self.temporal_prebinding_status == _PREBINDING_STRUCTURE
            else UNATTESTED_BLOCKED
        )
        if self.status != expected:
            raise ValueError("ORIGIN_GAP_INCONSISTENT_STATUS")

    def public_record(self) -> dict[str, str | int | bool | list[str]]:
        """Allowlist: NEVER include response bytes, IDs, URLs, times or keys."""
        return {
            "record_kind": "EFLAW_INDEPENDENT_ORIGIN_EVIDENCE_GAP_V1",
            "status": self.status,
            "same_provider_signal": self.same_provider_signal,
            "official_guide_signal": self.official_guide_signal,
            "local_fetch_signal": self.local_fetch_signal,
            "declared_receipt_signal": self.declared_receipt_signal,
            "temporal_prebinding_status": self.temporal_prebinding_status,
            "article_collision_groups": self.article_collision_groups,
            "article_collision_member_units": self.article_collision_member_units,
            "annex_collision_groups": self.annex_collision_groups,
            "outstanding_requirement_codes": list(self.outstanding_requirement_codes),
            "independently_attested_origin_count": 0,
            "same_provider_agreement_is_independent_attestation": False,
            "guide_uri_is_origin_attestation": False,
            "receipt_claim_is_witnessed_acquisition": False,
            "local_http_200_is_origin_attestation": False,
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "canonical_law_version_identity": NOT_EVALUATED,
            "current_legal_validity": NOT_EVALUATED,
            "amendment_and_supplementary_legal_effect": NOT_EVALUATED,
            "article_and_annex_legal_effect": NOT_EVALUATED,
            "parcel_applicability": NOT_EVALUATED,
            "candidate_creation": "NOT_PERFORMED",
            "date_candidate_join": "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY",
            "collision_merging": "FORBIDDEN",
            "rule_engine_admission": "FORBIDDEN",
            "production_admission": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_independent_origin_evidence_requirements(
    correspondence: LegalSourceEflawListDetailLocalCorrespondenceInspection,
    *,
    guide: LegalSourceEflawOfficialGuideEvidenceInspection | None = None,
    local_observation: LegalSourceEflawLocalAcquisitionObservation | None = None,
    receipt_inspection: LegalSourceAcquisitionReceiptInspection | None = None,
) -> LegalSourceEflawIndependentOriginEvidenceRequirementsInspection:
    """Inventory *supplied* unverified signals, NEVER promote them.

    Optional objects are independent diagnostics, NOT proven to refer to the
    same wire request, response or legal version as `correspondence`.
    No ID, URI, digest or raw response member is accessed or emitted.
    """
    if type(correspondence) is not LegalSourceEflawListDetailLocalCorrespondenceInspection:
        raise TypeError("ORIGIN_GAP_INVALID_CORRESPONDENCE")
    if guide is not None and type(guide) is not LegalSourceEflawOfficialGuideEvidenceInspection:
        raise TypeError("ORIGIN_GAP_INVALID_GUIDE")
    if local_observation is not None and type(local_observation) is not LegalSourceEflawLocalAcquisitionObservation:
        raise TypeError("ORIGIN_GAP_INVALID_LOCAL_OBSERVATION")
    if receipt_inspection is not None and type(receipt_inspection) is not LegalSourceAcquisitionReceiptInspection:
        raise TypeError("ORIGIN_GAP_INVALID_RECEIPT_INSPECTION")

    same_provider = (
        "EXACT_TRIPLE_SAME_PROVIDER_UNATTESTED" if correspondence.status == EXACT_ONE
        else "NORMALIZED_ONLY_SAME_PROVIDER_UNATTESTED" if correspondence.status == NORMALIZED_ONLY
        else "SAME_PROVIDER_RELATION_UNRESOLVED"
    )
    guide_signal = (
        "NOT_SUPPLIED" if guide is None else
        "GUIDE_REFERENCE_ONLY" if guide.status == GUIDE_ALIGNED else "GUIDE_UNRESOLVED"
    )
    local_signal = (
        "NOT_SUPPLIED" if local_observation is None else
        "LOCAL_HTTP_200_UNVERIFIED_ORIGIN" if local_observation.status == LOCAL_SUCCESS
        else "LOCAL_FETCH_UNRESOLVED"
    )
    receipt_signal = (
        "NOT_SUPPLIED" if receipt_inspection is None else
        "DECLARED_RECEIPT_CONSISTENT_UNATTESTED"
        if receipt_inspection.status == "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"
        else "DECLARED_RECEIPT_UNRESOLVED"
    )
    prebinding = correspondence.prebinding_status
    collision = bool(correspondence.article_collision_groups or correspondence.annex_collision_groups)
    status = (
        COLLISION_BLOCKED if collision or prebinding == _PREBINDING_COLLISIONS
        else STRUCTURE_BLOCKED if prebinding == _PREBINDING_STRUCTURE
        else UNATTESTED_BLOCKED
    )
    return LegalSourceEflawIndependentOriginEvidenceRequirementsInspection(
        status, same_provider, guide_signal, local_signal, receipt_signal,
        prebinding, correspondence.article_collision_groups,
        correspondence.article_collision_member_units,
        correspondence.annex_collision_groups, _REQUIRED, _seal=_SEAL,
    )
