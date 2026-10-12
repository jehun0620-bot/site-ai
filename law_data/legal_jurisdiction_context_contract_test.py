# -*- coding: utf-8 -*-
"""Read-only contract for PNU-only jurisdiction identity; no API or snapshots."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

from law_data.authority_source_scope import AuthoritySourceScope
from law_data.legal_jurisdiction_context import (
    JurisdictionIdentityMismatchError,
    parse_legal_jurisdiction_context,
)

SEOUL_PNU = "1168010300100120002"
BUSAN_PNU = "2635010500105240002"


def _rejects(expected_exception: type[Exception], fn, *args, **kwargs) -> None:
    try:
        fn(*args, **kwargs)
    except expected_exception:
        return
    raise AssertionError(f"Expected {expected_exception.__name__}")


def main() -> None:
    seoul = parse_legal_jurisdiction_context(
        SEOUL_PNU,
        expected_sido_code="11",
        expected_sigungu_code="11680",
        expected_bjdong_code="10300",
    )
    assert seoul.pnu == SEOUL_PNU
    assert (seoul.sido_code, seoul.sigungu_code, seoul.bjdong_code) == (
        "11", "11680", "10300"
    )
    assert (seoul.land_division_code, seoul.main_no, seoul.sub_no) == (
        "1", "0012", "0002"
    )

    busan = parse_legal_jurisdiction_context(
        BUSAN_PNU,
        expected_sido_code="26",
        expected_sigungu_code="26350",
        expected_bjdong_code="10500",
    )
    assert (busan.sido_code, busan.sigungu_code, busan.bjdong_code) == (
        "26", "26350", "10500"
    )
    assert (busan.land_division_code, busan.main_no, busan.sub_no) == (
        "1", "0524", "0002"
    )
    assert parse_legal_jurisdiction_context(f"  {BUSAN_PNU}  ").pnu == BUSAN_PNU

    # A synthetic valid structure must remain parseable without whitelisting
    # Seoul/Busan or assuming an official municipality/ordinance exists.
    synthetic = parse_legal_jurisdiction_context("4168010300200120002")
    assert synthetic.sido_code == "41"
    assert synthetic.land_division_code == "2"
    assert synthetic.to_dict()["identity_basis"] == "PNU_STRUCTURE_ONLY"

    for value in (
        None,
        1168010300100120002,
        "",
        SEOUL_PNU[:-1],
        SEOUL_PNU + "0",
        SEOUL_PNU[:10] + "3" + SEOUL_PNU[11:],
        "abcdefghij100120002",
        "１１６８０１０３００１００１２０００２",
    ):
        _rejects(ValueError, parse_legal_jurisdiction_context, value)

    for expected_key, expected_value in (
        ("expected_sido_code", "26"),
        ("expected_sigungu_code", "26350"),
        ("expected_bjdong_code", "10500"),
    ):
        _rejects(
            JurisdictionIdentityMismatchError,
            parse_legal_jurisdiction_context,
            SEOUL_PNU,
            **{expected_key: expected_value},
        )
    for expected_key, expected_value in (
        ("expected_sido_code", "1"),
        ("expected_sigungu_code", "1168"),
        ("expected_bjdong_code", "abcde"),
        ("expected_sido_code", 11),
    ):
        _rejects(
            ValueError,
            parse_legal_jurisdiction_context,
            SEOUL_PNU,
            **{expected_key: expected_value},
        )

    result = busan.to_dict()
    assert result["legal_authority_decision"] == "NOT_EVALUATED"
    assert result["legal_applicability_decision"] == "NOT_EVALUATED"
    assert "authority_chain_verified" not in result
    assert "region_binding_verified" not in result
    assert "applicability" not in result

    # Structural PNU parsing may not create verified AuthoritySourceScope.
    scope = AuthoritySourceScope(region_binding=busan.sido_code)
    assert scope.region_binding_verified is False
    assert scope.authority_chain_verified is False

    try:
        busan.sido_code = "11"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Jurisdiction context must be immutable")

    print("LEGAL_JURISDICTION_CONTEXT_CONTRACT_PASS")


if __name__ == "__main__":
    main()
