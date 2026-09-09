from __future__ import annotations

from hybrid_spatial_notice_uqq700_identity_evidence_adapter import (
    Uqq700IdentityEvidenceInput,
    adapt_uqq700_identity_evidence,
)


def check(name: str, value: bool) -> bool:
    print(f"{name}: {'PASS' if value else 'FAIL'}")
    return value


def main() -> None:
    print("=" * 88)
    print("UQQ700 HYBRID_SPATIAL_NOTICE IDENTITY EVIDENCE ADAPTER TEST")
    print("=" * 88)

    cases = []

    empty = adapt_uqq700_identity_evidence(Uqq700IdentityEvidenceInput())
    cases += [
        check("empty input stays unverified", empty["official_designation_identity_verified"] is False),
        check("empty input no discovery", empty["discovery_performed"] is False),
        check("empty input no legal inference", empty["legal_inference_performed"] is False),
        check("empty input no production wiring", empty["production_wiring_applied"] is False),
        check("empty input no runtime mutation", empty["runtime_registry_mutated"] is False),
        check("empty input no SITE mutation", empty["site_mutated"] is False),
    ]

    complete = Uqq700IdentityEvidenceInput(
        candidate_qualified=True,
        authority_source_qualified=True,
        target_name_bound=True,
        designation_act_bound=True,
        notice_number="성남시 고시 제2000-1호",
        issuing_authority="성남시장",
        effective_or_notice_date="2000-01-01",
        source_url="https://example.go.kr/official-notice",
    )
    verified = adapt_uqq700_identity_evidence(complete)
    cases += [
        check("complete explicit evidence verifies identity", verified["official_designation_identity_verified"] is True),
        check("identity alone does not verify validity", verified["verification"]["current_validity_verified"] is False),
        check("identity alone does not verify spatial inclusion", verified["verification"]["site_spatial_inclusion_verified"] is False),
        check("identity alone cannot register runtime", verified["verification"]["runtime_registration_allowed"] is False),
        check("identity alone cannot promote SITE", verified["verification"]["site_promotion_allowed"] is False),
    ]

    required_text_fields = ["notice_number", "issuing_authority", "effective_or_notice_date"]
    for field in required_text_fields:
        values = complete.__dict__.copy()
        values[field] = ""
        result = adapt_uqq700_identity_evidence(Uqq700IdentityEvidenceInput(**values))
        cases.append(check(f"missing {field} fails closed", result["official_designation_identity_verified"] is False))

    required_boolean_fields = [
        "candidate_qualified",
        "authority_source_qualified",
        "target_name_bound",
        "designation_act_bound",
    ]
    for field in required_boolean_fields:
        values = complete.__dict__.copy()
        values[field] = False
        result = adapt_uqq700_identity_evidence(Uqq700IdentityEvidenceInput(**values))
        cases.append(check(f"false {field} fails closed", result["official_designation_identity_verified"] is False))

    diagnostic = adapt_uqq700_identity_evidence(
        Uqq700IdentityEvidenceInput(),
        diagnostics={"search_hit": True, "http_200": True, "negative_evidence": True},
    )
    cases += [
        check("diagnostics cannot verify identity", diagnostic["official_designation_identity_verified"] is False),
        check("negative evidence remains disabled", diagnostic["verification"]["negative_evidence_allowed"] is False),
        check("legal absence remains disabled", diagnostic["verification"]["legal_absence_inference_allowed"] is False),
        check("SITE FALSE remains disabled", diagnostic["verification"]["site_false_inference_allowed"] is False),
    ]

    all_pass = all(cases)
    print()
    print("CLASSIFICATION: UQQ700_HYBRID_SPATIAL_NOTICE_IDENTITY_EVIDENCE_ADAPTER_PASS" if all_pass else "CLASSIFICATION: UQQ700_HYBRID_SPATIAL_NOTICE_IDENTITY_EVIDENCE_ADAPTER_FAIL")
    print(f"all_pass: {all_pass}")
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
