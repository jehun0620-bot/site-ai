"""Contract test for isolated historical SITE-truth promotion execution."""
from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_site_truth_promotion_authorization import (
    AUTHORIZED,
    BOUNDARY_NAME as AUTHORIZATION_BOUNDARY,
    HistoricalSiteEventSiteTruthPromotionAuthorization,
)
from law_data.historical_site_event_site_truth_promotion_executor import (
    EXECUTED,
    REJECTED,
    execute_historical_site_event_site_truth_promotion,
)

PNU = "1168010300100120000"
CONDITION = "TEST_HISTORICAL_CONDITION"


def authorization():
    return HistoricalSiteEventSiteTruthPromotionAuthorization(
        boundary=AUTHORIZATION_BOUNDARY,
        status=AUTHORIZED,
        pnu_binding_present=True,
        pnu_binding_boundary_matched=True,
        pnu_binding_authorized=True,
        bound_pnu=PNU,
        bound_condition=CONDITION,
        bound_state="FALSE",
        production_authorization_present=True,
        production_authorization_boundary_matched=True,
        production_integration_authorized=True,
        production_repairs_present=True,
        production_condition_matched=True,
        production_state_matched=True,
        production_provenance_preserved=True,
        missing_gates=(),
        promotion_authorized=True,
    )


def main():
    auth = authorization()
    assert auth.authorized

    good = execute_historical_site_event_site_truth_promotion(auth)
    assert good.status == EXECUTED
    assert good.executed
    assert good.bound_pnu == PNU
    assert good.bound_condition == CONDITION
    assert good.bound_state == "FALSE"
    assert good.promoted_condition_present
    assert good.promoted_condition["type"] == "SITE"
    assert good.promoted_condition["state"] == "FALSE"
    assert good.promoted_condition["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"
    assert good.promoted_condition["pnu"] == PNU
    assert good.promoted_condition["runtime"] is True
    assert good.promoted_condition["historical"] is True
    assert not good.site_registry_mutated
    assert not good.rule_engine_called
    assert not good.builder_modified
    assert not good.runtime_registered
    assert not good.public_api_exposed

    unauthorized = execute_historical_site_event_site_truth_promotion(
        replace(auth, promotion_authorized=False)
    )
    assert unauthorized.status == REJECTED
    assert not unauthorized.executed
    assert not unauthorized.promoted_condition
    assert "promotion_authorized" in unauthorized.missing_gates

    wrong_pnu = execute_historical_site_event_site_truth_promotion(
        replace(auth, bound_pnu="11680")
    )
    assert wrong_pnu.status == REJECTED
    assert not wrong_pnu.executed
    assert "bound_pnu_valid" in wrong_pnu.missing_gates

    missing_condition = execute_historical_site_event_site_truth_promotion(
        replace(auth, bound_condition="")
    )
    assert missing_condition.status == REJECTED
    assert not missing_condition.executed
    assert "bound_condition_present" in missing_condition.missing_gates

    invalid_state = execute_historical_site_event_site_truth_promotion(
        replace(auth, bound_state="UNKNOWN")
    )
    assert invalid_state.status == REJECTED
    assert not invalid_state.executed
    assert "bound_state_valid" in invalid_state.missing_gates

    print("HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_EXECUTOR_CONTRACT_PASS")


if __name__ == "__main__":
    main()
