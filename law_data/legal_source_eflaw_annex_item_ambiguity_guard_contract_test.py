# -*- coding: utf-8 -*-
"""Fully synthetic offline EFLAW annex ambiguity barrier contract."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_annex_item_ambiguity_guard import (
    AMBIGUOUS, INELIGIBLE, UNIQUE_LOCAL,
    LegalSourceEflawAnnexItemAmbiguityInspection,
    inspect_legal_source_eflaw_annex_item_ambiguity,
)

SECRET = "SYNTHETIC_PRIVATE_OC_DO_NOT_EXPOSE"


def encode(units):
    return json.dumps({"법령": {"기본정보": {"시행일자": "20120106"},
                                 "별표": {"별표단위": units}}},
                      ensure_ascii=False).encode("utf-8")


def unit(number="1", branch="0", date="20120106", **extra):
    return {"별표번호": number, "별표가지번호": branch,
            "별표시행일자": date, **extra}


def rejected(fn, code):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        assert SECRET not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def safe(result):
    record = result.public_record()
    view = json.dumps(record, ensure_ascii=False)
    for forbidden in (SECRET, "OC=", "20120106", "20300230",
                      "별표번호", "별표가지번호", "별표내용", "https://", "MST="):
        assert forbidden not in view and forbidden not in repr(result)
    assert record["annex_date_candidate_join"] == "BLOCKED_ALL_UNATTESTED_SOURCE_IDENTITY"
    assert record["temporal_candidate_creation"] == "NOT_PERFORMED"
    assert record["collision_merging"] == "FORBIDDEN"
    assert record["array_index_identifier_promotion"] == "FORBIDDEN"
    assert record["missing_branch_auto_normalization"] == "FORBIDDEN"
    for field in ("official_item_identity_decision", "acquisition_authenticity_decision",
                  "official_origin_decision", "annex_legal_effect_decision",
                  "legal_applicability_decision", "production_admission_decision"):
        assert record[field] == "NOT_EVALUATED"


def main():
    cases = 0
    inspect = inspect_legal_source_eflaw_annex_item_ambiguity
    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")):
        r = inspect(encode([unit("1", "0"), unit("1", "1"), unit("2", "0")]))
        assert r.status == UNIQUE_LOCAL
        assert (r.annex_units_examined, r.annex_date_fields, r.eligible_units,
                r.distinct_local_pairs, r.collision_groups) == (3, 3, 3, 3, 0)
        safe(r)
        cases += 1

        # A set of 31 distinct raw pairs reproduces the STRUCTURAL count only.
        r = inspect(encode([unit(str(i % 28), str(i // 28)) for i in range(31)]))
        assert (r.annex_units_examined, r.distinct_local_pairs, r.collision_groups) == (31, 31, 0)
        safe(r)
        cases += 1

        # If two payload units reuse a pair, even if contents or dates agree,
        # their identity remains unresolved rather than silently merged.
        r = inspect(encode([unit("3", "0", extra=SECRET), unit("3", "0")]))
        assert r.status == AMBIGUOUS
        assert (r.collision_groups, r.collision_member_units,
                r.collision_excess_units, r.collision_date_variation_groups) == (1, 2, 1, 0)
        safe(r)
        cases += 1
        r = inspect(encode([unit("3", "0"), unit("3", "0", "20120201")]))
        assert r.collision_date_variation_groups == 1
        safe(r)
        cases += 1
        r = inspect(encode([unit("3", "0"), {"별표번호": "3", "별표가지번호": "0"}]))
        assert r.collision_date_unresolved_groups == 1
        cases += 1
        r = inspect(encode([unit("3", "0")] * 3))
        assert (r.collision_groups, r.collision_member_units, r.collision_excess_units) == (1, 3, 2)
        cases += 1

        # Missing is NOT zero or empty; neither is eligible. No fallback.
        for bad in (None, False, 0, "", [], {}):
            for field in ("별표번호", "별표가지번호"):
                broken = unit()
                broken[field] = bad
                r = inspect(encode([broken]))
                assert r.status == INELIGIBLE and r.ineligible_units == 1
                safe(r)
                cases += 1
        for field in ("별표번호", "별표가지번호"):
            broken = unit()
            del broken[field]
            r = inspect(encode([broken]))
            assert r.status == INELIGIBLE
            cases += 1

        # An ambiguous valid pair dominates unrelated invalid rows.
        r = inspect(encode([unit("3", "0"), unit("3", "0"), {"별표번호": "7"}]))
        assert r.status == AMBIGUOUS and r.ineligible_units == 1
        cases += 1
        # Even an empty list cannot issue an approval.
        r = inspect(encode([]))
        assert r.status == UNIQUE_LOCAL and r.distinct_local_pairs == 0
        safe(r)
        cases += 1

        # Date field is only a raw string; not an effective-on-day decision.
        for raw in ("20300230", "", SECRET):
            r = inspect(encode([unit("4", "0", raw)]))
            assert r.status == UNIQUE_LOCAL and r.annex_date_fields == 1
            safe(r)
            cases += 1
        for wrong_date in (None, {}, ["20120106"], 20120106):
            rejected(lambda v=wrong_date: inspect(encode([unit("4", "0", v)])),
                     "TEMPORAL_FIELD_TYPE_UNRESOLVED")
            cases += 1

        # No success-state fabrication via dataclasses.replace or mutation.
        r = inspect(encode([unit("1", "0"), unit("1", "0")]))
        rejected(lambda: replace(r, status=UNIQUE_LOCAL), "INCONSISTENT_ANNEX_AMBIGUITY_STATUS")
        cases += 1
        rejected(lambda: replace(r, eligible_units=7), "INCONSISTENT_ANNEX_ELIGIBILITY_COUNTS")
        cases += 1
        rejected(lambda: replace(r, distinct_local_pairs=17), "INCONSISTENT_ANNEX_PAIR_COUNTS")
        cases += 1
        rejected(lambda: replace(r, collision_groups=0), "INCONSISTENT_ANNEX_COLLISION_COUNTS")
        cases += 1
        rejected(lambda: LegalSourceEflawAnnexItemAmbiguityInspection(
            AMBIGUOUS, 2, 2, 2, 0, 1, 1, 2, 1, 0, 0),
                 "DIRECT_ANNEX_AMBIGUITY_RESULT_FORBIDDEN")
        cases += 1
        try:
            r.status = "SOURCE_VERIFIED"
        except (FrozenInstanceError, AttributeError):
            cases += 1
        else:
            raise AssertionError("RESULT_MUTABLE")

        # Shared JSON parser rejects duplicate keys and invalid structure.
        for bad, reason in (
            (b"", "TEMPORAL_RESPONSE_BYTE_BOUNDS_UNRESOLVED"),
            (b"{}", "TEMPORAL_EFLAW_ROOT_UNRESOLVED"),
            (b"{broken", "TEMPORAL_RESPONSE_JSON_UNRESOLVED"),
            ('{"법령":{"별표":{"별표단위":[],"별표단위":[]}}}'.encode(),
             "TEMPORAL_DUPLICATE_JSON_KEY"),
            ('{"법령":{"별표":{"별표단위":[null]}}}'.encode(),
             "TEMPORAL_UNIT_SHAPE_UNRESOLVED"),
            ('{"법령":{"별표":{"별표단위":{}}}}'.encode(),
             "TEMPORAL_UNIT_COLLECTION_UNRESOLVED"),
            ('{"법령":{}}'.encode(), "ANNEX_AMBIGUITY_UNITS_UNRESOLVED"),
        ):
            rejected(lambda data=bad: inspect(data), reason)
            cases += 1

    print("SYNTHETIC_ANNEX_ITEM_AMBIGUITY_CASES:", cases)
    print("MISSING_OR_EMPTY_BRANCH_IS_INELIGIBLE: True")
    print("REPEATED_RAW_ANNEX_PAIR_IS_UNRESOLVED: True")
    print("UNIQUE_LOCAL_DOES_NOT_PERMIT_CANDIDATE_JOIN: True")
    print("RAW_VALUES_NOT_DISCLOSED: True")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("EFLAW_ANNEX_RESPONSE_LOCAL_AMBIGUITY_GUARD_CONTRACT_PASS")


if __name__ == "__main__":
    main()
