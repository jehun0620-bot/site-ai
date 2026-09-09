from __future__ import annotations

from hybrid_spatial_notice_current_validity_resolver import (
    ACT_DESIGNATE,
    CURRENT_VALIDITY_UNKNOWN,
    resolve_current_validity,
)
from hybrid_spatial_notice_uqq700_validity_seed_adapter import (
    adapt_verified_uqq700_identity_to_validity_seed,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_VALIDITY_SEED_ADAPTER_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_VALIDITY_SEED_ADAPTER_REGRESSION"


def verified_identity() -> dict[str, object]:
    return {
        "target": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "verification_accepted": True,
        "official_designation_identity_verified": True,
        "preserved_provenance": {
            "document_id": "official-document-1",
            "notice_number": "성남시고시 제2000-1호",
            "issuing_authority": "성남시장",
            "effective_or_notice_date": "2000-01-01",
            "all_identity_fields_same_document": True,
        },
    }


def main() -> int:
    checks: list[tuple[str, bool]] = []

    seed = adapt_verified_uqq700_identity_to_validity_seed(verified_identity())
    acts = seed["verified_notice_acts"]

    checks.append(("verified Gate 1 can create one DESIGNATE seed", len(acts) == 1))
    checks.append(
        (
            "seed act is identity-verified DESIGNATE",
            len(acts) == 1
            and acts[0].act_type == ACT_DESIGNATE
            and acts[0].official_designation_identity_verified is True,
        )
    )
    checks.append(
        (
            "seed preserves notice number and effective date",
            len(acts) == 1
            and acts[0].notice_number == "성남시고시 제2000-1호"
            and acts[0].effective_date.isoformat() == "2000-01-01",
        )
    )
    checks.append(
        (
            "seed preserves authority provenance outside resolver act",
            seed["seed_provenance"]["issuing_authority"] == "성남시장",
        )
    )
    checks.append(
        (
            "adapter never infers amendment release or history completeness",
            seed["amend_continue_act_inferred"] is False
            and seed["release_act_inferred"] is False
            and seed["downstream_history_complete_inferred"] is False,
        )
    )

    validity = resolve_current_validity(
        acts,
        downstream_history_complete=False,
        search_no_hit=True,
    )
    checks.append(
        (
            "DESIGNATE seed alone cannot verify current validity",
            validity["status"] == CURRENT_VALIDITY_UNKNOWN
            and validity["current_validity_verified"] is False,
        )
    )
    checks.append(
        (
            "search no-hit remains non-dispositive",
            validity["history"]["search_no_hit"] is True
            and validity["history"]["search_no_hit_dispositive"] is False,
        )
    )
    checks.append(
        (
            "later gates and runtime remain closed",
            seed["current_validity_verified"] is False
            and seed["site_spatial_inclusion_verified"] is False
            and seed["minimum_registration_gate_satisfied"] is False
            and seed["runtime_registration_allowed"] is False,
        )
    )
    checks.append(
        (
            "safety inference remains disabled",
            seed["negative_evidence_allowed"] is False
            and seed["legal_absence_inference_allowed"] is False
            and seed["site_false_inference_allowed"] is False
            and seed["site_promotion_allowed"] is False,
        )
    )
    checks.append(
        (
            "adapter is pure and non-mutating",
            seed["production_wiring_applied"] is False
            and seed["runtime_registry_mutated"] is False
            and seed["site_mutated"] is False,
        )
    )

    bad_date = verified_identity()
    bad_date["preserved_provenance"] = dict(bad_date["preserved_provenance"])
    bad_date["preserved_provenance"]["effective_or_notice_date"] = "2000/01/01"
    rejected_date = adapt_verified_uqq700_identity_to_validity_seed(bad_date)
    checks.append(
        (
            "non-ISO date fails closed",
            rejected_date["seed_accepted"] is False
            and rejected_date["verified_notice_acts"] == [],
        )
    )

    unverified = verified_identity()
    unverified["official_designation_identity_verified"] = False
    rejected_identity = adapt_verified_uqq700_identity_to_validity_seed(unverified)
    checks.append(
        (
            "unverified Gate 1 fails closed",
            rejected_identity["seed_accepted"] is False
            and rejected_identity["verified_notice_acts"] == [],
        )
    )

    wrong_target = verified_identity()
    wrong_target["target"] = "다른구역"
    rejected_target = adapt_verified_uqq700_identity_to_validity_seed(wrong_target)
    checks.append(
        (
            "wrong target fails closed",
            rejected_target["seed_accepted"] is False
            and rejected_target["verified_notice_acts"] == [],
        )
    )

    missing_authority = verified_identity()
    missing_authority["preserved_provenance"] = dict(
        missing_authority["preserved_provenance"]
    )
    missing_authority["preserved_provenance"]["issuing_authority"] = ""
    rejected_authority = adapt_verified_uqq700_identity_to_validity_seed(
        missing_authority
    )
    checks.append(
        (
            "missing issuing authority fails closed",
            rejected_authority["seed_accepted"] is False
            and rejected_authority["verified_notice_acts"] == [],
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE VALIDITY SEED ADAPTER TEST")
    print("=" * 96)
    print("Current validity promotion: DISABLED")
    print("Amendment/release inference: DISABLED")
    print("History completeness inference: DISABLED")
    print("Production/runtime mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
