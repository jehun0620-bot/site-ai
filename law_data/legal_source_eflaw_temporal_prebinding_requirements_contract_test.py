# -*- coding: utf-8 -*-
"""Offline synthetic contract: EFLAW temporal prebinding is ALWAYS blocked."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_temporal_prebinding_requirements import (
    COLLISION_BLOCKED, STRUCTURE_BLOCKED, UNATTESTED_BLOCKED,
    LegalSourceEflawTemporalPrebindingRequirementsInspection,
    inspect_legal_source_eflaw_temporal_prebinding_requirements as inspect,
)

PRIVATE = "SYNTHETIC_PRIVATE_OC_AND_CONTENT_DO_NOT_EXPOSE"


def encode(articles=(), annexes=(), *, law_date="20120106", supplementary=True):
    law = {"조문": {"조문단위": list(articles)}, "별표": {"별표단위": list(annexes)}}
    if law_date is not None:
        law["기본정보"] = {"시행일자": law_date}
    if supplementary:
        law["부칙"] = {"부칙단위": [{"부칙내용": [PRIVATE]}]}
    return json.dumps({"법령": law}, ensure_ascii=False).encode("utf-8")


def article(n="1", k="K", *, branch="0", date="20120106", body=PRIVATE,
            omit_branch=False, omit_date=False):
    x = {"조문번호": n, "조문키": k, "조문내용": body}
    if not omit_branch:
        x["조문가지번호"] = branch
    if not omit_date:
        x["조문시행일자"] = date
    return x


def annex(n="1", branch="0", *, date="20120106", omit_date=False):
    x = {"별표번호": n, "별표가지번호": branch}
    if not omit_date:
        x["별표시행일자"] = date
    return x


def safe(result):
    doc = result.public_record()
    shown = json.dumps(doc, ensure_ascii=False) + repr(result)
    for word in (PRIVATE, "조문번호", "조문키", "별표번호", "별표가지번호",
                 "조문내용", "20120106", "20300230", "OC=", "https://", "MST="):
        assert word not in shown, "PRIVATE_INFORMATION_EXPOSED"
    assert doc["date_shape_is_legal_effect"] is False
    assert doc["local_identifier_uniqueness_is_canonical"] is False
    assert doc["response_array_position_is_identifier"] is False
    assert doc["candidate_creation"] == "NOT_PERFORMED"
    assert doc["article_candidate_join"] == "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY"
    assert doc["annex_candidate_join"] == "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY"
    assert doc["collision_merging"] == "FORBIDDEN"
    assert doc["array_index_identifier_promotion"] == "FORBIDDEN"
    assert doc["rule_engine_admission"] == "FORBIDDEN"
    for field in (
        "source_origin_attestation", "response_law_version_identity",
        "canonical_article_identity", "canonical_annex_identity",
        "supplementary_and_amendment_effect", "article_and_annex_legal_effect",
        "parcel_applicability", "current_legal_validity", "production_admission",
    ):
        assert doc[field] == "NOT_EVALUATED", field


def rejects(fn, code):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        assert PRIVATE not in str(exc)
    else:
        raise AssertionError("EXPECTED_FAIL_CLOSED_ERROR")


def main():
    count = 0
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("DISK_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("DISK_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("DISK_IO_FORBIDDEN")):
        base = inspect(encode([article("1", "K1"), article("2", "K2")], [annex()]))
        assert base.status == UNATTESTED_BLOCKED
        assert (base.date_literals_calendar_shape_valid, base.date_literals_calendar_shape_invalid) == (4, 0)
        safe(base)
        count += 1

        # This synthetic response reproduces OBSERVED structural counts,
        # but is NOT a copy, attestation, or legal interpretation of the API.
        records = [article(str(i), "KEY_" + str(i), omit_branch=(i % 2 == 0))
                   for i in range(157)]
        for i in range(14):
            records.append(article(str(i), "ALT_" + str(i),
                                   omit_branch=(i % 2 == 0)))
        for i in (14, 15):
            records.append(article(str(i), "ALT_" + str(i)))
            records.append(article(str(i), "KEY_" + str(i), body="CHANGED_BODY"))
        # Correct the branch to match the initial base item (all i=14,15
        # are even/odd and here both base branch presence differs).
        for i in (14, 15):
            original = records[i]
            for later in records[157:]:
                if later["조문번호"] == original["조문번호"]:
                    if "조문가지번호" not in original:
                        later.pop("조문가지번호", None)
        # Total 157 + 14 + 4 = 175. Repeated raw pairs 16, triple collision 2.
        assert len(records) == 175
        annexes = [annex(str(i % 28), str(i // 28)) for i in range(31)]
        historic = inspect(encode(records, annexes))
        assert historic.status == COLLISION_BLOCKED
        assert (historic.article_units_examined, historic.article_collision_groups,
                historic.article_collision_member_units, historic.annex_units_examined,
                historic.annex_collision_groups) == (175, 2, 4, 31, 0)
        assert (historic.date_literals_calendar_shape_valid,
                historic.date_literals_calendar_shape_invalid) == (207, 0)
        safe(historic)
        count += 1

        # Local uniqueness, even with no collisions, NEVER allows candidate joins.
        for art, ann, status in (
            ([article("1", "A")], [annex()], UNATTESTED_BLOCKED),
            ([], [], STRUCTURE_BLOCKED),
            ([article("1", "A", omit_branch=True),
              article("1", "A", branch="0")], [annex("1", "0")], UNATTESTED_BLOCKED),
        ):
            r = inspect(encode(art, ann))
            assert r.status == status
            safe(r)
            count += 1

        # A repeated triple dominates unrelated invalid annex local pairs.
        r = inspect(encode([article(), article(body="changed")],
                           [annex("1", ""), annex("2", "0")]))
        assert r.status == COLLISION_BLOCKED
        assert r.article_collision_groups == 1 and r.annex_ineligible_units == 1
        safe(r)
        count += 1
        r = inspect(encode([article("1", "A")], [annex(), annex()]))
        assert r.status == COLLISION_BLOCKED and r.annex_collision_groups == 1
        safe(r)
        count += 1

        # Candidate gate stays shut for missing or incorrectly typed selectors.
        for field, bad_value in (
            ("조문번호", ""), ("조문번호", None), ("조문번호", 1),
            ("조문키", ""), ("조문키", None), ("조문키", 4),
            ("조문가지번호", ""), ("조문가지번호", None), ("조문가지번호", 0),
        ):
            a = article()
            a[field] = bad_value
            r = inspect(encode([a], [annex()]))
            assert r.status == STRUCTURE_BLOCKED and r.article_ineligible_units == 1
            safe(r)
            count += 1
        for field, value in (("별표번호", ""), ("별표번호", None),
                             ("별표번호", 9), ("별표가지번호", ""),
                             ("별표가지번호", None), ("별표가지번호", 9)):
            a = annex()
            a[field] = value
            r = inspect(encode([article()], [a]))
            assert r.status == STRUCTURE_BLOCKED and r.annex_ineligible_units == 1
            safe(r)
            count += 1
        for field in ("별표번호", "별표가지번호"):
            a = annex()
            del a[field]
            r = inspect(encode([article()], [a]))
            assert r.status == STRUCTURE_BLOCKED
            count += 1

        # These are syntactically invalid or non-calendar strings, not legal dates.
        bad_dates = ("20300230", "", "２０２０１００１", "20121301", "20120001",
                     "00000101", "2012011", "2012-01-06", PRIVATE)
        for raw in bad_dates:
            for location in ("law", "article", "annex"):
                if location == "law":
                    r = inspect(encode([article()], [annex()], law_date=raw))
                elif location == "article":
                    r = inspect(encode([article(date=raw)], [annex()]))
                else:
                    r = inspect(encode([article()], [annex(date=raw)]))
                assert r.status == STRUCTURE_BLOCKED and r.date_literals_calendar_shape_invalid == 1
                safe(r)
                count += 1
        for p in (
            encode([article(omit_date=True)], [annex()]),
            encode([article()], [annex(omit_date=True)]),
            encode([article()], [annex()], law_date=None),
            encode([article()], [annex()], supplementary=False),
        ):
            r = inspect(p)
            assert r.status == STRUCTURE_BLOCKED
            safe(r)
            count += 1

        # A malformed date type is fail-closed in upstream extractor.
        for wrong in (None, 0, [], {}):
            rejects(lambda x=wrong: inspect(encode([article(date=x)], [annex()])),
                    "TEMPORAL_FIELD_TYPE_UNRESOLVED")
            count += 1
        for wrong in (None, 0, [], {}):
            rejects(lambda x=wrong: inspect(encode([article()], [annex(date=x)])),
                    "TEMPORAL_FIELD_TYPE_UNRESOLVED")
            count += 1

        # The upstream strict parser prevents duplicates and malformed JSON.
        for raw, error in (
            (b"", "TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED"),
            (b"{}", "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b"{invalid", "TEMPORAL_RESPONSE_JSON_UNRESOLVED"),
            ('{"법령":{"조문":{},"조문":{}}}'.encode(),
             "TEMPORAL_DUPLICATE_JSON_KEY"),
            ('{"법령":{"조문":{"조문단위":[null]}}}'.encode(),
             "TEMPORAL_UNIT_SHAPE_UNRESOLVED"),
        ):
            rejects(lambda p=raw: inspect(p), error)
            count += 1

        # Sealed immutable diagnostic; cannot forge approval or contradictory status.
        rejects(lambda: replace(historic, status=UNATTESTED_BLOCKED),
                "INCONSISTENT_PREBINDING_STATUS")
        count += 1
        rejects(lambda: replace(historic, article_collision_member_units=999),
                "INCONSISTENT_PREBINDING_IDENTIFIER_COUNTS")
        count += 1
        rejects(lambda: replace(base, date_literals_calendar_shape_valid=999),
                "INCONSISTENT_PREBINDING_DATE_COUNTS")
        count += 1
        rejects(lambda: LegalSourceEflawTemporalPrebindingRequirementsInspection(
            UNATTESTED_BLOCKED, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, True),
            "DIRECT_PREBINDING_INSPECTION_FORBIDDEN")
        count += 1
        try:
            base.status = "VERIFIED"
        except (FrozenInstanceError, AttributeError):
            count += 1
        else:
            raise AssertionError("MUTABLE_INSPECTION_FORBIDDEN")

    print("SYNTHETIC_TEMPORAL_PREBINDING_REQUIREMENTS_CASES:", count)
    print("HISTORIC_ARTICLE_COLLISIONS_AND_ANNEX_DISTINCT_SYNTHETIC: True")
    print("UNIQUE_LOCAL_STILL_BLOCKS_ALL_CANDIDATE_JOINS: True")
    print("MISSING_DATE_AND_NONCALENDAR_SHAPES_FAIL_CLOSED: True")
    print("SUPPLEMENTARY_CONTENT_NOT_INTERPRETED: True")
    print("PRIVATE_DATES_IDENTIFIERS_AND_PROSE_NOT_DISCLOSED: True")
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("OFFICIAL_ORIGIN_ATTESTATION: NOT_EVALUATED")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("EFLAW_TEMPORAL_PREBINDING_REQUIREMENTS_CONTRACT_PASS")


if __name__ == "__main__":
    main()
