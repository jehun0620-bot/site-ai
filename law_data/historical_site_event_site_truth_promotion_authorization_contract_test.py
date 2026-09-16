"""Contract test for the final non-executing historical SITE promotion permit."""
from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_production_integration_authorization import (
    BOUNDARY_NAME as PRODUCTION_BOUNDARY,
    HistoricalSiteEventProductionIntegrationAuthorization,
)
from law_data.historical_site_event_site_truth_promotion_authorization import (
    AUTHORIZED,
    REJECTED,
    authorize_historical_site_event_site_truth_promotion,
)
from law_data.historical_site_event_site_truth_promotion_pnu_binding_authorization import (
    AUTHORIZED as PNU_AUTHORIZED,
    BOUNDARY_NAME as PNU_BOUNDARY,
    HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization,
)

PNU = "1168010300100120000"
CONDITION = "TEST_HISTORICAL_CONDITION"
SOURCE = "RUNTIME_HISTORICAL_SITE_EVENT"


def pnu_binding():
    return HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization(
        boundary=PNU_BOUNDARY,
        status=PNU_AUTHORIZED,
        promotion_binding_present=True,
        promotion_binding_boundary_matched=True,
        promotion_binding_authorized=True,
        canonical_pnu_present=True,
        canonical_pnu_valid=True,
        requested_pnu_present=True,
        requested_pnu_valid=True,
        pnu_matched=True,
        bound_pnu=PNU,
        bound_condition=CONDITION,
        bound_state="FALSE",
        missing_gates=(),
        pnu_binding_authorized=True,
    )


def production(repair=None):
    repair = repair or {
        "condition": CONDITION,
        "before": "UNKNOWN",
        "after": "FALSE",
        "new_confidence": "HIGH",
        "new_source": SOURCE,
    }
    return HistoricalSiteEventProductionIntegrationAuthorization(
        boundary=PRODUCTION_BOUNDARY,
        execution_present=True,
        execution_boundary_matched=True,
        execution_succeeded=True,
        actual_repairs_aligned=True,
        original_rules_immutable=True,
        historical_provenance_preserved=True,
        execution_mode="CHANGED_TARGETS",
        actual_repair_count=1,
        expected_refresh_rule_count=1,
        changed_rule_indexes_aligned=True,
        missing_gates=(),
        production_integration_authorized=True,
        authorized_rules=(),
        authorized_repairs=(repair,),
    )


def main():
    pnu = pnu_binding()
    prod = production()
    assert pnu.authorized

    good = authorize_historical_site_event_site_truth_promotion(pnu, prod)
    assert good.status == AUTHORIZED
    assert good.authorized
    assert good.bound_pnu == PNU
    assert good.bound_condition == CONDITION
    assert good.bound_state == "FALSE"
    assert good.production_condition_matched
    assert good.production_state_matched
    assert good.production_provenance_preserved
    assert not good.site_truth_decision_allowed
    assert not good.site_truth_mutation_allowed
    assert not good.promotion_execution_allowed
    assert not good.production_registration_allowed
    assert not good.runtime_registration_allowed
    assert not good.public_api_exposure_allowed

    wrong_condition = authorize_historical_site_event_site_truth_promotion(
        pnu, production({"condition": "OTHER", "after": "FALSE", "new_source": SOURCE})
    )
    assert wrong_condition.status == REJECTED
    assert not wrong_condition.authorized
    assert "production_condition_matched" in wrong_condition.missing_gates

    wrong_state = authorize_historical_site_event_site_truth_promotion(
        pnu, production({"condition": CONDITION, "after": "TRUE", "new_source": SOURCE})
    )
    assert wrong_state.status == REJECTED
    assert not wrong_state.authorized
    assert "production_state_matched" in wrong_state.missing_gates

    wrong_source = authorize_historical_site_event_site_truth_promotion(
        pnu, production({"condition": CONDITION, "after": "FALSE", "new_source": "OTHER"})
    )
    assert wrong_source.status == REJECTED
    assert not wrong_source.authorized
    assert "production_provenance_preserved" in wrong_source.missing_gates

    unauthorized_pnu = authorize_historical_site_event_site_truth_promotion(
        replace(pnu, pnu_binding_authorized=False), prod
    )
    assert unauthorized_pnu.status == REJECTED
    assert not unauthorized_pnu.authorized

    unauthorized_production = authorize_historical_site_event_site_truth_promotion(
        pnu, replace(prod, production_integration_authorized=False)
    )
    assert unauthorized_production.status == REJECTED
    assert not unauthorized_production.authorized

    no_repairs = authorize_historical_site_event_site_truth_promotion(
        pnu, replace(prod, authorized_repairs=())
    )
    assert no_repairs.status == REJECTED
    assert not no_repairs.authorized
    assert "production_repairs_present" in no_repairs.missing_gates

    print("HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
