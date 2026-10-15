# -*- coding: utf-8 -*-
"""Offline synthetic contract: even combined 'good' evidence remains blocked."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_public_request_descriptor import LegalSourcePublicRequestDescriptor
from law_data.legal_source_eflaw_list_detail_local_correspondence import (
    inspect_legal_source_eflaw_list_detail_local_correspondence,
)
from law_data.legal_source_eflaw_official_guide_evidence_boundary import (
    GUIDE_URI, LegalSourceEflawOfficialGuideReference,
    inspect_legal_source_eflaw_official_guide_evidence,
)
from law_data.legal_source_acquisition_receipt_inspection import LegalSourceAcquisitionReceiptInspection
from law_data.legal_source_http_safety_boundary import (
    HTTP_REJECTED, SUCCESS, LegalSourceHttpFetchOutcome,
)
from law_data.legal_source_eflaw_local_acquisition_observation import (
    fetch_legal_source_eflaw_with_local_observation,
)
from law_data.legal_source_eflaw_independent_origin_evidence_requirements import (
    COLLISION_BLOCKED, STRUCTURE_BLOCKED, UNATTESTED_BLOCKED,
    LegalSourceEflawIndependentOriginEvidenceRequirementsInspection as Inspection,
    inspect_legal_source_eflaw_independent_origin_evidence_requirements as inspect,
)

PRIVATE = "PRIVATE_SOURCE_BODY_NEVER_PRINT"


def _payload(*, collisions: bool = False, structure: bool = False) -> bytes:
    articles = [{
        "조문번호": "1", "조문가지번호": "0", "조문키": "K1",
        "조문시행일자": "20120106", "조문내용": PRIVATE,
    }]
    if collisions:
        articles = [
            {**articles[0], "조문내용": PRIVATE},
            {**articles[0], "조문내용": "DIFFERENT_PRIVATE_BODY"},
            {**articles[0], "조문번호": "2", "조문키": "K2"},
            {**articles[0], "조문번호": "2", "조문키": "K2", "조문내용": "ALSO_DIFFERENT"},
        ]
    if structure:
        articles[0].pop("조문시행일자")
    root = {
        "법령": {
            "기본정보": {"법령ID": "001234", "법령명_한글": PRIVATE, "시행일자": "20120106"},
            "조문": {"조문단위": articles},
            "별표": {"별표단위": [{"별표번호": "1", "별표가지번호": "0", "별표시행일자": "20120106"}]},
            "부칙": {"부칙단위": [{"부칙내용": [PRIVATE]}]},
        }
    }
    return json.dumps(root, ensure_ascii=False).encode("utf-8")


def _listing(*, mode: str = "exact") -> bytes:
    sample = {"법령ID": "001234", "법령일련번호": "121615", "시행일자": "20120106"}
    if mode == "normalized":
        sample["법령일련번호"] = 121615
    elif mode == "missing":
        sample["법령일련번호"] = "999999"
    elif mode == "duplicate":
        return json.dumps({"LawSearch": {"law": [sample, dict(sample)]}}, ensure_ascii=False).encode("utf-8")
    return json.dumps({"LawSearch": {"law": sample}}, ensure_ascii=False).encode("utf-8")


def _receipt(status: str) -> LegalSourceAcquisitionReceiptInspection:
    # This is deliberately caller-constructible; NO independent attestation.
    key = ("MOLEG_DRF", "eflaw", "PRIVATE_RECORD", "121615")
    return LegalSourceAcquisitionReceiptInspection(
        status=status,
        integrity_status="CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN",
        binding_status="IDENTITY_ALIGNED_UNVERIFIED",
        version_key=key, receipt_version_key=key,
        evidence_key=("MOLEG_DRF", "eflaw", "PRIVATE_EVIDENCE"),
        receipt_identity_aligned=True,
        receipt_byte_count_matches=True, receipt_digest_matches=True,
        missing_receipt_fields=(), url_relation="UNCHANGED_DECLARED",
    )


def _safe(obj: Inspection) -> None:
    record = obj.public_record()
    body = json.dumps(record, ensure_ascii=False) + repr(obj)
    for secret in (PRIVATE, "PRIVATE_RECORD", "PRIVATE_EVIDENCE", "001234", "121615",
                   "20120106", "OC=", "https://", "law.go.kr", "법령ID", "조문내용"):
        assert secret not in body, "ORIGIN_GAP_PRIVATE_VALUE_LEAK"
    assert record["independently_attested_origin_count"] == 0
    for field in (
        "acquisition_authenticity_decision", "official_origin_decision",
        "original_text_identity_decision", "canonical_law_version_identity",
        "current_legal_validity", "amendment_and_supplementary_legal_effect",
        "article_and_annex_legal_effect", "parcel_applicability", "production_admission",
    ):
        assert record[field] == "NOT_EVALUATED"
    assert record["candidate_creation"] == "NOT_PERFORMED"
    assert record["date_candidate_join"] == "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY"
    assert record["collision_merging"] == "FORBIDDEN"
    assert record["rule_engine_admission"] == "FORBIDDEN"
    assert all(not record[field] for field in (
        "same_provider_agreement_is_independent_attestation",
        "guide_uri_is_origin_attestation", "receipt_claim_is_witnessed_acquisition",
        "local_http_200_is_origin_attestation",
    ))
    assert len(record["outstanding_requirement_codes"]) == 11
    assert len(set(record["outstanding_requirement_codes"])) == 11


def _reject(action, expected: str) -> None:
    try:
        action()
    except (TypeError, ValueError) as exc:
        assert str(exc) == expected, "UNEXPECTED_ERROR_CODE"
        assert PRIVATE not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def main() -> None:
    checks = 0
    d = LegalSourcePublicRequestDescriptor("eflaw", "121615", "20120106")
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("DISK_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("DISK_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("DISK_IO_FORBIDDEN")):
        corr = inspect_legal_source_eflaw_list_detail_local_correspondence(_payload(), _listing(), d)
        base = inspect(corr)
        assert base.status == UNATTESTED_BLOCKED
        assert base.same_provider_signal == "EXACT_TRIPLE_SAME_PROVIDER_UNATTESTED"
        assert base.official_guide_signal == base.local_fetch_signal == base.declared_receipt_signal == "NOT_SUPPLIED"
        _safe(base)
        checks += 1

        guide = inspect_legal_source_eflaw_official_guide_evidence(
            d, LegalSourceEflawOfficialGuideReference(GUIDE_URI),
        )
        claim = _receipt("RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN")
        outcome = LegalSourceHttpFetchOutcome(d, SUCCESS, http_status=200, payload=_payload())
        with patch("law_data.legal_source_eflaw_local_acquisition_observation.fetch_legal_source_http",
                   return_value=outcome) as fake_fetch, patch(
            "law_data.legal_source_eflaw_local_acquisition_observation._utc_iso",
            side_effect=("2026-10-15T00:00:01.000000Z", "2026-10-15T00:00:02.000000Z")
        ), patch("law_data.legal_source_eflaw_local_acquisition_observation.uuid4") as fake_uuid:
            fake_uuid.return_value.hex = "0" * 32
            observed = fetch_legal_source_eflaw_with_local_observation(d, "SYNTHETIC", enabled=True)
            assert fake_fetch.call_count == 1
        all_claims = inspect(corr, guide=guide, local_observation=observed, receipt_inspection=claim)
        assert all_claims.status == UNATTESTED_BLOCKED
        assert all_claims.official_guide_signal == "GUIDE_REFERENCE_ONLY"
        assert all_claims.local_fetch_signal == "LOCAL_HTTP_200_UNVERIFIED_ORIGIN"
        assert all_claims.declared_receipt_signal == "DECLARED_RECEIPT_CONSISTENT_UNATTESTED"
        _safe(all_claims)
        checks += 1

        # Every supplied claim is still NON-ATTESTED.
        for mode, signal in (
            ("normalized", "NORMALIZED_ONLY_SAME_PROVIDER_UNATTESTED"),
            ("missing", "SAME_PROVIDER_RELATION_UNRESOLVED"),
            ("duplicate", "SAME_PROVIDER_RELATION_UNRESOLVED"),
        ):
            c = inspect_legal_source_eflaw_list_detail_local_correspondence(_payload(), _listing(mode=mode), d)
            r = inspect(c, guide=guide, local_observation=observed, receipt_inspection=claim)
            assert r.same_provider_signal == signal and r.status == UNATTESTED_BLOCKED
            _safe(r)
            checks += 1

        for detail, expected_status in ((_payload(collisions=True), COLLISION_BLOCKED),
                                        (_payload(structure=True), STRUCTURE_BLOCKED)):
            c = inspect_legal_source_eflaw_list_detail_local_correspondence(detail, _listing(), d)
            r = inspect(c, guide=guide, local_observation=observed, receipt_inspection=claim)
            assert r.status == expected_status
            if expected_status == COLLISION_BLOCKED:
                assert (r.article_collision_groups, r.article_collision_member_units) == (2, 4)
            _safe(r)
            checks += 1

        bad_guide = inspect_legal_source_eflaw_official_guide_evidence(
            d, LegalSourceEflawOfficialGuideReference(None),
        )
        r = inspect(corr, guide=bad_guide)
        assert r.official_guide_signal == "GUIDE_UNRESOLVED"
        _safe(r)
        checks += 1

        for receipt in (
            _receipt("RECEIPT_DIGEST_MISMATCH"),
            _receipt("SOURCE_VERIFIED"),  # A forged caller status cannot promote.
        ):
            r = inspect(corr, receipt_inspection=receipt)
            assert r.declared_receipt_signal == "DECLARED_RECEIPT_UNRESOLVED"
            _safe(r)
            checks += 1

        failed_outcome = LegalSourceHttpFetchOutcome(d, HTTP_REJECTED, http_status=403)
        with patch("law_data.legal_source_eflaw_local_acquisition_observation.fetch_legal_source_http",
                   return_value=failed_outcome), patch(
            "law_data.legal_source_eflaw_local_acquisition_observation._utc_iso",
            side_effect=("2026-10-15T00:00:01.000000Z", "2026-10-15T00:00:02.000000Z")
        ), patch("law_data.legal_source_eflaw_local_acquisition_observation.uuid4") as fake_uuid:
            fake_uuid.return_value.hex = "0" * 32
            failed = fetch_legal_source_eflaw_with_local_observation(d, "SYNTHETIC", enabled=True)
        r = inspect(corr, local_observation=failed)
        assert r.local_fetch_signal == "LOCAL_FETCH_UNRESOLVED"
        _safe(r)
        checks += 1

        for incorrect, kwargs, label in (
            (None, {}, "ORIGIN_GAP_INVALID_CORRESPONDENCE"),
            ("fake", {}, "ORIGIN_GAP_INVALID_CORRESPONDENCE"),
            (corr, {"guide": GUIDE_URI}, "ORIGIN_GAP_INVALID_GUIDE"),
            (corr, {"guide": {}}, "ORIGIN_GAP_INVALID_GUIDE"),
            (corr, {"local_observation": outcome}, "ORIGIN_GAP_INVALID_LOCAL_OBSERVATION"),
            (corr, {"receipt_inspection": "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"},
             "ORIGIN_GAP_INVALID_RECEIPT_INSPECTION"),
        ):
            _reject(lambda c=incorrect, k=kwargs: inspect(c, **k), label)
            checks += 1

        _reject(lambda: Inspection(
            UNATTESTED_BLOCKED, "EXACT_TRIPLE_SAME_PROVIDER_UNATTESTED",
            "NOT_SUPPLIED", "NOT_SUPPLIED", "NOT_SUPPLIED",
            "EFLAW_TEMPORAL_PREBINDING_BLOCKED_UNATTESTED_IDENTITIES",
            0, 0, 0, base.outstanding_requirement_codes,
        ), "ORIGIN_GAP_DIRECT_RESULT_FORBIDDEN")
        checks += 1
        for kwargs, error in (
            ({"status": "SOURCE_VERIFIED"}, "ORIGIN_GAP_INCONSISTENT_STATUS"),
            ({"status": COLLISION_BLOCKED}, "ORIGIN_GAP_INCONSISTENT_STATUS"),
            ({"official_guide_signal": "SOURCE_VERIFIED"}, "ORIGIN_GAP_INVALID_SIGNAL"),
            ({"article_collision_groups": 1}, "ORIGIN_GAP_INVALID_COLLISION_COUNTS"),
            ({"outstanding_requirement_codes": ()}, "ORIGIN_GAP_INCONSISTENT_REQUIREMENTS"),
            ({"temporal_prebinding_status": "SOURCE_VERIFIED"}, "ORIGIN_GAP_INVALID_PREBINDING"),
        ):
            _reject(lambda k=kwargs: replace(base, **k), error)
            checks += 1
        try:
            base.status = "SOURCE_VERIFIED"
        except (FrozenInstanceError, AttributeError):
            checks += 1
        else:
            raise AssertionError("MUTABLE_RESULT_FORBIDDEN")

    print("SYNTHETIC_INDEPENDENT_ORIGIN_GAP_CASES:", checks)
    print("ALL_CORRESPONDENCE_AND_ACQUISITION_SIGNALS_UNATTESTED: True")
    print("TWO_ARTICLE_COLLISIONS_REMAIN_BLOCKED: True")
    print("FORGED_RECEIPT_STATUS_NOT_PROMOTED: True")
    print("CANONICAL_VERSION_AND_LEGAL_EFFECT_NOT_EVALUATED: True")
    print("CANDIDATE_AND_RULE_ENGINE_ADMISSION_BLOCKED: True")
    print("PRIVATE_VALUES_NOT_DISCLOSED: True")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("EFLAW_INDEPENDENT_ORIGIN_EVIDENCE_REQUIREMENTS_CONTRACT_PASS")


if __name__ == "__main__":
    main()
