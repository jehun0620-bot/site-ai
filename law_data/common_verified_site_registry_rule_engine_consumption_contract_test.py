"""Contract test for common verified SITE registry Rule Engine consumption."""

from dataclasses import replace

from law_data.common_verified_site_registry_live_consumption import (
    CommonVerifiedSiteRegistryLiveConsumption,
    DISTRICT_UNIT_PLAN,
    HISTORICAL,
    BOUNDARY_NAME,
)
from law_data.rule_evaluation_pipeline import evaluate_site_rules


def _common_registry(source_family, registry):
    return CommonVerifiedSiteRegistryLiveConsumption(
        boundary=BOUNDARY_NAME,
        source_family=source_family,
        source_authorization_verified=True,
        candidate_registry_valid=True,
        verified_site_registry=registry,
        missing_gates=(),
        consumption_ready=True,
    )


def main():
    # --------------------------------------------------------
    # historical common input
    # --------------------------------------------------------
    historical = _common_registry(
        HISTORICAL,
        {
            "서울도심": {
                "state": "FALSE",
                "confidence": "HIGH",
                "source": "RUNTIME_HISTORICAL_SITE_EVENT",
            }
        },
    )

    historical_result = evaluate_site_rules(
        common_verified_site_registry=historical,
    )

    assert historical_result["site_registry"]["서울도심"]["state"] == "FALSE"
    assert (
        historical_result["site_registry"]["서울도심"]["source"]
        == "RUNTIME_HISTORICAL_SITE_EVENT"
    )

    # --------------------------------------------------------
    # district-unit-plan common input
    # --------------------------------------------------------
    district = _common_registry(
        DISTRICT_UNIT_PLAN,
        {
            "지구단위계획": {
                "state": "TRUE",
                "confidence": "HIGH",
                "source": "RUNTIME_DISTRICT_UNIT_PLAN_HYBRID",
                "pnu": "1168010600100010000",
                "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
            }
        },
    )

    district_result = evaluate_site_rules(
        common_verified_site_registry=district,
    )

    assert district_result["site_registry"]["지구단위계획"]["state"] == "TRUE"
    assert (
        district_result["site_registry"]["지구단위계획"]["source"]
        == "RUNTIME_DISTRICT_UNIT_PLAN_HYBRID"
    )

    # --------------------------------------------------------
    # forged common boundary must fail closed
    # --------------------------------------------------------
    forged = replace(
        district,
        boundary="FORGED",
    )

    try:
        evaluate_site_rules(
            common_verified_site_registry=forged,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "forged common verified registry was not rejected"
        )

    # --------------------------------------------------------
    # historical + common simultaneous consumption prohibited
    # --------------------------------------------------------
    try:
        evaluate_site_rules(
            historical_registry_authorization=object(),
            common_verified_site_registry=district,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "dual registry consumption was not rejected"
        )

    print(
        "COMMON_VERIFIED_SITE_REGISTRY_RULE_ENGINE_CONSUMPTION_CONTRACT_PASS"
    )


if __name__ == "__main__":
    main()
