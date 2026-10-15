# -*- coding: utf-8 -*-
"""Synthetic offline contract: equality remains UNATTESTED, all joins blocked."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_public_request_descriptor import LegalSourcePublicRequestDescriptor
from law_data.legal_source_eflaw_list_detail_local_correspondence import (
    EXACT_ONE, MULTIPLE, NO_MATCH, NORMALIZED_ONLY, PATH_UNRESOLVED,
    LegalSourceEflawListDetailLocalCorrespondenceInspection,
    inspect_legal_source_eflaw_list_detail_local_correspondence as inspect,
)

PRIVATE = "PRIVATE_LAW_NAME_AND_OC_DO_NOT_EXPOSE"


def detail(*, lid="001234", day="20120106", articles=None, annexes=None,
           law_name=PRIVATE, supplementary=True):
    if articles is None:
        articles = [{"조문번호": "1", "조문가지번호": "0", "조문키": "K1",
                     "조문시행일자": day, "조문내용": PRIVATE}]
    if annexes is None:
        annexes = [{"별표번호": "1", "별표가지번호": "0", "별표시행일자": day}]
    root = {
        "기본정보": {"법령ID": lid, "법령명_한글": law_name, "시행일자": day},
        "조문": {"조문단위": articles},
        "별표": {"별표단위": annexes},
    }
    if supplementary:
        root["부칙"] = {"부칙단위": [{"부칙내용": [PRIVATE]}]}
    return json.dumps({"법령": root}, ensure_ascii=False).encode("utf-8")


def listing(rows):
    return json.dumps({"LawSearch": {"law": rows}}, ensure_ascii=False).encode("utf-8")


def row(a="001234", b="121615", c="20120106", **extra):
    return {"법령ID": a, "법령일련번호": b, "시행일자": c, **extra}


def descriptor(efyd="20120106"):
    return LegalSourcePublicRequestDescriptor("eflaw", "121615", efyd)


def safe(r):
    record = r.public_record()
    displayed = json.dumps(record, ensure_ascii=False) + repr(r)
    for text in (PRIVATE, "001234", "121615", "20120106", "OC=", "https://",
                 "법령ID", "법령일련번호", "시행일자"):
        assert text not in displayed, "PRIVATE_VALUES_EXPOSED"
    assert record["exact_match_confirms_canonical_version"] is False
    assert record["no_match_proves_legal_absence"] is False
    assert record["list_filter_enforcement"] == "NOT_EVALUATED"
    assert record["cross_endpoint_provider_independence"] is False
    assert record["candidate_creation"] == "NOT_PERFORMED"
    assert record["date_candidate_join"] == "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY"
    assert record["collision_merging"] == "FORBIDDEN"
    assert record["array_index_identifier_promotion"] == "FORBIDDEN"
    assert record["rule_engine_admission"] == "FORBIDDEN"
    for key in ("official_origin_attestation", "canonical_law_version_identity",
                "article_and_annex_legal_effect", "current_legal_validity",
                "parcel_applicability", "production_admission"):
        assert record[key] == "NOT_EVALUATED"


def rejects(fn, expected):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == expected, (str(exc), expected)
        assert PRIVATE not in str(exc)
    else:
        raise AssertionError("EXPECTED_FAIL_CLOSED")


def main():
    checks = 0
    p = detail()
    d = descriptor()
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("DISK_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("DISK_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("DISK_IO_FORBIDDEN")):
        base = inspect(p, listing(row()), d)
        assert base.status == EXACT_ONE
        assert (base.rows_examined, base.normalized_triple_matches,
                base.exact_unmodified_string_matches, base.normalized_only_matches) == (1, 1, 1, 0)
        assert base.prebinding_status == "EFLAW_TEMPORAL_PREBINDING_BLOCKED_UNATTESTED_IDENTITIES"
        safe(base)
        checks += 1

        scenarios = (
            ([row()], EXACT_ONE, (1, 1, 0)),
            (row(), EXACT_ONE, (1, 1, 0)),
            ([row(b=121615)], NORMALIZED_ONLY, (1, 0, 1)),
            ([row(c=20120106)], NORMALIZED_ONLY, (1, 0, 1)),
            ([row(b=" 121615 ")], NORMALIZED_ONLY, (1, 0, 1)),
            ([row(a={"content": "001234"})], NORMALIZED_ONLY, (1, 0, 1)),
            ([row(a=1234)], NO_MATCH, (0, 0, 0)),
            ([row(c="20120107")], NO_MATCH, (0, 0, 0)),
            ([row(b="121616")], NO_MATCH, (0, 0, 0)),
            ([row(), row()], MULTIPLE, (2, 2, 0)),
            ([row(), row(b=121615)], MULTIPLE, (2, 1, 1)),
            ([], NO_MATCH, (0, 0, 0)),
            ([{"other": "value"}], NO_MATCH, (0, 0, 0)),
            ([row(a=None)], NO_MATCH, (0, 0, 0)),
            ([row(a=True)], NO_MATCH, (0, 0, 0)),
            ([row(a=-1)], NO_MATCH, (0, 0, 0)),
        )
        for rows, state, counts in scenarios:
            r = inspect(p, listing(rows), d)
            assert r.status == state
            assert (r.normalized_triple_matches, r.exact_unmodified_string_matches,
                    r.normalized_only_matches) == counts
            safe(r)
            checks += 1

        # Exact matching cannot supersede the upstream TWO ARTICLE COLLISIONS.
        articles = [
            {"조문번호": "1", "조문가지번호": "0", "조문키": "K1",
             "조문시행일자": "20120106", "조문내용": PRIVATE},
            {"조문번호": "1", "조문가지번호": "0", "조문키": "K1",
             "조문시행일자": "20120106", "조문내용": "different"},
            {"조문번호": "2", "조문가지번호": "0", "조문키": "K2",
             "조문시행일자": "20120106", "조문내용": PRIVATE},
            {"조문번호": "2", "조문가지번호": "0", "조문키": "K2",
             "조문시행일자": "20120106", "조문내용": "another"},
        ]
        collision = inspect(detail(articles=articles), listing(row()), d)
        assert collision.status == EXACT_ONE
        assert collision.prebinding_status == "EFLAW_TEMPORAL_PREBINDING_BLOCKED_RESPONSE_LOCAL_COLLISIONS"
        assert collision.article_collision_groups == 2 and collision.article_collision_member_units == 4
        safe(collision)
        checks += 1

        # Same observed raw triad but selector different is NOT current-law proof.
        different_selector = inspect(p, listing(row()), descriptor("20120107"))
        assert different_selector.selector_vs_detail_day == "DIFFERENT_RAW_DAY"
        safe(different_selector)
        checks += 1

        # Observed single-response list path is NOT an official JSON schema.
        for raw, state in (
            ({}, "NOT_OBSERVED"),
            ({"LawSearch": {}}, "NOT_OBSERVED"),
            ({"LawSearch": None}, "UNSUPPORTED_MEMBER_SHAPE"),
            ({"LawSearch": {"law": None}}, "UNSUPPORTED_MEMBER_SHAPE"),
            ({"LawSearch": {"law": [row(), None]}}, "UNSUPPORTED_MEMBER_SHAPE"),
        ):
            result = inspect(p, json.dumps(raw, ensure_ascii=False).encode("utf-8"), d)
            assert result.status == PATH_UNRESOLVED and result.path_state == state
            safe(result)
            checks += 1
        deceptive = {"LawSearch": {"law": {"nested": row()}}}
        result = inspect(p, json.dumps(deceptive, ensure_ascii=False).encode("utf-8"), d)
        assert result.status == NO_MATCH
        safe(result)
        checks += 1

        # Upstream structure, date format, duplicate JSON keys are fail-closed.
        for raw, code in (
            (b"", "CORRESPONDENCE_LIST_BYTE_BOUNDS_UNRESOLVED"),
            (b"[]", "CORRESPONDENCE_LIST_ROOT_UNRESOLVED"),
            (b"broken", "CORRESPONDENCE_LIST_JSON_UNRESOLVED"),
            ('{"LawSearch":{"law":{},"law":{}}}'.encode(),
             "CORRESPONDENCE_LIST_JSON_UNRESOLVED"),
            (b'{"LawSearch":{"law":NaN}}', "CORRESPONDENCE_LIST_JSON_UNRESOLVED"),
        ):
            rejects(lambda data=raw: inspect(p, data, d), code)
            checks += 1
        for malformed in (detail(lid=""), detail(lid=1234), detail(day="20300230"),
                          detail(law_name=""), detail(supplementary=False, articles=[])):
            if malformed == detail(supplementary=False, articles=[]):
                r = inspect(malformed, listing(row()), d)
                assert r.status == EXACT_ONE and r.prebinding_status == (
                    "EFLAW_TEMPORAL_PREBINDING_BLOCKED_STRUCTURE_OR_DATE_SHAPE"
                )
                safe(r)
            else:
                rejects(lambda data=malformed: inspect(data, listing(row()), d),
                        "CORRESPONDENCE_DETAIL_IDENTITY_SHAPE_UNRESOLVED")
            checks += 1
        rejects(lambda: inspect(p, listing(row()), object()),
                "CORRESPONDENCE_INVALID_DESCRIPTOR")
        checks += 1
        rejects(lambda: inspect(p, listing(row()), LegalSourcePublicRequestDescriptor("ordin", "1")),
                "CORRESPONDENCE_INVALID_DESCRIPTOR")
        checks += 1
        rejects(lambda: replace(base, status=MULTIPLE), "CORRESPONDENCE_INCONSISTENT_STATUS")
        checks += 1
        rejects(lambda: replace(base, exact_unmodified_string_matches=9),
                "CORRESPONDENCE_INCONSISTENT_COUNTS")
        checks += 1
        rejects(lambda: LegalSourceEflawListDetailLocalCorrespondenceInspection(
            EXACT_ONE, "OBSERVED_OBJECT_UNATTESTED", 1, 1, 1, 0, 0, 0,
            1, 1, 0, "SAME_RAW_DAY", "EFLAW_TEMPORAL_PREBINDING_BLOCKED_UNATTESTED_IDENTITIES",
            0, 0, 0), "CORRESPONDENCE_DIRECT_RESULT_FORBIDDEN")
        checks += 1
        try:
            base.status = MULTIPLE
        except (FrozenInstanceError, AttributeError):
            checks += 1
        else:
            raise AssertionError("CORRESPONDENCE_MUTABLE")

    print("SYNTHETIC_LIST_DETAIL_CORRESPONDENCE_CASES:", checks)
    print("EXACT_STRING_AND_NORMALIZED_MATCHES_DISTINCT: True")
    print("OBSERVED_ROW_PATH_NOT_SCHEMA_ATTESTATION: True")
    print("TWO_ARTICLE_COLLISIONS_CANNOT_BE_OVERRIDDEN_BY_MATCH: True")
    print("NO_MATCH_DOES_NOT_PROVE_LEGAL_ABSENCE: True")
    print("CANDIDATE_AND_RULE_ENGINE_ADMISSION_BLOCKED: True")
    print("PRIVATE_VALUES_NOT_DISCLOSED: True")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("EFLAW_LIST_DETAIL_LOCAL_CORRESPONDENCE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
