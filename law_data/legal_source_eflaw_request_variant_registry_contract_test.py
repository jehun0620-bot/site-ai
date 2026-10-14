# -*- coding: utf-8 -*-
"""Synthetic, offline contract for national MST + requested efYd inventory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    LegalSourceEflawRequestVariantRegistry,
    build_legal_source_eflaw_request_variant_registry,
)
from law_data.legal_source_public_request_descriptor import (
    build_legal_source_public_request_descriptor,
)
from law_data.legal_source_registry import (
    LegalSourceRecord,
    LegalSourceVersionConflictError,
    build_legal_source_registry,
)
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
    bind_legal_source_version_evidence,
)

SECRET = "SYNTHETIC_CREDENTIAL_NEVER_LOG"


def create(*, mst="121615", efyd="20120106", evidence_id="EVIDENCE-A",
           source_id="SYNTHETIC-NATIONAL-SOURCE", record_date=None, kind="NATIONAL_SUBORDINATE"):
    descriptor = build_legal_source_public_request_descriptor({
        "target": "eflaw", "type": "JSON", "MST": mst, "efYd": efyd,
    })
    effective_date = record_date if record_date is not None else f"{efyd[:4]}-{efyd[4:6]}-{efyd[6:]}"
    record = LegalSourceRecord(
        source_system="MOLEG_DRF", source_namespace="eflaw", source_id=source_id,
        version_id=mst, effective_date=effective_date, title="Synthetic National Act",
        source_type=kind, jurisdiction_level="NATIONAL",
    )
    reference = LegalSourceVersionEvidenceReference(
        source_system="MOLEG_DRF", source_namespace="eflaw", source_id=source_id,
        version_id=mst, source_type=kind, jurisdiction_level="NATIONAL",
        jurisdiction_code=None, evidence_id=evidence_id,
        evidence_uri="https://synthetic.example/national-document",
        declared_sha256=hashlib.sha256((mst + ":" + efyd).encode()).hexdigest(),
    )
    return LegalSourceEflawRequestVariant(descriptor, record, reference)


def rejects(callback, expected):
    try:
        callback()
    except ValueError as exc:
        assert str(exc) == expected, (str(exc), expected)
        assert SECRET not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION_" + expected)


def check_safe(output):
    serialized = json.dumps(output, ensure_ascii=False)
    for forbidden in (
        SECRET, "SYNTHETIC-NATIONAL-SOURCE", "synthetic.example", "EVIDENCE-A",
        "121615", "20120106", "SOURCE_VERIFIED", "OC=",
    ):
        assert forbidden not in serialized
    for field in (
        "source_verification_decision", "current_validity_decision",
        "legal_authority_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert output[field] == "NOT_EVALUATED"


def main():
    cases = 0
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")):
        for mst, first_date, second_date in (
            ("121615", "20120106", "20120201"),
            ("149889", "20140117", "20140814"),
        ):
            first = create(mst=mst, efyd=first_date, evidence_id="EVIDENCE-A")
            second = create(mst=mst, efyd=second_date, evidence_id="EVIDENCE-B")
            assert first.record.version_key == second.record.version_key
            assert first.variant_key != second.variant_key
            assert first.reference.declared_sha256 != second.reference.declared_sha256
            assert first.record.version_id == mst == second.reference.version_id
            candidates = build_legal_source_eflaw_request_variant_registry([first, second, first])
            assert len(candidates.variants) == 2
            assert candidates.variant_exact(*first.variant_key) is first
            assert candidates.variant_exact(*second.variant_key) is second
            assert candidates.variant_exact(*first.variant_key[:-1], "19990101") is None
            assert len(candidates.variants_for(*first.record.source_key)) == 2
            check_safe(first.public_record())
            check_safe(candidates.public_record())
            assert "EVIDENCE-A" not in repr(first) and SECRET not in repr(candidates)
            assert first.public_record()["requested_efyd_vs_declared_effective_date"] == "MATCH_DECLARED_UNVERIFIED"
            cases += 1

            # This is the documented legacy limit. New inventory intentionally
            # DOES NOT change the original registry or its MST-only contract.
            try:
                build_legal_source_registry([first.record, second.record])
            except LegalSourceVersionConflictError:
                pass
            else:
                raise AssertionError("LEGACY_REGISTRY_UNEXPECTED_ACCEPTANCE")
            cases += 1

            # Old evidence-ID collision detection sees only (source, MST);
            # the new request inventory must reject reuse across distinct efYd.
            reused = LegalSourceEflawRequestVariant(
                second.descriptor, second.record,
                replace(second.reference, evidence_id=first.reference.evidence_id),
            )
            assert bind_legal_source_version_evidence(
                reused.record, reused.reference, known_references=(first.reference,)
            ).status == "IDENTITY_ALIGNED_UNVERIFIED"
            rejects(lambda: build_legal_source_eflaw_request_variant_registry([first, reused]),
                    "EVIDENCE_ID_REUSED_ACROSS_REQUEST_VARIANTS")
            cases += 1

            different_claim = LegalSourceEflawRequestVariant(
                first.descriptor, first.record,
                replace(first.reference, declared_sha256="f" * 64),
            )
            rejects(lambda: build_legal_source_eflaw_request_variant_registry(
                [first, different_claim]), "REQUEST_VARIANT_COLLISION")
            cases += 1

            # The request date is NOT proof of the record's legal effective date.
            different_date = create(
                mst=mst, efyd=first_date, record_date="2000-01-01",
                evidence_id="EVIDENCE-C",
            )
            assert different_date.public_record()[
                "requested_efyd_vs_declared_effective_date"
            ] == "MISMATCH_DECLARED_UNVERIFIED"
            cases += 1

            # No independent data or current law is selected automatically.
            empty = LegalSourceEflawRequestVariantRegistry()
            assert empty.variant_exact(*first.variant_key) is None
            check_safe(empty.public_record())
            cases += 1

        first = create()
        invalid = (
            (lambda: LegalSourceEflawRequestVariant(object(), first.record, first.reference),
             "INVALID_VARIANT_DESCRIPTOR"),
            (lambda: LegalSourceEflawRequestVariant(first.descriptor, object(), first.reference),
             "INVALID_VARIANT_RECORD"),
            (lambda: LegalSourceEflawRequestVariant(first.descriptor, first.record, object()),
             "INVALID_VARIANT_REFERENCE"),
            (lambda: LegalSourceEflawRequestVariant(
                first.descriptor, replace(first.record, version_id="999"), first.reference),
             "MST_REQUEST_MISMATCH"),
            (lambda: LegalSourceEflawRequestVariant(
                first.descriptor, replace(first.record, source_namespace="ordin"), first.reference),
             "INVALID_EFLAW_SCOPE"),
            (lambda: LegalSourceEflawRequestVariant(
                first.descriptor, first.record, replace(first.reference, source_id="OTHER")),
             "EVIDENCE_BINDING_UNRESOLVED"),
            (lambda: LegalSourceEflawRequestVariant(
                first.descriptor, first.record, replace(first.reference, evidence_uri=None)),
             "EVIDENCE_BINDING_UNRESOLVED"),
            (lambda: LegalSourceEflawRequestVariant(
                first.descriptor, first.record, replace(first.reference, declared_sha256=None)),
             "EVIDENCE_BINDING_UNRESOLVED"),
            (lambda: build_legal_source_eflaw_request_variant_registry([object()]),
             "INVALID_VARIANT_ITEM"),
            (lambda: build_legal_source_eflaw_request_variant_registry("invalid"),
             "INVALID_VARIANT_COLLECTION"),
        )
        for call, expected in invalid:
            rejects(call, expected)
            cases += 1

        # Local ordinance is intentionally excluded: no change to ordin paths.
        ordin = build_legal_source_public_request_descriptor({
            "target": "ordin", "type": "JSON", "MST": "2149501",
        })
        rejects(lambda: LegalSourceEflawRequestVariant(ordin, first.record, first.reference),
                "EFLAW_ONLY")
        cases += 1

        same_source_different_scope = create(efyd="20120201", kind="NATIONAL_LAW",
                                             evidence_id="EVIDENCE-B")
        rejects(lambda: build_legal_source_eflaw_request_variant_registry(
            [first, same_source_different_scope]), "SOURCE_SCOPE_COLLISION")
        cases += 1

        different_mst = create(mst="149889", efyd="20140117", evidence_id="EVIDENCE-A")
        rejects(lambda: build_legal_source_eflaw_request_variant_registry(
            [first, different_mst]), "EVIDENCE_ID_REUSED_ACROSS_REQUEST_VARIANTS")
        cases += 1

        try:
            first.record = object()  # type: ignore[misc]
        except (FrozenInstanceError, AttributeError):
            cases += 1
        else:
            raise AssertionError("MUTABLE_VARIANT")

    print("TARGETS_TESTED: 1")
    print("SYNTHETIC_EFLAW_VARIANT_CASES:", cases)
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("SOURCE_CODE_CHANGED: False")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_REQUEST_VARIANT_REGISTRY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
