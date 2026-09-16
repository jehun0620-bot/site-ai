"""Contract test for canonical-PNU binding of historical promotion candidates."""
from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_site_truth_promotion_binding_authorization import (
    AUTHORIZED as UPSTREAM_AUTHORIZED,
    BOUNDARY_NAME as UPSTREAM_BOUNDARY,
    HistoricalSiteEventSiteTruthPromotionBindingAuthorization,
)
from law_data.historical_site_event_site_truth_promotion_pnu_binding_authorization import (
    AUTHORIZED,
    REJECTED,
    authorize_historical_site_event_site_truth_promotion_pnu_binding,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"
CONDITION = "TEST_HISTORICAL_CONDITION"


def promotion_binding():
    return HistoricalSiteEventSiteTruthPromotionBindingAuthorization(
        boundary=UPSTREAM_BOUNDARY,
        status=UPSTREAM_AUTHORIZED,
        applicability_admitted=True,
        canonical_pnu=PNU,
        candidate_present=True,
        candidate_state="FALSE",
        consistency_present=True,
        consistency_boundary_matched=True,
        consistency_authorized=True,
        condition_binding_present=True,
        condition_binding_boundary_matched=True,
        condition_binding_authorized=True,
        bound_condition=CONDITION,
        mutation_execution_present=True,
        mutation_execution_boundary_matched=True,
        mutation_executed=True,
        committed_condition_name=CONDITION,
        condition_identity_matched=True,
        committed_condition_present=True,
        committed_state="FALSE",
        state_matched=True,
        historical_type_preserved=True,
        registry_source_matched=True,
        original_historical_source_preserved=True,
        missing_gates=(),
        promotion_binding_authorized=True,
    )


def main():
    upstream = promotion_binding()
    assert upstream.authorized

    good = authorize_historical_site_event_site_truth_promotion_pnu_binding(upstream, PNU)
    assert good.status == AUTHORIZED
    assert good.authorized
    assert good.bound_pnu == PNU
    assert good.bound_condition == CONDITION
    assert good.bound_state == "FALSE"
    assert not good.site_truth_decision_allowed
    assert not good.site_truth_mutation_allowed
    assert not good.site_promotion_allowed
    assert not good.production_registration_allowed
    assert not good.runtime_registration_allowed

    cross_pnu = authorize_historical_site_event_site_truth_promotion_pnu_binding(upstream, OTHER_PNU)
    assert cross_pnu.status == REJECTED
    assert not cross_pnu.authorized
    assert not cross_pnu.bound_pnu
    assert "pnu_matched" in cross_pnu.missing_gates

    invalid_pnu = authorize_historical_site_event_site_truth_promotion_pnu_binding(upstream, "11680")
    assert invalid_pnu.status == REJECTED
    assert not invalid_pnu.authorized
    assert "requested_pnu_valid" in invalid_pnu.missing_gates

    invalid_upstream_pnu = authorize_historical_site_event_site_truth_promotion_pnu_binding(
        replace(upstream, canonical_pnu="BAD"), PNU
    )
    assert invalid_upstream_pnu.status == REJECTED
    assert not invalid_upstream_pnu.authorized
    assert "canonical_pnu_valid" in invalid_upstream_pnu.missing_gates

    unauthorized_upstream = authorize_historical_site_event_site_truth_promotion_pnu_binding(
        replace(upstream, promotion_binding_authorized=False), PNU
    )
    assert unauthorized_upstream.status == REJECTED
    assert not unauthorized_upstream.authorized
    assert "promotion_binding_authorized" in unauthorized_upstream.missing_gates

    missing_condition = authorize_historical_site_event_site_truth_promotion_pnu_binding(
        replace(upstream, bound_condition=""), PNU
    )
    assert missing_condition.status == REJECTED
    assert not missing_condition.authorized
    assert "bound_condition_present" in missing_condition.missing_gates

    print("HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_PNU_BINDING_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
