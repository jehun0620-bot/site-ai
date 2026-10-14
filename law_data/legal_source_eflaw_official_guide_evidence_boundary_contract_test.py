# -*- coding: utf-8 -*-
"""Offline synthetic contract for the OFFICIAL GUIDE REFERENCE ONLY boundary.

No network, actual credential, local files, official source promotion,
current legal validity, or production integration is used or inferred.
"""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_public_request_descriptor import (
    build_legal_source_public_request_descriptor,
)
from law_data.legal_source_eflaw_official_guide_evidence_boundary import (
    ALIGNED, REFERENCE_MISSING, REFERENCE_MISMATCH,
    REQUEST_OUT_OF_SCOPE, REQUEST_SHAPE_MISMATCH,
    GUIDE_URI, GUIDE_REVIEW_DATE, GUIDE_REQUEST_MODE,
    LegalSourceEflawOfficialGuideReference,
    LegalSourceEflawOfficialGuideEvidenceInspection,
    inspect_legal_source_eflaw_official_guide_evidence,
)

SECRET = "SYNTHETIC_OC_SECRET_DO_NOT_EXPOSE"


def reject(call, klass, label):
    try:
        call()
    except klass as exc:
        assert str(exc) == label, "UNEXPECTED_ERROR_LABEL"
        assert SECRET not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def safe(result):
    serialized = json.dumps(result.public_record(), ensure_ascii=True)
    for private in ("OC=", SECRET, "MST=", "efYd=", "lawService.do", "20120106", "121615", "open.law.go.kr"):
        assert private not in serialized and private not in repr(result)
    for field in (
        "guide_capture_authenticity", "guide_currentness",
        "guide_transport_https_provenance", "national_response_mst_field_verified",
        "actual_authenticated_request_observed", "acquisition_authenticity_decision",
        "official_origin_decision", "original_text_identity_decision",
        "source_verification_decision", "current_validity_decision",
        "legal_authority_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert result.public_record()[field] == "NOT_EVALUATED"
    assert result.public_record()["guide_reference_basis"] == "CALLER_SUPPLIED_URL_VS_MANUALLY_REVIEWED_OFFICIAL_GUIDE"


def main():
    total = 0
    request = build_legal_source_public_request_descriptor({
        "target": "eflaw", "type": "JSON", "MST": "121615", "efYd": "20120106",
    })
    other_request = build_legal_source_public_request_descriptor({
        "target": "eflaw", "type": "JSON", "MST": "121615", "efYd": "20120201",
    })
    ordinance = build_legal_source_public_request_descriptor({
        "target": "ordin", "type": "JSON", "MST": "2149501",
    })
    reference = LegalSourceEflawOfficialGuideReference(GUIDE_URI)
    audit = inspect_legal_source_eflaw_official_guide_evidence

    with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), patch(
        "socket.create_connection", side_effect=AssertionError("NO_NETWORK")
    ), patch("builtins.open", side_effect=AssertionError("NO_FILE_IO")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("NO_FILE_IO")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("NO_FILE_IO")):
        for descriptor in (request, other_request):
            result = audit(descriptor, reference)
            assert result.status == ALIGNED
            assert result.guide_reference_check == "MATCH"
            assert result.requested_mode_check == "MATCH"
            assert result.guide_request_fields_check == "MATCH"
            safe(result)
            total += 1

        result = audit(ordinance, reference)
        assert result.status == REQUEST_OUT_OF_SCOPE
        safe(result)
        total += 1

        for value in (None, ""):
            result = audit(request, LegalSourceEflawOfficialGuideReference(value))
            assert result.status == REFERENCE_MISSING
            safe(result)
            total += 1

        bad_references = (
            "https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=lsNwInfoGuide",
            GUIDE_URI + "#fragment",
            GUIDE_URI.replace("open.law.go.kr", "synthetic.example"),
            GUIDE_URI.replace("https:", "http:"),
            GUIDE_URI + "&extra=1",
            GUIDE_URI.replace("lsEfYdInfoGuide", "lsHistory"),
        )
        for value in bad_references:
            result = audit(request, LegalSourceEflawOfficialGuideReference(value))
            assert result.status == REFERENCE_MISMATCH
            safe(result)
            total += 1

        for unsafe in (GUIDE_URI + "&OC=" + SECRET,
                       GUIDE_URI + "&oc=" + SECRET,
                       GUIDE_URI + "\n" + SECRET):
            reject(lambda u=unsafe: LegalSourceEflawOfficialGuideReference(u),
                   ValueError, "UNSAFE_GUIDE_REFERENCE")
            total += 1

        # Endpoint drift must not inherit an approved documentary mapping.
        with patch(
            "law_data.legal_source_eflaw_official_guide_evidence_boundary.ENDPOINT",
            "https://example.invalid/DRF/lawService.do",
        ):
            r = audit(request, reference)
            assert r.status == REQUEST_SHAPE_MISMATCH
            safe(r)
            total += 1

        for desc in (None, "eflaw", {}, True):
            reject(lambda d=desc: audit(d, reference), TypeError, "INVALID_PUBLIC_DESCRIPTOR")
            total += 1
        for ref in (None, GUIDE_URI, {}, False):
            reject(lambda r=ref: audit(request, r), TypeError, "INVALID_GUIDE_REFERENCE")
            total += 1
        for bad in (3, {}, True, [GUIDE_URI]):
            reject(lambda b=bad: LegalSourceEflawOfficialGuideReference(b), ValueError, "INVALID_GUIDE_REFERENCE")
            total += 1

        reject(lambda: LegalSourceEflawOfficialGuideEvidenceInspection(
            ALIGNED, "MATCH", "MATCH", "MATCH"), ValueError,
            "DIRECT_GUIDE_EVIDENCE_RESULT_FORBIDDEN")
        total += 1
        reject(lambda: LegalSourceEflawOfficialGuideEvidenceInspection(
            ALIGNED, "MISMATCH", "MATCH", "MATCH"), ValueError,
            "INCONSISTENT_GUIDE_EVIDENCE_SUCCESS")
        total += 1
        reject(lambda: LegalSourceEflawOfficialGuideEvidenceInspection(
            "SOURCE_VERIFIED", "MATCH", "MATCH", "MATCH"), ValueError,
            "INVALID_GUIDE_EVIDENCE_STATUS")
        total += 1
        reject(lambda: LegalSourceEflawOfficialGuideEvidenceInspection(
            ALIGNED, "MATCH", "MATCH", "UNTRUSTED"), ValueError,
            "INVALID_GUIDE_EVIDENCE_CHECK")
        total += 1
        try:
            result.status = "SOURCE_VERIFIED"
        except (AttributeError, FrozenInstanceError):
            total += 1
        else:
            raise AssertionError("RESULT_MUTABLE")

        assert GUIDE_REQUEST_MODE == "MST_EFYD_JSON"
        assert GUIDE_REVIEW_DATE == "2026-10-14"
        assert result.public_record()["production_admission_decision"] == "NOT_EVALUATED"
        total += 1

        # A caller can supply an exact-looking official guide URL; this does
        # not independently authenticate either this URL or an API response.
        assert audit(request, reference).public_record()["acquisition_authenticity_decision"] == "NOT_EVALUATED"
        total += 1

        # A same-MST request at another efYd has documentary compatibility,
        # not verification of an effective date or legal version.
        assert audit(other_request, reference).public_record()["current_validity_decision"] == "NOT_EVALUATED"
        total += 1

    print("SYNTHETIC_GUIDE_EVIDENCE_CASES:", total)
    print("GUIDE_REFERENCE_EXACT_MATCH_ONLY: True")
    print("DOCUMENTED_MST_EFYD_JSON_MODE_ONLY: True")
    print("GUIDE_URL_NOT_SOURCE_ORIGIN_ATTESTATION: True")
    print("NATIONAL_RESPONSE_MST_NOT_PROMOTED: True")
    print("SOURCE_VERIFIED_PROMOTION_FORBIDDEN: True")
    print("NETWORK_REQUESTS: 0")
    print("REAL_API_KEY_USED: False")
    print("FILES_WRITTEN: 0")
    print("CURRENT_LEGAL_VALIDITY: NOT_EVALUATED")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_OFFICIAL_GUIDE_EVIDENCE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
