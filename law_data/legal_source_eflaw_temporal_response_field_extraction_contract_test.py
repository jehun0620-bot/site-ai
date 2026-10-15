# -*- coding: utf-8 -*-
"""Offline synthetic contract; no network, file output, or legal effects."""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_temporal_response_field_extraction import (
    OBSERVED, PARTIAL,
    LegalSourceEflawTemporalResponseFieldExtraction,
    extract_legal_source_eflaw_temporal_response_fields,
)

PRIVATE = "SYNTHETIC_PRIVATE_OC_SECRET_NOT_FOR_PUBLIC_DIAGNOSTICS"


def payload(doc):
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def expect_rejection(fn, code):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        assert PRIVATE not in str(exc)
    else:
        raise AssertionError("EXPECTED_FAIL_CLOSED_REJECTION")


def assert_safe(result):
    public = json.dumps(result.public_record(), ensure_ascii=False)
    shown = repr(result)
    for part in (PRIVATE, "OC=", "20120106", "20300230", "RAW_SUPPLEMENTARY_TEXT",
                 "https://", "121615", "법령/"):
        assert part not in public and part not in shown, "PRIVATE_DATA_EXPOSED"
    record = result.public_record()
    assert record["date_values_parsed_or_verified"] is False
    assert record["supplementary_content_interpreted"] is False
    assert record["inventory_candidate_admission"] == "NOT_EVALUATED"
    assert record["path_basis"] == "ONE_PRIOR_LIVE_RESPONSE_OBSERVATION_NOT_GENERAL_SCHEMA"
    assert record["value_basis"] == "CALLER_PROVIDED_RESPONSE_BYTES_UNATTESTED"
    for k in ("response_source_identity_decision", "acquisition_authenticity_decision",
              "official_origin_decision", "current_validity_decision",
              "article_legal_effect_decision", "annex_legal_effect_decision",
              "supplementary_legal_effect_decision", "legal_applicability_decision",
              "production_admission_decision"):
        assert record[k] == "NOT_EVALUATED"
    assert "date_literals" not in public and "raw_date" not in public


def main():
    tested = 0
    inspect = extract_legal_source_eflaw_temporal_response_fields
    good = {"법령": {
        "기본정보": {"시행일자": "20120106"},
        "조문": {"조문단위": [
            {"조문시행일자": "20120106"},
            {"조문시행일자": "20300230"},
            {"조문명": PRIVATE},
        ]},
        "별표": {"별표단위": [{"별표시행일자": "20201011"}]},
        "부칙": {"부칙단위": [
            {"부칙내용": ["RAW_SUPPLEMENTARY_TEXT", PRIVATE]},
            {"부칙내용": [{"some": "other"}]},
        ]},
    }}
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")):
        r = inspect(payload(good))
        assert r.status == OBSERVED
        assert (r.law_count, r.article_count, r.annex_count, r.supplementary_count) == (1, 2, 1, 2)
        assert (r.article_units_examined, r.annex_units_examined,
                r.supplementary_units_examined) == (3, 1, 2)
        assert len(r._date_literals) == 4
        assert r._date_literals[0] == ("LAW_EFFECTIVE", None, "20120106")
        assert r._date_literals[2] == ("ARTICLE_EFFECTIVE", 1, "20300230")
        assert PRIVATE not in repr(r)
        assert_safe(r)
        tested += 1

        # Reproduce the number of observed structures in ONE prior user-local
        # response, but with synthetic values, not legal data or a schema proof.
        sizes = {"법령": {
            "기본정보": {"시행일자": "20120106"},
            "조문": {"조문단위": [{"조문시행일자": "20120106"}] * 175},
            "별표": {"별표단위": [{"별표시행일자": "20120106"}] * 31},
            "부칙": {"부칙단위": [{"부칙내용": ["unread"]}] * 63},
        }}
        r = inspect(payload(sizes))
        assert (r.law_count, r.article_count, r.annex_count,
                r.supplementary_count) == (1, 175, 31, 63)
        assert_safe(r)
        tested += 1

        # A missing path does not prove the corresponding law has no provisions.
        for doc in (
            {"법령": {}},
            {"법령": {"기본정보": {}}},
            {"법령": {"조문": {"조문단위": []}}},
            {"법령": {"기본정보": {"시행일자": ""}}},
            {"법령": {"부칙": {"부칙단위": [{"내용": ["unread"]}]}}},
            {"법령": {"별표": {"별표단위": [{}]}}},
        ):
            found = inspect(payload(doc))
            assert found.status == PARTIAL
            assert_safe(found)
            tested += 1

        # Paths outside one observed placement are ignored, not generalized.
        other_path = {"법령": {"새구조": {"조문시행일자": "20120106"},
                             "조문": {"조문단위": [{"다른필드": "20120106"}]}}}
        r = inspect(payload(other_path))
        assert r.article_count == 0 and r.status == PARTIAL
        tested += 1

        # Date literal extraction is NOT validation of a YYYYMMDD calendar date.
        for literal in ("20300230", "", "unknown", PRIVATE, "2030-01-01"):
            doc = {"법령": {"기본정보": {"시행일자": literal}}}
            r = inspect(payload(doc))
            assert r.law_count == 1 and r.status == PARTIAL
            assert r._date_literals == (("LAW_EFFECTIVE", None, literal),)
            assert_safe(r)
            tested += 1

        for source, code in (
            (b"", "TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED"),
            ("text", "TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED"),
            (b"{}{}", "TEMPORAL_RESPONSE_JSON_UNRESOLVED"),
            (b"{broken", "TEMPORAL_RESPONSE_JSON_UNRESOLVED"),
            (b"\xff", "TEMPORAL_RESPONSE_JSON_UNRESOLVED"),
            (b'[{"x": {}}]', "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b"[]", "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b"{}", "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b'{"x":NaN}', "TEMPORAL_NONSTANDARD_JSON_CONSTANT"),
            (b'{"x":Infinity}', "TEMPORAL_NONSTANDARD_JSON_CONSTANT"),
            (b'{"x":1,"x":2}', "TEMPORAL_DUPLICATE_JSON_KEY"),
            (b"x" * 10_000_001, "TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED"),
        ):
            expect_rejection(lambda s=source: inspect(s), code)
            tested += 1

        for bad in (None, [], "value", False, 0):
            expect_rejection(lambda v=bad: inspect(payload({"법령": v})),
                             "TEMPORAL_EFLAW_ROOT_UNRESOLVED")
            tested += 1

        for section in ("기본정보", "조문", "별표", "부칙"):
            for value in ([], "bad", None):
                expect_rejection(lambda s=section, v=value: inspect(payload({"법령": {s: v}})),
                                 "TEMPORAL_SECTION_SHAPE_UNRESOLVED")
                tested += 1

        for section, group in (("조문", "조문단위"), ("별표", "별표단위"), ("부칙", "부칙단위")):
            for value in ({}, "bad", None, [None]):
                code = "TEMPORAL_UNIT_SHAPE_UNRESOLVED" if type(value) is list else "TEMPORAL_UNIT_COLLECTION_UNRESOLVED"
                expect_rejection(lambda s=section, g=group, v=value:
                                 inspect(payload({"법령": {s: {g: v}}})), code)
                tested += 1

        for section, group, name, wrong in (
            ("기본정보", None, "시행일자", 20120106),
            ("기본정보", None, "시행일자", None),
            ("기본정보", None, "시행일자", ["20120106"]),
            ("조문", "조문단위", "조문시행일자", ["20120106"]),
            ("조문", "조문단위", "조문시행일자", None),
            ("별표", "별표단위", "별표시행일자", False),
            ("별표", "별표단위", "별표시행일자", {}),
            ("부칙", "부칙단위", "부칙내용", "unexpected string"),
            ("부칙", "부칙단위", "부칙내용", None),
            ("부칙", "부칙단위", "부칙내용", {}),
        ):
            obj = {name: wrong}
            node = obj if group is None else {group: [obj]}
            expect_rejection(lambda s=section, n=node: inspect(payload({"법령": {s: n}})),
                             "TEMPORAL_FIELD_TYPE_UNRESOLVED")
            tested += 1

        for section, group in (("조문", "조문단위"), ("별표", "별표단위"), ("부칙", "부칙단위")):
            expect_rejection(lambda s=section, g=group: inspect(payload({
                "법령": {s: {g: [{}] * 20_001}}
            })), "TEMPORAL_UNIT_COLLECTION_UNRESOLVED")
            tested += 1

        # Prevent direct minting of success or contradictory diagnostics.
        expect_rejection(lambda: LegalSourceEflawTemporalResponseFieldExtraction(
            OBSERVED, 1, 1, 1, 1, 1, 1, 1, ()),
            "DIRECT_TEMPORAL_EXTRACTION_RESULT_FORBIDDEN")
        tested += 1
        expect_rejection(lambda: replace(r, status=OBSERVED),
                         "INCONSISTENT_TEMPORAL_EXTRACTION_STATUS")
        tested += 1
        expect_rejection(lambda: replace(r, law_count=4),
                         "INCONSISTENT_TEMPORAL_EXTRACTION_COUNTS")
        tested += 1
        expect_rejection(lambda: replace(r, _date_literals=()),
                         "INCONSISTENT_PRIVATE_DATE_LITERALS")
        tested += 1
        try:
            r.status = "SOURCE_VERIFIED"
        except (FrozenInstanceError, AttributeError):
            tested += 1
        else:
            raise AssertionError("EXTRACTION_RESULT_MUTABLE")

    print("SYNTHETIC_TEMPORAL_FIELD_EXTRACTION_CASES:", tested)
    print("ONE_LIVE_RESPONSE_PATHS_ONLY: True")
    print("LAW_ARTICLE_ANNEX_STRINGS_AND_SUPPLEMENTARY_ARRAYS: True")
    print("RESPONSE_DATE_LITERALS_NOT_VERIFIED_OR_PUBLIC: True")
    print("SUPPLEMENTARY_ARRAY_CONTENT_NOT_INTERPRETED: True")
    print("MISSING_PATH_NOT_LEGAL_ABSENCE: True")
    print("NO_CANDIDATE_INVENTORY_OR_RULE_ENGINE_PROMOTION: True")
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("CURRENT_VALIDITY: NOT_EVALUATED")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_TEMPORAL_RESPONSE_FIELD_EXTRACTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
