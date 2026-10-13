# -*- coding: utf-8 -*-
"""Offline contract for MOLEG HTTP result -> exact version/payload inspection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_http_safety_boundary import (
    HTTP_REJECTED, REDIRECT_BLOCKED, SUCCESS, TIMEOUT, TLS_FAILED,
    TRANSPORT_FAILED, LegalSourceHttpFetchOutcome,
)
from law_data.legal_source_http_integrity_bridge import (
    HTTP_UNRESOLVED, INSPECTION_FAILED, REQUEST_SCOPE_MISMATCH,
    REQUEST_SOURCE_MISMATCH, REQUEST_VERSION_MISMATCH,
    LegalSourceHttpIntegrityBridgeResult,
    inspect_legal_source_http_integrity_bridge,
)
from law_data.legal_source_public_request_descriptor import (
    build_legal_source_public_request_descriptor,
)
from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
)

SECRET = "SYNTHETIC_CREDENTIAL_NEVER_LOG"
PAYLOAD = b"\x00\xff Synthetic official-looking bytes \r\n" + SECRET.encode("ascii")
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
CASES = (
    ("eflaw", "288857", "20260918", "NATIONAL_SUBORDINATE", "NATIONAL", None),
    ("ordin", "2149501", None, "LOCAL_ORDINANCE", "SIDO", "11"),
)


def fixtures(case):
    target, mst, efyd, source_type, level, code = case
    criteria = {"target": target, "type": "JSON", "MST": mst}
    if efyd is not None:
        criteria["efYd"] = efyd
    desc = build_legal_source_public_request_descriptor(criteria)
    record_fields = dict(
        source_system="MOLEG_DRF", source_namespace=target,
        source_id="SOURCE-" + target, version_id=mst,
        title="Synthetic evidence only", source_type=source_type,
        jurisdiction_level=level, jurisdiction_code=code,
        source_uri="https://synthetic.example/index",
    )
    reference_fields = dict(
        source_system="MOLEG_DRF", source_namespace=target,
        source_id="SOURCE-" + target, version_id=mst,
        source_type=source_type, jurisdiction_level=level, jurisdiction_code=code,
        evidence_id="EVIDENCE-" + target,
        evidence_uri="https://synthetic.example/claimed-document",
        declared_sha256=DIGEST.upper(),
    )
    return desc, record_fields, reference_fields


def newrecord(fields, **changes):
    return LegalSourceRecord(**{**fields, **changes})


def newref(fields, **changes):
    return LegalSourceVersionEvidenceReference(**{**fields, **changes})


def outcome(desc, status=SUCCESS, payload=PAYLOAD, http_status=200):
    return LegalSourceHttpFetchOutcome(
        descriptor=desc, status=status, http_status=http_status, payload=payload,
    )


def assert_safe(result, expected_status, *, has_inspection=False):
    assert type(result) is LegalSourceHttpIntegrityBridgeResult
    assert result.status == expected_status, (result.status, expected_status)
    assert (result.inspection is not None) is has_inspection
    public = result.public_record()
    text = json.dumps(public, ensure_ascii=False)
    assert SECRET not in text and SECRET not in repr(result)
    assert "OC=" not in text and "OC=" not in repr(result)
    assert "synthetic.example" not in text
    assert "SOURCE-" not in text and "EVIDENCE-" not in text
    assert "payload" not in public and "inspection" not in public
    assert "response_url" not in public and "requested_url" not in public
    assert "exception" not in public and "headers" not in public
    assert public["status"] == expected_status
    assert public["http_acquisition_basis"] == "CALLER_SUPPLIED_OUTCOME_UNVERIFIED"
    assert public["evidence_basis"] == "CALLER_SUPPLIED_REFERENCE_AND_DIGEST"
    for name in (
        "requested_url_identity", "official_origin_decision",
        "original_text_identity_decision", "source_verification_decision",
        "current_validity_decision", "legal_authority_decision",
        "legal_applicability_decision", "production_admission_decision",
    ):
        assert public[name] == "NOT_EVALUATED"
    original_mst = result.http_outcome.descriptor.mst
    public["public_request"]["MST"] = "TAMPERED"
    assert result.public_record()["public_request"]["MST"] == original_mst
    try:
        result.status = "SOURCE_VERIFIED"  # type: ignore[misc]
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("MUTABLE_BRIDGE_RESULT")


def main():
    scenario_count = 0
    # The inspector uses only caller-provided bytes. No real HTTP, .env or disk.
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("DISK_ACCESS_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("DISK_ACCESS_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("DISK_ACCESS_FORBIDDEN")):
        for case in CASES:
            desc, rf, ef = fixtures(case)
            record, reference = newrecord(rf), newref(ef)
            received = outcome(desc)
            # Byte equality to a declared digest is not official provenance.
            matched = inspect_legal_source_http_integrity_bridge(received, record, reference)
            assert_safe(matched, "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN", has_inspection=True)
            assert matched.inspection.digest_matches is True
            assert matched.inspection.computed_sha256 == DIGEST
            assert matched.inspection.payload_byte_count == len(PAYLOAD)
            assert matched.public_record()["response_byte_count"] == len(PAYLOAD)
            assert matched.public_record()["digest_matches"] is True
            assert matched.http_outcome.payload == PAYLOAD
            scenario_count += 1

            # A changed byte or a different declared digest must fail.
            for mismatch in (
                inspect_legal_source_http_integrity_bridge(
                    outcome(desc, payload=PAYLOAD + b"\n"), record, reference
                ),
                inspect_legal_source_http_integrity_bridge(
                    received, record, newref(ef, declared_sha256="f" * 64)
                ),
            ):
                assert_safe(mismatch, "CONTENT_DIGEST_MISMATCH", has_inspection=True)
                assert mismatch.inspection.digest_matches is False
                scenario_count += 1

            empty = inspect_legal_source_http_integrity_bridge(
                outcome(desc, payload=b""), record, reference,
            )
            assert_safe(empty, "PAYLOAD_MISSING", has_inspection=True)
            assert empty.inspection.computed_sha256 is None
            scenario_count += 1

            # Even a valid content hash cannot bypass declared evidence binding.
            for changes in (
                {"source_id": "DIFFERENT"},
                {"source_namespace": "ordin" if desc.target == "eflaw" else "eflaw"},
                {"version_id": "777777"},
                {"evidence_uri": None},
                {"declared_sha256": None},
            ):
                blocked = inspect_legal_source_http_integrity_bridge(
                    received, record, newref(ef, **changes)
                )
                assert_safe(blocked, "EVIDENCE_BINDING_REJECTED", has_inspection=True)
                assert blocked.inspection.digest_matches is None
                assert blocked.inspection.computed_sha256 is None
                scenario_count += 1

            # Same evidence ID on a different version is a collision.
            ref2 = newref(ef, version_id="777777")
            blocked = inspect_legal_source_http_integrity_bridge(
                received, record, reference, known_references=(ref2,)
            )
            assert_safe(blocked, "EVIDENCE_BINDING_REJECTED", has_inspection=True)
            scenario_count += 1

            # A request for a different namespace/version cannot borrow the bytes.
            for bad_record, expected in (
                (newrecord(rf, source_system="SYNTHETIC"), REQUEST_SOURCE_MISMATCH),
                (newrecord(rf, source_namespace="ordin" if desc.target == "eflaw" else "eflaw"), REQUEST_SOURCE_MISMATCH),
                (newrecord(rf, version_id="777777"), REQUEST_VERSION_MISMATCH),
                (newrecord(rf, version_id=None), REQUEST_VERSION_MISMATCH),
            ):
                blocked = inspect_legal_source_http_integrity_bridge(
                    received, bad_record, reference
                )
                assert_safe(blocked, expected)
                scenario_count += 1

            # Scope violation cannot be masked by a matching digest.
            if desc.target == "eflaw":
                bad_scope = newrecord(
                    rf, source_type="LOCAL_ORDINANCE",
                    jurisdiction_level="SIDO", jurisdiction_code="11",
                )
            else:
                bad_scope = newrecord(
                    rf, source_type="NATIONAL_SUBORDINATE",
                    jurisdiction_level="NATIONAL", jurisdiction_code=None,
                )
            blocked = inspect_legal_source_http_integrity_bridge(
                received, bad_scope, reference
            )
            assert_safe(blocked, REQUEST_SCOPE_MISMATCH)
            scenario_count += 1

            # All failed HTTP statuses (including redirects) must not be hashed.
            for http_status, code in (
                (HTTP_REJECTED, 403), (HTTP_REJECTED, 500),
                (REDIRECT_BLOCKED, 302), (TIMEOUT, None),
                (TLS_FAILED, None), (TRANSPORT_FAILED, None),
            ):
                bad_outcome = outcome(desc, status=http_status, payload=None, http_status=code)
                with patch(
                    "law_data.legal_source_http_integrity_bridge.inspect_legal_source_original_payload_integrity",
                    side_effect=AssertionError("INSPECTION_MUST_NOT_RUN"),
                ):
                    result = inspect_legal_source_http_integrity_bridge(
                        bad_outcome, record, reference
                    )
                assert_safe(result, HTTP_UNRESOLVED)
                assert result.public_record()["digest_matches"] is None
                scenario_count += 1

            # An inspector failure is reported with no chained/raw exception.
            with patch(
                "law_data.legal_source_http_integrity_bridge.inspect_legal_source_original_payload_integrity",
                side_effect=RuntimeError("secret=" + SECRET),
            ):
                result = inspect_legal_source_http_integrity_bridge(
                    received, record, reference
                )
            assert_safe(result, INSPECTION_FAILED)
            scenario_count += 1

            # Direct callers cannot create a forged public diagnostic status.
            for arguments in (
                {"status": SECRET, "http_outcome": received},
                {"status": "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN", "http_outcome": received},
                {"status": HTTP_UNRESOLVED, "http_outcome": received, "inspection": matched.inspection},
                {"status": "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN", "http_outcome": received,
                 "inspection": replace(matched.inspection, binding_status=SECRET)},
                {"status": "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN", "http_outcome": received,
                 "inspection": replace(matched.inspection, payload_byte_count=SECRET)},
            ):
                try:
                    LegalSourceHttpIntegrityBridgeResult(**arguments)
                except ValueError as exc:
                    assert SECRET not in str(exc)
                else:
                    raise AssertionError("FORGED_PUBLIC_BRIDGE_ACCEPTED")
                scenario_count += 1

            # Wrong parameter types fail closed with non-reflecting codes.
            for args, kw, message in (
                ((object(), record, reference), {}, "INVALID_HTTP_OUTCOME"),
                ((received, {}, reference), {}, "INVALID_SOURCE_RECORD"),
                ((received, record, {}), {}, "INVALID_EVIDENCE_REFERENCE"),
                ((received, record, reference), {"known_references": [reference]}, "INVALID_KNOWN_REFERENCES"),
                ((received, record, reference), {"known_references": (object(),)}, "INVALID_KNOWN_REFERENCES"),
            ):
                try:
                    inspect_legal_source_http_integrity_bridge(*args, **kw)
                except TypeError as exc:
                    assert str(exc) == message and SECRET not in repr(exc)
                else:
                    raise AssertionError("INVALID_INPUT_ACCEPTED")
                scenario_count += 1

    print("TARGETS_TESTED: 2")
    print("SYNTHETIC_BRIDGE_CASES:", scenario_count)
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("SOURCE_CODE_CHANGED: False")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_HTTP_INTEGRITY_BRIDGE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
