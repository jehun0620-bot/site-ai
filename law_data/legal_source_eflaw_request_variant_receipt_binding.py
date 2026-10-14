# -*- coding: ascii -*-
"""Offline eflaw variant / HTTP / DECLARED receipt locator relation.

This checks only CALLER-SUPPLIED, credential-free public descriptor URL claims.
The public descriptor URL is NOT the actual OC-authenticated request URL.
Never pass a credential-bearing URL here: mismatches are rejected without
logging/reprinting URL, source identity, evidence ID, original bytes or digest.
No proof of an acquisition, source origin, legal validity, or SITE admission.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from law_data.legal_source_acquisition_receipt_inspection import (
    LegalSourceAcquisitionReceipt,
    inspect_legal_source_acquisition_receipt,
)
from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    LegalSourceEflawRequestVariantRegistry,
)
from law_data.legal_source_eflaw_request_variant_http_binding import (
    BOUND,
    inspect_legal_source_eflaw_request_variant_http_binding,
)
from law_data.legal_source_http_safety_boundary import LegalSourceHttpFetchOutcome
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference

NOT_EVALUATED = "NOT_EVALUATED"
ALIGNED = "EFLAW_VARIANT_DECLARED_RECEIPT_ALIGNED_UNVERIFIED_ORIGIN"
NOT_REGISTERED = "RECEIPT_VARIANT_NOT_REGISTERED"
DESCRIPTOR_MISMATCH = "RECEIPT_HTTP_DESCRIPTOR_MISMATCH"
LOCATOR_MISSING = "RECEIPT_PUBLIC_LOCATOR_MISSING"
LOCATOR_MISMATCH = "RECEIPT_PUBLIC_LOCATOR_MISMATCH"
HTTP_UNRESOLVED = "RECEIPT_VARIANT_HTTP_BINDING_UNRESOLVED"
RECEIPT_UNRESOLVED = "RECEIPT_CLAIM_CONSISTENCY_UNRESOLVED"
INSPECTION_FAILED = "RECEIPT_RELATION_INSPECTION_FAILED"
_STATUSES = frozenset((
    ALIGNED, NOT_REGISTERED, DESCRIPTOR_MISMATCH, LOCATOR_MISSING,
    LOCATOR_MISMATCH, HTTP_UNRESOLVED, RECEIPT_UNRESOLVED, INSPECTION_FAILED,
))
_SEAL = object()


@dataclass(frozen=True, slots=True)
class LegalSourceEflawRequestVariantReceiptBinding:
    """Only fixed, non-sensitive diagnostics; NOT observed acquisition evidence."""
    status: str
    descriptor_check: str
    public_locator_check: str
    http_binding_check: str
    receipt_claim_check: str
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in _STATUSES:
            raise ValueError("INVALID_RECEIPT_VARIANT_STATUS")
        for field_name in ("descriptor_check", "public_locator_check",
                           "http_binding_check", "receipt_claim_check"):
            if getattr(self, field_name) not in ("MATCH", "MISMATCH", "MISSING", "UNRESOLVED", NOT_EVALUATED):
                raise ValueError("INVALID_RECEIPT_VARIANT_CHECK")
        if self.status == ALIGNED and (
            self.descriptor_check != "MATCH"
            or self.public_locator_check != "MATCH"
            or self.http_binding_check != "MATCH"
            or self.receipt_claim_check != "MATCH"
        ):
            raise ValueError("INCONSISTENT_RECEIPT_VARIANT_SUCCESS")
        if self._seal is not _SEAL:
            raise ValueError("DIRECT_RECEIPT_VARIANT_RESULT_FORBIDDEN")

    def public_record(self) -> dict[str, str]:
        """Never include raw receipt, reference, original response or URLs."""
        return {
            "record_kind": "LEGAL_EFLAW_REQUEST_VARIANT_RECEIPT_RELATION_V1",
            "status": self.status,
            "descriptor_check": self.descriptor_check,
            "public_locator_check": self.public_locator_check,
            "http_binding_check": self.http_binding_check,
            "receipt_claim_check": self.receipt_claim_check,
            "locator_basis": "EXACT_CREDENTIAL_FREE_CALLER_CLAIM_NOT_WITNESSED_HTTP_URL",
            "receipt_basis": "CALLER_SUPPLIED_UNATTESTED",
            "acquisition_authenticity_decision": NOT_EVALUATED,
            "official_origin_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "source_verification_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def inspect_legal_source_eflaw_request_variant_receipt_binding(
    registry: LegalSourceEflawRequestVariantRegistry,
    variant: LegalSourceEflawRequestVariant,
    http_outcome: LegalSourceHttpFetchOutcome,
    receipt: LegalSourceAcquisitionReceipt,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceEflawRequestVariantReceiptBinding:
    """Fail closed when a CLAIMED receipt locator differs from registered efYd.

    Exact URL equality intentionally disallows credentials, reordered query
    params, extra params, encoded aliases, fragments and duplicate keys. This
    accepts only the descriptor's public (credential-free) canonical locator.
    That URL is NOT an observation of the authenticated outgoing request.
    """
    if type(registry) is not LegalSourceEflawRequestVariantRegistry:
        raise TypeError("INVALID_VARIANT_REGISTRY")
    if type(variant) is not LegalSourceEflawRequestVariant:
        raise TypeError("INVALID_VARIANT")
    if type(http_outcome) is not LegalSourceHttpFetchOutcome:
        raise TypeError("INVALID_HTTP_OUTCOME")
    if type(receipt) is not LegalSourceAcquisitionReceipt:
        raise TypeError("INVALID_CLAIMED_RECEIPT")
    if type(known_references) is not tuple or any(
        type(x) is not LegalSourceVersionEvidenceReference for x in known_references
    ):
        raise TypeError("INVALID_KNOWN_REFERENCES")

    def result(status: str, desc: str = NOT_EVALUATED,
               locator: str = NOT_EVALUATED, http: str = NOT_EVALUATED,
               claim: str = NOT_EVALUATED) -> LegalSourceEflawRequestVariantReceiptBinding:
        return LegalSourceEflawRequestVariantReceiptBinding(
            status, desc, locator, http, claim, _seal=_SEAL,
        )

    if registry.variant_exact(*variant.variant_key) is not variant:
        return result(NOT_REGISTERED)
    if http_outcome.descriptor != variant.descriptor:
        return result(DESCRIPTOR_MISMATCH, "MISMATCH")

    # These are claimed *public* locators. The authenticated actual URL,
    # which contains OC, must NEVER be serialized into a receipt here.
    expected = variant.descriptor.public_descriptor_url()
    if receipt.requested_url is None or receipt.final_url is None or variant.reference.evidence_uri is None:
        return result(LOCATOR_MISSING, "MATCH", "MISSING")
    if (receipt.requested_url != expected or receipt.final_url != expected
            or variant.reference.evidence_uri != expected):
        return result(LOCATOR_MISMATCH, "MATCH", "MISMATCH")

    inventory_refs = tuple(x.reference for x in registry.variants if x is not variant)
    all_other_refs = inventory_refs + known_references
    try:
        bound = inspect_legal_source_eflaw_request_variant_http_binding(
            registry, variant, http_outcome, known_references=known_references,
        )
        if bound.status != BOUND:
            return result(HTTP_UNRESOLVED, "MATCH", "MATCH", "UNRESOLVED")
        inspected = inspect_legal_source_acquisition_receipt(
            variant.record, variant.reference, http_outcome.payload, receipt,
            known_references=all_other_refs,
        )
    except Exception:
        # Never expose a caller-supplied exception containing OC or raw URLs.
        return result(INSPECTION_FAILED, "MATCH", "MATCH", "UNRESOLVED")

    if inspected.status != "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN":
        return result(RECEIPT_UNRESOLVED, "MATCH", "MATCH", "MATCH", "UNRESOLVED")
    return result(ALIGNED, "MATCH", "MATCH", "MATCH", "MATCH")
