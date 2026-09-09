from __future__ import annotations

from hybrid_spatial_notice_historical_candidate_resolver import (
    HistoricalNoticeCandidateInput,
    qualify_historical_notice_candidate,
)
from hybrid_spatial_notice_uqq700_historical_identity_bridge import (
    Uqq700HistoricalIdentityProvenance,
    bridge_uqq700_historical_candidate_to_identity,
)


def _candidate(**overrides):
    values = {
        "url": "https://example.go.kr/notice/view.do?id=1",
        "title": "개발밀도관리구역 지정 고시",
        "notice_number": "성남시고시 제2000-1호",
        "published_date": "2000-01-01",
        "authority_source_qualified": True,
        "target_name_present": True,
        "document_role": "DESIGNATION_NOTICE_CANDIDATE",
    }
    values.update(overrides)
    return qualify_historical_notice_candidate(HistoricalNoticeCandidateInput(**values))


def main() -> None:
    checks: list[tuple[str, bool]] = []

    candidate = _candidate()
    baseline = bridge_uqq700_historical_candidate_to_identity(candidate)
    checks.extend(
        [
            (
                "qualified candidate alone cannot verify identity",
                baseline["official_designation_identity_verified"] is False,
            ),
            (
                "designation act is not inferred from document role",
                baseline["mapping"]["designation_act_bound_inferred"] is False
                and baseline["explicit_provenance"]["designation_act_bound"] is False,
            ),
            (
                "issuing authority is not inferred",
                baseline["mapping"]["issuing_authority_inferred"] is False
                and baseline["explicit_provenance"]["issuing_authority"] == "",
            ),
            (
                "published date is not automatically promoted",
                baseline["identity_result"]["provenance"]["effective_or_notice_date"] == "",
            ),
            (
                "no production or runtime mutation",
                baseline["production_wiring_applied"] is False
                and baseline["runtime_registry_mutated"] is False
                and baseline["site_mutated"] is False,
            ),
        ]
    )

    full = bridge_uqq700_historical_candidate_to_identity(
        candidate,
        provenance=Uqq700HistoricalIdentityProvenance(
            designation_act_bound=True,
            issuing_authority="성남시장",
            effective_or_notice_date_verified=True,
        ),
    )
    checks.extend(
        [
            (
                "complete explicit provenance can verify identity",
                full["official_designation_identity_verified"] is True,
            ),
            (
                "verified published date is passed explicitly",
                full["identity_result"]["provenance"]["effective_or_notice_date"]
                == "2000-01-01",
            ),
            (
                "identity alone still cannot verify validity",
                full["identity_result"]["verification"]["current_validity_verified"]
                is False,
            ),
            (
                "identity alone still cannot verify spatial inclusion",
                full["identity_result"]["verification"]["site_spatial_inclusion_verified"]
                is False,
            ),
            (
                "identity alone still cannot register runtime",
                full["identity_result"]["verification"]["runtime_registration_allowed"]
                is False,
            ),
        ]
    )

    missing_notice = bridge_uqq700_historical_candidate_to_identity(
        _candidate(notice_number=""),
        provenance=Uqq700HistoricalIdentityProvenance(
            designation_act_bound=True,
            issuing_authority="성남시장",
            effective_or_notice_date_verified=True,
        ),
    )
    checks.append(
        (
            "missing notice number fails closed",
            missing_notice["official_designation_identity_verified"] is False,
        )
    )

    unqualified = bridge_uqq700_historical_candidate_to_identity(
        _candidate(authority_source_qualified=False),
        provenance=Uqq700HistoricalIdentityProvenance(
            designation_act_bound=True,
            issuing_authority="성남시장",
            effective_or_notice_date_verified=True,
        ),
    )
    checks.append(
        (
            "unqualified historical candidate fails closed",
            unqualified["official_designation_identity_verified"] is False,
        )
    )

    no_date_attestation = bridge_uqq700_historical_candidate_to_identity(
        candidate,
        provenance=Uqq700HistoricalIdentityProvenance(
            designation_act_bound=True,
            issuing_authority="성남시장",
            effective_or_notice_date_verified=False,
        ),
    )
    checks.append(
        (
            "date without explicit attestation fails closed",
            no_date_attestation["official_designation_identity_verified"] is False,
        )
    )

    print("=" * 88)
    print("UQQ700 HYBRID_SPATIAL_NOTICE HISTORICAL IDENTITY BRIDGE TEST")
    print("=" * 88)
    for name, passed in checks:
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(passed for _, passed in checks)
    print()
    print(
        "CLASSIFICATION: "
        "UQQ700_HYBRID_SPATIAL_NOTICE_HISTORICAL_IDENTITY_BRIDGE_PASS"
        if all_pass
        else "CLASSIFICATION: UQQ700_HYBRID_SPATIAL_NOTICE_HISTORICAL_IDENTITY_BRIDGE_FAIL"
    )
    print(f"all_pass: {all_pass}")
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
