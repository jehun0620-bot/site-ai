# -*- coding: utf-8 -*-
"""Offline synthetic fail-closed tests: no candidate joins, files, or network."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_article_item_ambiguity_guard import (
    AMBIGUOUS, INELIGIBLE, UNIQUE_LOCAL,
    LegalSourceEflawArticleItemAmbiguityInspection,
    inspect_legal_source_eflaw_article_item_ambiguity,
)

PRIVATE = "SYNTHETIC_PRIVATE_OC_DO_NOT_EXPOSE"


def encode(units):
    law = {"기본정보": {"시행일자": "20120106"},
           "조문": {"조문단위": units}}
    return json.dumps({"법령": law}, ensure_ascii=False).encode("utf-8")


def unit(primary, branch, key, body, *, date="20120106", omit_branch=False):
    out = {"조문번호": primary, "조문키": key,
           "조문시행일자": date, "조문내용": body}
    if not omit_branch:
        out["조문가지번호"] = branch
    return out


def assert_safe(result):
    doc = result.public_record()
    raw = json.dumps(doc, ensure_ascii=False)
    shown = repr(result)
    for forbidden in (PRIVATE, "OC=", "20120106", "20300230", "ARTICLE_SECRET",
                      "조문내용", "조문번호", "조문키", "https://"):
        assert forbidden not in raw and forbidden not in shown, "PRIVATE_DATA_EXPOSED"
    assert doc["article_date_candidate_join"] == "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY"
    assert doc["temporal_candidate_creation"] == "NOT_PERFORMED"
    assert doc["collision_merging"] == "FORBIDDEN"
    assert doc["array_index_identifier_promotion"] == "FORBIDDEN"
    assert doc["branch_absence_distinct_from_present_string_zero"] is True
    for k in ("official_item_identity_decision", "source_origin_attestation",
              "current_legal_validity", "legal_applicability", "production_admission"):
        assert doc[k] == "NOT_EVALUATED"


def rejected(fn, kind, code):
    try:
        fn()
    except kind as exc:
        assert str(exc) == code, (str(exc), code)
        assert PRIVATE not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def main():
    checked = 0
    inspect = inspect_legal_source_eflaw_article_item_ambiguity
    a = unit("11", "0", "ARTICLE_SECRET", PRIVATE)
    b = unit("11", "0", "ARTICLE_SECRET", "DIFFERENT_BODY")
    c = unit("12", "0", "UNIQUE_X", "other")
    d = unit("13", "", "UNIQUE_Z", "other")

    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")):
        x = inspect(encode([a, b, c]))
        assert x.status == AMBIGUOUS
        assert (x.article_units_examined, x.triple_eligible_units,
                x.triple_collision_groups, x.triple_collision_member_units,
                x.triple_collision_excess_units) == (3, 3, 1, 2, 1)
        assert x.collision_content_variation_groups == 1
        assert x.collision_date_variation_groups == 0
        assert x.raw_pair_repeated_groups == 1
        assert_safe(x)
        checked += 1

        # Reproduce the user-observed 175 / 16 pair groups / 2 triple collisions
        # with entirely synthetic identifiers and dates, not real legal evidence.
        originals = [unit(str(i), "0", "UNIQUE_" + str(i), PRIVATE) for i in range(157)]
        # 14 repeated pairs of 2 and 2 pairs of 3 -> 175 items total.
        duplicates = []
        for i in range(14):
            duplicates.append(unit(str(i), "0", "EXTRA_" + str(i), "other"))
        for i in range(14, 16):
            duplicates.append(unit(str(i), "0", "EXTRA_" + str(i), "other"))
            duplicates.append(unit(str(i), "0", "UNIQUE_" + str(i), "other"))
        r = inspect(encode(originals + duplicates))
        assert (r.article_units_examined, r.raw_pair_repeated_groups,
                r.triple_collision_groups, r.triple_collision_member_units,
                r.triple_collision_excess_units) == (175, 16, 2, 4, 2)
        assert r.collision_content_variation_groups == 2
        assert_safe(r)
        checked += 1

        # Response-local uniqueness still grants zero legal or candidate rights.
        for data in (
            [unit("1", "0", "A", PRIVATE), unit("2", "0", "B", "other")],
            [unit("1", "0", "A", PRIVATE), unit("1", "0", "B", "other")],
            [unit("1", "0", "A", PRIVATE), unit("1", "0", "A", "other", omit_branch=True)],
            [],
        ):
            r = inspect(encode(data))
            assert r.status == UNIQUE_LOCAL
            assert r.triple_collision_groups == 0
            assert_safe(r)
            checked += 1

        # Missing vs explicitly present string zero are different raw keys.
        missing = unit("1", "0", "A", "one", omit_branch=True)
        present = unit("1", "0", "A", "two")
        r = inspect(encode([missing, present]))
        assert r.status == UNIQUE_LOCAL and r.raw_pair_repeated_groups == 0
        assert_safe(r)
        checked += 1

        # The same triple with equal contents is still ambiguous.
        r = inspect(encode([a, a]))
        assert r.status == AMBIGUOUS and r.collision_content_variation_groups == 0
        checked += 1
        r = inspect(encode([a, unit("11", "0", "ARTICLE_SECRET", "different", date="20201231")]))
        assert r.collision_date_variation_groups == 1
        checked += 1
        r = inspect(encode([a, {k: v for k, v in b.items() if k != "조문내용"}]))
        assert r.collision_content_unresolved_groups == 1
        checked += 1

        # All unsupported key/branch/primary types fail eligibility closed.
        bad_variants = (
            ("조문번호", ""), ("조문번호", None), ("조문번호", 17),
            ("조문가지번호", ""), ("조문가지번호", None), ("조문가지번호", 0),
            ("조문키", ""), ("조문키", None), ("조문키", 1),
        )
        for label, value in bad_variants:
            u = dict(a)
            u[label] = value
            r = inspect(encode([u]))
            assert r.status == INELIGIBLE and r.triple_ineligible_units == 1
            assert_safe(r)
            checked += 1
        for missing_label in ("조문번호", "조문키"):
            u = dict(a)
            del u[missing_label]
            r = inspect(encode([u]))
            assert r.status == INELIGIBLE
            checked += 1

        # A detected collision always takes precedence over missing identifiers.
        u = dict(a)
        u["조문키"] = None
        r = inspect(encode([a, b, u]))
        assert r.status == AMBIGUOUS and r.triple_ineligible_units == 1
        checked += 1

        # Contradictory post-hoc status fabrication is blocked.
        rejected(lambda: replace(x, status=UNIQUE_LOCAL), ValueError,
                 "INCONSISTENT_ARTICLE_AMBIGUITY_STATUS")
        checked += 1
        rejected(lambda: replace(x, triple_collision_groups=0), ValueError,
                 "INCONSISTENT_ARTICLE_COLLISION_COUNTS")
        checked += 1
        rejected(lambda: replace(x, triple_eligible_units=17), ValueError,
                 "INCONSISTENT_ARTICLE_ELIGIBILITY_COUNTS")
        checked += 1
        rejected(lambda: LegalSourceEflawArticleItemAmbiguityInspection(
            AMBIGUOUS, 3, 3, 1, 3, 0, 1, 2, 1, 1, 0, 0),
            ValueError, "DIRECT_ARTICLE_AMBIGUITY_RESULT_FORBIDDEN")
        checked += 1
        try:
            x.status = UNIQUE_LOCAL
        except (FrozenInstanceError, AttributeError):
            checked += 1
        else:
            raise AssertionError("MUTABLE_RESULT")

        # The existing parser prevents duplicate keys and wrong response types.
        for bad, code in (
            ('{"법령":{"조문":{},"조문":{}}}'.encode("utf-8"), "TEMPORAL_DUPLICATE_JSON_KEY"),
            (b"{broken", "TEMPORAL_RESPONSE_JSON_UNRESOLVED"),
            (b"{}", "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b"[]", "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b"", "TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED"),
            ('{"법령":{"조문":{"조문단위":[null]}}}'.encode("utf-8"),
             "TEMPORAL_UNIT_SHAPE_UNRESOLVED"),
            ('{"법령":{"조문":{"조문단위":[]}}}'.encode("utf-8"), None),
        ):
            if code is None:
                assert inspect(bad).status == UNIQUE_LOCAL
            else:
                rejected(lambda data=bad: inspect(data), ValueError, code)
            checked += 1

    print("SYNTHETIC_ARTICLE_AMBIGUITY_GUARD_CASES:", checked)
    print("REPEATED_PAIR_KEY_CONTENT_VARIATION_UNRESOLVED: True")
    print("RAW_BRANCH_MISSING_DISTINCT_FROM_STRING_ZERO: True")
    print("NO_IDENTIFIER_OR_CANDIDATE_ADMISSION: True")
    print("PRIVATE_VALUES_NOT_DISCLOSED: True")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("CURRENT_VALIDITY: NOT_EVALUATED")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("EFLAW_ARTICLE_RESPONSE_LOCAL_AMBIGUITY_GUARD_CONTRACT_PASS")


if __name__ == "__main__":
    main()
