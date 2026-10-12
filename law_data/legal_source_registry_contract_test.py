# -*- coding: utf-8 -*-
"""No-network/no-write contract for descriptive legal-source inventory."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

from law_data.authority_source_scope import AuthoritySourceScope
from law_data.legal_jurisdiction_context import parse_legal_jurisdiction_context
from law_data.legal_source_registry import (
    LegalSourceIdentityConflictError,
    LegalSourceRecord,
    LegalSourceRegistry,
    LegalSourceVersionConflictError,
    build_legal_source_registry,
)


def rejects(exc: type[Exception], fn, *args, **kwargs) -> None:
    try:
        fn(*args, **kwargs)
    except exc:
        return
    raise AssertionError(f"Expected {exc.__name__}")


def ordinance(**overrides) -> LegalSourceRecord:
    # Synthetic IDs/dates/URI: contract fixtures, NOT retrieved law data.
    values = dict(
        source_system="TEST_REGISTRY",
        source_namespace="ordin",
        source_id="TEST-ORD-1",
        title="합성 시험용 조례",
        source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO",
        jurisdiction_code="11",
        version_id="00012",
        source_uri="https://example.go.kr/ordin/1",
        promulgation_date="2024-02-29",
        effective_date="2024-03-01",
        revision_label="테스트 개정",
    )
    values.update(overrides)
    return LegalSourceRecord(**values)


def main() -> None:
    seoul = ordinance()
    busan = ordinance(
        source_id="TEST-ORD-2", jurisdiction_code="26", version_id=None,
        promulgation_date=None, effective_date=None, source_uri=None,
    )
    national = LegalSourceRecord(
        source_system="TEST_REGISTRY", source_namespace="law",
        source_id="TEST-NAT-1", title="합성 국가 법령", source_type="NATIONAL_LAW",
        jurisdiction_level="NATIONAL", version_id="0000003",
    )
    subordinate = LegalSourceRecord(
        source_system="TEST_REGISTRY", source_namespace="law",
        source_id="TEST-NAT-2", title="합성 시행령", source_type="NATIONAL_SUBORDINATE",
        jurisdiction_level="NATIONAL", version_id="0000010",
    )
    basic = ordinance(
        source_id="TEST-BASIC-1", title="합성 기초자치단체 조례",
        jurisdiction_level="SIGUNGU", jurisdiction_code="11680",
    )

    assert seoul.version_id == "00012"  # Leading zeros must survive.
    assert seoul.to_dict()["source_identity_basis"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert seoul.to_dict()["current_validity_decision"] == "NOT_EVALUATED"
    assert seoul.to_dict()["legal_authority_decision"] == "NOT_EVALUATED"
    assert seoul.to_dict()["legal_applicability_decision"] == "NOT_EVALUATED"
    assert seoul.to_dict()["production_admission_decision"] == "NOT_EVALUATED"
    assert busan.version_id is None
    assert busan.effective_date is None
    assert national.jurisdiction_code is None
    assert subordinate.jurisdiction_level == "NATIONAL"
    assert basic.jurisdiction_code == "11680"

    # No date inference, latest-version inference, or current-law promotion.
    revised = ordinance(
        version_id="00013", title="합성 시험용 조례(명칭 변경)",
        promulgation_date="2025-02-28", effective_date=None,
    )
    unknown = ordinance(
        version_id=None, promulgation_date=None, effective_date=None,
    )
    reg = build_legal_source_registry([seoul, seoul, revised, unknown, busan, national, subordinate, basic])
    assert isinstance(reg, LegalSourceRegistry)
    assert isinstance(reg.records, tuple)
    assert len(reg.records) == 7  # Exact duplicate removed.
    assert len(reg.versions_for(*seoul.source_key)) == 3
    assert reg.version_exact(*seoul.source_key, "00012") == seoul
    assert reg.version_exact(*seoul.source_key, "00013") == revised
    assert reg.version_exact(*seoul.source_key, None) == unknown
    assert reg.version_exact(*seoul.source_key, "LATEST") is None
    assert reg.version_exact(*seoul.source_key, "00099") is None
    assert reg.versions_for("OTHER", "ordin", "TEST-ORD-1") == ()

    # Distinct provider namespaces may reuse an identifier without collision.
    shared_id_law = LegalSourceRecord(
        source_system="TEST_REGISTRY", source_namespace="law",
        source_id="TEST-ORD-1", title="합성 국가법령", source_type="NATIONAL_LAW",
        jurisdiction_level="NATIONAL",
    )
    assert len(LegalSourceRegistry((seoul, shared_id_law)).records) == 2

    # The same source version may not silently change its content/metadata.
    rejects(
        LegalSourceVersionConflictError, build_legal_source_registry,
        [seoul, ordinance(effective_date="2024-04-01")],
    )
    rejects(
        LegalSourceVersionConflictError, build_legal_source_registry,
        [seoul, ordinance(source_uri="https://example.go.kr/other")],
    )
    # One provider source ID cannot switch province, scope level, or source type.
    rejects(
        LegalSourceIdentityConflictError, build_legal_source_registry,
        [seoul, ordinance(version_id="00013", jurisdiction_code="26")],
    )
    rejects(
        LegalSourceIdentityConflictError, build_legal_source_registry,
        [seoul, ordinance(version_id="00013", jurisdiction_level="SIGUNGU", jurisdiction_code="11680")],
    )
    rejects(
        LegalSourceIdentityConflictError, build_legal_source_registry,
        [seoul, LegalSourceRecord(
            source_system="TEST_REGISTRY", source_namespace="ordin", source_id="TEST-ORD-1",
            title="합성 국가법령", source_type="NATIONAL_LAW", jurisdiction_level="NATIONAL",
        )],
    )

    # Syntactic region identity can be checked, but it grants no authority.
    seoul_pnu = parse_legal_jurisdiction_context("1168010300100120002")
    busan_pnu = parse_legal_jurisdiction_context("2635010500105240002")
    assert seoul.jurisdiction_code == seoul_pnu.sido_code
    assert seoul.jurisdiction_code != busan_pnu.sido_code
    scope = AuthoritySourceScope(
        region_binding=seoul.jurisdiction_code,
        source_uri=seoul.source_uri,
        source_role="PRIMARY",
    )
    assert scope.official_host_verified is False
    assert scope.region_binding_verified is False
    assert scope.authority_chain_verified is False

    # No counterfeit source verification, even with plausible metadata.
    rejects(ValueError, ordinance, source_state="SOURCE_VERIFIED")
    rejects(ValueError, ordinance, source_state="ENGINE_READY")
    review = ordinance(source_state="REVIEW_REQUIRED", source_id="TEST-ORD-3")
    assert review.to_dict()["legal_authority_decision"] == "NOT_EVALUATED"

    for kwargs in (
        {"source_id": ""}, {"source_id": 12}, {"source_namespace": " "},
        {"source_type": "OFFICIAL_NOTICE"},
        {"jurisdiction_level": "GU"},
        {"jurisdiction_code": "11680"},
        {"jurisdiction_code": "２６"},
        {"jurisdiction_code": "aa"},
        {"effective_date": "2024-02-30"},
        {"effective_date": "2024/02/01"},
        {"promulgation_date": "2023-02-29"},
        {"version_id": "  "},
        {"source_uri": "file:///local/document.pdf"},
        {"source_uri": "example.go.kr"},
    ):
        rejects(ValueError, ordinance, **kwargs)
    rejects(ValueError, ordinance, source_type="NATIONAL_LAW")
    rejects(ValueError, LegalSourceRecord,
        source_system="TEST_REGISTRY", source_namespace="ordin", source_id="ORD",
        title="합성 조례", source_type="LOCAL_ORDINANCE", jurisdiction_level="NATIONAL",
    )
    rejects(TypeError, LegalSourceRegistry, records=(seoul, {"source_id": "FORGED"}))
    rejects(TypeError, LegalSourceRegistry, records="not a record collection")

    try:
        seoul.title = "tampered"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("source records must be immutable")
    try:
        reg.records += (seoul,)
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("registry must be immutable")

    print("LEGAL_SOURCE_REGISTRY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
