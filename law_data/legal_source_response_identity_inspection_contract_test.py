# -*- coding: utf-8 -*-
"""Synthetic/offline checks for bounded MOLEG response identity inspection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_http_integrity_bridge import inspect_legal_source_http_integrity_bridge
from law_data.legal_source_http_safety_boundary import (
    HTTP_REJECTED, SUCCESS, LegalSourceHttpFetchOutcome,
)
from law_data.legal_source_public_request_descriptor import (
    build_legal_source_public_request_descriptor,
)
from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference
from law_data.legal_source_response_identity_inspection import (
    FIELDS_MISMATCH, FIELDS_MISSING, JSON_INVALID, NATIONAL_LIMITED,
    ORDIN_ALIGNED, SHAPE_UNKNOWN, UPSTREAM_UNRESOLVED,
    LegalSourceResponseIdentityInspection, inspect_legal_source_response_identity,
)

SECRET = "SYNTHETIC_PRIVATE_CREDENTIAL_DO_NOT_LOG"
SAMPLES = (
    ("eflaw", "288857", "20260918", "009419", "\uad6d\ud1a0\uc758 \uacc4\ud68d \ubc0f \uc774\uc6a9\uc5d0 \uad00\ud55c \ubc95\ub960 \uc2dc\ud589\ub839", "2026-09-18"),
    ("ordin", "2149501", None, "2000719", "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc \ub3c4\uc2dc\uacc4\ud68d \uc870\ub840", "2026-07-13"),
)


def make_input(case, *, changes=None, raw=None):
    target, mst, efyd, source_id, title, effective = case
    query = {"target": target, "type": "JSON", "MST": mst}
    if efyd is not None:
        query["efYd"] = efyd
    descriptor = build_legal_source_public_request_descriptor(query)
    if raw is None:
        if target == "eflaw":
            doc = {"\ubc95\ub839": {"\uae30\ubcf8\uc815\ubcf4": {
                "\ubc95\ub839ID": source_id,
                "\ubc95\ub839\uba85_\ud55c\uae00": title,
                "\uc2dc\ud589\uc77c\uc790": effective.replace("-", ""),
            }}}
        else:
            doc = {"LawService": {"\uc790\uce58\ubc95\uaddc\uae30\ubcf8\uc815\ubcf4": {
                "\uc790\uce58\ubc95\uaddcID": source_id,
                "\uc790\uce58\ubc95\uaddc\uba85": title,
                "\uc2dc\ud589\uc77c\uc790": effective.replace("-", ""),
                "\uc790\uce58\ubc95\uaddc\uc77c\ub828\ubc88\ud638": mst,
            }}}
        if changes:
            section = doc["\ubc95\ub839"]["\uae30\ubcf8\uc815\ubcf4"] if target == "eflaw" else doc["LawService"]["\uc790\uce58\ubc95\uaddc\uae30\ubcf8\uc815\ubcf4"]
            for key, value in changes.items():
                if value is None:
                    section.pop(key, None)
                else:
                    section[key] = value
        raw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    record = LegalSourceRecord(
        source_system="MOLEG_DRF", source_namespace=target,
        source_id=source_id, title=title, version_id=mst,
        effective_date=effective,
        source_type="NATIONAL_SUBORDINATE" if target == "eflaw" else "LOCAL_ORDINANCE",
        jurisdiction_level="NATIONAL" if target == "eflaw" else "SIDO",
        jurisdiction_code=None if target == "eflaw" else "11",
    )
    ref = LegalSourceVersionEvidenceReference(
        source_system=record.source_system, source_namespace=target,
        source_id=source_id, version_id=mst,
        source_type=record.source_type, jurisdiction_level=record.jurisdiction_level,
        jurisdiction_code=record.jurisdiction_code, evidence_id="SYNTHETIC-" + target,
        evidence_uri="https://synthetic.example/claimed-document",
        declared_sha256=hashlib.sha256(raw).hexdigest(),
    )
    outcome = LegalSourceHttpFetchOutcome(descriptor, SUCCESS, 200, raw)
    return outcome, record, ref


def check(outcome, record, ref, expected, *, fields=None):
    result = inspect_legal_source_response_identity(outcome, record, ref)
    assert type(result) is LegalSourceResponseIdentityInspection
    assert result.status == expected, (result.status, expected)
    doc = result.public_record()
    safe = json.dumps(doc, ensure_ascii=False)
    assert SECRET not in safe and SECRET not in repr(result)
    assert "OC=" not in safe and "synthetic.example" not in safe
    assert "SOURCE-" not in safe and "EVIDENCE-" not in safe
    assert "raw_payload" not in safe and "payload" not in doc
    assert "response_url" not in safe and "requested_url\"" not in safe
    assert doc["record_kind"] == "LEGAL_RESPONSE_IDENTITY_PUBLIC_DIAGNOSTIC_V1"
    assert doc["status"] == expected
    for label in (
        "official_origin_decision", "original_text_identity_decision",
        "current_validity_decision", "legal_authority_decision",
        "legal_applicability_decision", "production_admission_decision",
    ):
        assert doc[label] == "NOT_EVALUATED"
    assert doc["upstream"]["production_admission_decision"] == "NOT_EVALUATED"
    if fields:
        for name, expected_value in fields.items():
            assert doc[name] == expected_value, (name, doc[name], expected_value)
    doc["upstream"]["public_request"]["MST"] = "TAMPERED"
    assert result.public_record()["upstream"]["public_request"]["MST"] == outcome.descriptor.mst
    try:
        result.status = "SOURCE_VERIFIED"  # type: ignore[misc]
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("MUTABLE_RESULT")
    return result


def main():
    total = 0
    # Real upstream SHA256/binding modules are used (not mocked).
    with patch("socket.socket", side_effect=AssertionError("SOCKET_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("SOCKET_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")):
        for case in SAMPLES:
            target, mst, efyd, source_id, title, effective = case
            http, record, reference = make_input(case)
            status = NATIONAL_LIMITED if target == "eflaw" else ORDIN_ALIGNED
            matched = check(http, record, reference, status, fields={
                "source_id_check": "MATCH", "name_check": "MATCH",
                "effective_date_check": "MATCH",
                "response_mst_check": (
                    "NOT_PRESENT_IN_CONFIRMED_NATIONAL_SCHEMA" if target == "eflaw" else "MATCH"
                ),
            })
            assert matched.bridge.inspection is not None
            assert matched.bridge.inspection.digest_matches is True
            assert matched.bridge.inspection.computed_sha256 == reference.declared_sha256
            total += 1

            id_key = "\ubc95\ub839ID" if target == "eflaw" else "\uc790\uce58\ubc95\uaddcID"
            name_key = "\ubc95\ub839\uba85_\ud55c\uae00" if target == "eflaw" else "\uc790\uce58\ubc95\uaddc\uba85"
            mst_key = "\uc790\uce58\ubc95\uaddc\uc77c\ub828\ubc88\ud638"

            for change, expected, flagged in (
                ({id_key: "WRONG_ID"}, FIELDS_MISMATCH, "source_id_check"),
                ({name_key: "WRONG_NAME"}, FIELDS_MISMATCH, "name_check"),
                ({"\uc2dc\ud589\uc77c\uc790": "20250101"}, FIELDS_MISMATCH, "effective_date_check"),
                ({id_key: None}, FIELDS_MISSING, "source_id_check"),
                ({name_key: None}, FIELDS_MISSING, "name_check"),
                ({"\uc2dc\ud589\uc77c\uc790": None}, FIELDS_MISSING, "effective_date_check"),
                ({"\uc2dc\ud589\uc77c\uc790": "20260230"}, FIELDS_MISSING, "effective_date_check"),
                ({id_key: {"content": source_id, "#text": "WRONG_ID"}}, FIELDS_MISSING, "source_id_check"),
            ):
                changed, re, rf = make_input(case, changes=change)
                check(changed, re, rf, expected, fields={flagged: "MISMATCH" if expected == FIELDS_MISMATCH else "MISSING"})
                total += 1

            # Supported single-key API content wrappers are exact; nested or conflicting wrappers fail closed.
            changed, re, rf = make_input(case, changes={id_key: {"content": source_id}, name_key: {"#text": title}})
            check(changed, re, rf, status)
            total += 1

            if target == "ordin":
                for change, expected, flag in (
                    ({mst_key: "9999"}, FIELDS_MISMATCH, "MISMATCH"),
                    ({mst_key: None}, FIELDS_MISSING, "MISSING"),
                    ({mst_key: 2149501}, FIELDS_MISSING, "MISSING"),
                ):
                    changed, re, rf = make_input(case, changes=change)
                    check(changed, re, rf, expected, fields={"response_mst_check": flag})
                    total += 1
            else:
                # No invented national MST verification, even with a plausible unconfirmed field.
                changed, re, rf = make_input(case, changes={"\ubc95\ub839\uc77c\ub828\ubc88\ud638": "WRONG_MST"})
                check(changed, re, rf, NATIONAL_LIMITED, fields={
                    "response_mst_check": "NOT_PRESENT_IN_CONFIRMED_NATIONAL_SCHEMA",
                })
                total += 1
                # efYd is a request selector, not automatically the law's effective date.
                moved = build_legal_source_public_request_descriptor({
                    "target": "eflaw", "type": "JSON", "MST": mst, "efYd": "20261001",
                })
                check(replace(http, descriptor=moved), record, reference, NATIONAL_LIMITED)
                total += 1

            # Valid response JSON but unconfirmed root/basic object is not admitted.
            for bad_doc in ({}, {"unexpected": {}}, {"\ubc95\ub839": []}, {"LawService": []}):
                raw = json.dumps(bad_doc, ensure_ascii=False).encode("utf-8")
                changed, re, rf = make_input(case, raw=raw)
                check(changed, re, rf, SHAPE_UNKNOWN)
                total += 1
            for invalid in (
                b"", b"{invalid json", b"\xff", b"[]", b"null", b'{}{}',
                b'{"a":1,"a":2}', b'{"nested":{"x":1,"x":2}}',
            ):
                changed, re, rf = make_input(case, raw=invalid)
                check(changed, re, rf, UPSTREAM_UNRESOLVED if invalid == b"" else SHAPE_UNKNOWN if invalid in (b"[]", b"null") else JSON_INVALID)
                total += 1

            # A forged declared digest doesn't convert mismatched bytes into a success.
            bad_ref = replace(reference, declared_sha256="f" * 64)
            result = check(http, record, bad_ref, UPSTREAM_UNRESOLVED)
            assert result.bridge.status == "CONTENT_DIGEST_MISMATCH"
            total += 1
            # Wrong declared version is stopped by the existing bridge, before body parsing.
            result = check(http, replace(record, version_id="123"), reference, UPSTREAM_UNRESOLVED)
            assert result.bridge.status == "REQUEST_VERSION_MISMATCH"
            total += 1
            # Missing expected effective date cannot be silently promoted.
            check(http, replace(record, effective_date=None), reference, FIELDS_MISSING,
                  fields={"effective_date_check": "MISSING"})
            total += 1
            # HTTP failures contain no payload to parse and must remain unresolved.
            failed = LegalSourceHttpFetchOutcome(http.descriptor, HTTP_REJECTED, 403, None)
            check(failed, record, reference, UPSTREAM_UNRESOLVED)
            total += 1

        # Direct construction cannot mint arbitrary status text into public records.
        try:
            LegalSourceResponseIdentityInspection(SECRET, matched.bridge)
        except ValueError as exc:
            assert SECRET not in str(exc)
        else:
            raise AssertionError("INVALID_STATUS_ACCEPTED")
        total += 1

    print("TARGETS_TESTED: 2")
    print("SYNTHETIC_RESPONSE_CASES:", total)
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("SOURCE_CODE_CHANGED: False")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_RESPONSE_IDENTITY_INSPECTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
