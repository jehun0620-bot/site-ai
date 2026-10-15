# -*- coding: ascii -*-
"""Strict offline contract for caller-declared temporal evidence candidates."""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_public_request_descriptor import (
    build_legal_source_public_request_descriptor,
)
from law_data.legal_source_eflaw_official_guide_evidence_boundary import (
    GUIDE_URI,
    LegalSourceEflawOfficialGuideReference,
)
from law_data.legal_source_eflaw_temporal_evidence_inventory import (
    _KINDS, CLAIM_CONFLICT, EMPTY_UNVERIFIED, GUIDE_UNRESOLVED,
    INVENTORY_UNVERIFIED, LegalSourceEflawTemporalEvidenceCandidate,
    LegalSourceEflawTemporalEvidenceInspection,
    inspect_legal_source_eflaw_temporal_evidence_inventory,
)

PRIVATE = "SYNTHETIC_OC_PRIVATE_CREDENTIAL_DO_NOT_LOG"


def rejected(call, error_class, reason):
    try:
        call()
    except error_class as exc:
        assert str(exc) == reason, (str(exc), reason)
        assert PRIVATE not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def assert_safe(result):
    doc = result.public_record()
    dump = json.dumps(doc, ensure_ascii=True)
    for token in (PRIVATE, "OC=", "121615", "20120106", "20200101",
                  "ARTICLE_LOCAL_1", "https://", "lsEfYdInfoGuide"):
        assert token not in dump and token not in repr(result), "PRIVATE_EVIDENCE_EXPOSED"
    assert doc["item_basis"] == "CALLER_DECLARED_NOT_RESPONSE_FIELD_OBSERVED"
    assert doc["absent_candidate_means"] == "NOT_SUPPLIED_BY_CALLER_NOT_LEGAL_ABSENCE"
    assert doc["history_source_boundary"] == "LSHISTORY_HTML_SEPARATE_UNINSPECTED"
    for field in (
        "api_response_field_paths_verified", "guide_capture_authenticity",
        "acquisition_authenticity_decision", "official_origin_decision",
        "source_verification_decision", "current_validity_decision",
        "article_legal_effect_decision", "annex_legal_effect_decision",
        "supplementary_legal_effect_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert doc[field] == "NOT_EVALUATED"
    assert "claim_value" not in dump and "declared_yyyymmdd" not in dump
    assert "raw_response" not in dump and "payload" not in dump


def main():
    checked = 0
    descriptor = build_legal_source_public_request_descriptor({
        "target": "eflaw", "type": "JSON", "MST": "121615", "efYd": "20120106",
    })
    ordin = build_legal_source_public_request_descriptor({
        "target": "ordin", "type": "JSON", "MST": "2149501",
    })
    guide = LegalSourceEflawOfficialGuideReference(GUIDE_URI)
    inspect = inspect_legal_source_eflaw_temporal_evidence_inventory
    item = LegalSourceEflawTemporalEvidenceCandidate
    law = item("LAW_EFFECTIVE", _KINDS["LAW_EFFECTIVE"], declared_yyyymmdd="20120106")
    article = item("ARTICLE_EFFECTIVE", _KINDS["ARTICLE_EFFECTIVE"],
                   locator="ARTICLE_LOCAL_1", declared_yyyymmdd="20200101")
    annex = item("ANNEX_EFFECTIVE", _KINDS["ANNEX_EFFECTIVE"],
                 locator="ANNEX_LOCAL_1", declared_yyyymmdd="20220201")
    supp = item("SUPPLEMENTARY_CONTENT", _KINDS["SUPPLEMENTARY_CONTENT"],
                locator="SUPP_LOCAL_1", content_declared=True)
    claims = (law, article, annex, supp)

    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")):
        r = inspect(descriptor, guide, ())
        assert r.status == EMPTY_UNVERIFIED and r.temporal_candidate_count == 0
        assert r.selector_vs_declared_law_date == "NOT_SUPPLIED_BY_CALLER"
        assert_safe(r)
        checked += 1

        r = inspect(descriptor, guide, claims)
        assert r.status == INVENTORY_UNVERIFIED and r.guide_reference_check == "MATCH"
        assert (r.temporal_candidate_count, r.law_candidate_count,
                r.article_candidate_count, r.annex_candidate_count,
                r.supplementary_candidate_count) == (4, 1, 1, 1, 1)
        assert r.selector_vs_declared_law_date == "MATCH_DECLARED_UNVERIFIED"
        assert_safe(r)
        checked += 1

        # Distinct scope dates do not imply precedence, contradiction or legal effect.
        assert inspect(descriptor, guide, (article, annex, supp)).status == INVENTORY_UNVERIFIED
        checked += 1
        r = inspect(descriptor, guide, (replace(law, declared_yyyymmdd="20201231"),))
        assert r.status == INVENTORY_UNVERIFIED
        assert r.selector_vs_declared_law_date == "DIFFERENT_DECLARED_UNVERIFIED"
        assert_safe(r)
        checked += 1

        # None means no date declaration, not a missing field in law.
        undated = replace(article, declared_yyyymmdd=None)
        r = inspect(descriptor, guide, (undated,))
        assert r.temporal_candidate_count == 1
        assert r.selector_vs_declared_law_date == "NOT_SUPPLIED_BY_CALLER"
        checked += 1

        r = inspect(descriptor, guide, (law, law))
        assert r.status == INVENTORY_UNVERIFIED and r.temporal_candidate_count == 1
        checked += 1
        r = inspect(descriptor, guide, (article, replace(article, declared_yyyymmdd="20220201")))
        assert r.status == CLAIM_CONFLICT
        assert r.selector_vs_declared_law_date == "NOT_EVALUATED"
        assert_safe(r)
        checked += 1
        r = inspect(descriptor, guide, (law, replace(law, declared_yyyymmdd="20120201")))
        assert r.status == CLAIM_CONFLICT
        checked += 1
        r = inspect(descriptor, guide, (supp, replace(supp, content_declared=False)))
        assert r.status == CLAIM_CONFLICT
        checked += 1

        # Scope-gate has precedence; even a perfect-looking caller claim is no proof.
        for invalid_guide in (None, GUIDE_URI + "#a", "https://example.invalid/"):
            gr = LegalSourceEflawOfficialGuideReference(invalid_guide)
            r = inspect(descriptor, gr, claims)
            assert r.status == GUIDE_UNRESOLVED
            assert r.guide_reference_check == "UNRESOLVED"
            assert_safe(r)
            checked += 1

        # Dates are validated as calendar dates but NOT adjudicated as effective.
        for valid in ("20000229", "19990101", "20991231"):
            candidate = replace(law, declared_yyyymmdd=valid)
            assert inspect(descriptor, guide, (candidate,)).status == INVENTORY_UNVERIFIED
            checked += 1
        for bad in ("20260230", "20190229", "00000101", "2012010", "201201061",
                    "2012-01-06", "\uff12\uff10\uff12\uff10\uff10\uff11\uff10\uff11", 20120106,
                    False, {}, PRIVATE):
            rejected(lambda v=bad: replace(law, declared_yyyymmdd=v), ValueError,
                     "INVALID_DECLARED_DATE")
            checked += 1

        for bad_kind in ("HISTORY_HTML", "ARTICLE_LEGAL_EFFECT", "OTHER", "", PRIVATE):
            rejected(lambda k=bad_kind: item(k, _KINDS["LAW_EFFECTIVE"]),
                     ValueError, "UNSUPPORTED_TEMPORAL_EVIDENCE_KIND")
            checked += 1
        rejected(lambda: replace(law, field_name=_KINDS["ARTICLE_EFFECTIVE"]),
                 ValueError, "TEMPORAL_FIELD_KIND_MISMATCH")
        checked += 1
        rejected(lambda: replace(law, locator="LAW_LOCAL"),
                 ValueError, "LAW_TEMPORAL_LOCATOR_FORBIDDEN")
        checked += 1
        for bad_locator in (None, "", "https://bad.invalid", "OC=" + PRIVATE,
                            "A" * 65, "hangul-\ud55c\uae00", "name space"):
            rejected(lambda v=bad_locator: replace(article, locator=v), ValueError,
                     "INVALID_LOCAL_TEMPORAL_LOCATOR")
            checked += 1
        rejected(lambda: replace(supp, declared_yyyymmdd="20120106"),
                 ValueError, "SUPPLEMENTARY_DATE_INFERENCE_FORBIDDEN")
        checked += 1
        rejected(lambda: replace(supp, content_declared=None),
                 ValueError, "INVALID_SUPPLEMENTARY_CONTENT_CLAIM")
        checked += 1
        rejected(lambda: replace(article, content_declared=True),
                 ValueError, "CONTENT_CLAIM_FOR_DATE_FIELD_FORBIDDEN")
        checked += 1

        for bad_input, reason in (
            ((None, guide, claims), "INVALID_EFLAW_TEMPORAL_DESCRIPTOR"),
            ((ordin, guide, claims), "INVALID_EFLAW_TEMPORAL_DESCRIPTOR"),
            ((descriptor, None, claims), "INVALID_TEMPORAL_GUIDE_REFERENCE"),
            ((descriptor, guide, None), "INVALID_TEMPORAL_CANDIDATE_COLLECTION"),
            ((descriptor, guide, [law]), "INVALID_TEMPORAL_CANDIDATE_COLLECTION"),
            ((descriptor, guide, ("law",)), "INVALID_TEMPORAL_CANDIDATE_COLLECTION"),
        ):
            rejected(lambda a=bad_input: inspect(*a), TypeError, reason)
            checked += 1
        rejected(lambda: inspect(descriptor, guide, (law,) * 513),
                 ValueError, "TOO_MANY_TEMPORAL_CANDIDATES")
        checked += 1

        rejected(lambda: LegalSourceEflawTemporalEvidenceInspection(
            INVENTORY_UNVERIFIED, "MATCH", 1, 1, 0, 0, 0,
            "MATCH_DECLARED_UNVERIFIED"), ValueError,
            "DIRECT_TEMPORAL_INSPECTION_CONSTRUCTION_FORBIDDEN")
        checked += 1
        rejected(lambda: replace(r, status="SOURCE_VERIFIED"), ValueError,
                 "INVALID_TEMPORAL_INSPECTION_STATUS")
        checked += 1
        rejected(lambda: replace(r, temporal_candidate_count=999), ValueError,
                 "INCONSISTENT_TEMPORAL_COUNTS")
        checked += 1
        try:
            r.status = "SOURCE_VERIFIED"
        except (AttributeError, FrozenInstanceError):
            checked += 1
        else:
            raise AssertionError("RESULT_MUTABLE")

    print("SYNTHETIC_TEMPORAL_EVIDENCE_CASES:", checked)
    print("LAW_ARTICLE_ANNEX_SUPPLEMENTARY_DISTINCT: True")
    print("DUPLICATE_CONFLICTS_REMAIN_UNRESOLVED: True")
    print("ABSENCE_NOT_LEGAL_ABSENCE: True")
    print("NO_RESPONSE_JSON_FIELD_PATH_ASSUMED: True")
    print("HISTORY_HTML_SEPARATE_AND_UNPARSED: True")
    print("CURRENT_LEGAL_VALIDITY: NOT_EVALUATED")
    print("SOURCE_VERIFICATION: NOT_EVALUATED")
    print("NETWORK_REQUESTS: 0")
    print("REAL_API_KEY_USED: False")
    print("FILES_WRITTEN: 0")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_TEMPORAL_EVIDENCE_INVENTORY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
