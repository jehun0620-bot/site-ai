"""Contract test for historical SITE-truth pre-promotion binding authorization."""
from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_candidate_condition_binding_authorization import (
    authorize_historical_site_event_candidate_condition_binding,
)
from law_data.historical_site_event_candidate_repair_consistency_authorization import (
    authorize_historical_site_event_candidate_repair_consistency,
)
from law_data.historical_site_event_parcel_applicability_evidence import HistoricalSiteEventParcelEvidenceInput
from law_data.historical_site_event_site_applicability_admission import admit_historical_site_event_site_applicability
from law_data.historical_site_event_site_registry_mutation_executor import (
    BOUNDARY_NAME as MUTATION_BOUNDARY,
    HistoricalSiteEventSiteRegistryMutationExecution,
)
from law_data.historical_site_event_site_truth_promotion_binding_authorization import (
    AUTHORIZED,
    REJECTED,
    authorize_historical_site_event_site_truth_promotion_binding,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)
from law_data.historical_trusted_internal_source_handoff_authorization import (
    BOUNDARY_NAME as HANDOFF_BOUNDARY,
    HistoricalTrustedInternalSourceHandoffAuthorization,
)
from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.regulation_resolution_profile_resolver_family_input_admission import HISTORICAL_SITE_EVENT
from law_data.regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    RegulationResolutionProfileSiteDecisionEligibility,
)

PNU = "1168010300100120000"
CONDITION = "TEST_HISTORICAL_CONDITION"


def applicability():
    eligibility = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )
    evidence = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="TEST-EVENT",
        official_source_verified=True,
        parcel_binding_verified=True,
        event_binding_verified=True,
    )
    result = admit_historical_site_event_site_applicability(
        eligibility,
        {"pnu": PNU, "identity_status": "COMPLETE"},
        evidence,
    )
    assert result.admitted
    return result


def handoff(condition=CONDITION):
    repairs = ({
        "condition": condition,
        "before": "UNKNOWN",
        "after": "FALSE",
        "new_confidence": "HIGH",
        "new_source": PROVENANCE,
    },)
    return HistoricalTrustedInternalSourceHandoffAuthorization(
        boundary=HANDOFF_BOUNDARY,
        source_authorization_present=True,
        source_authorization_boundary_matched=True,
        trusted_source_authorized=True,
        channel_matched=True,
        provenance_matched=True,
        rules_present=True,
        repairs_present=True,
        repair_provenance_preserved=True,
        missing_gates=(),
        handoff_authorized=True,
        channel=CHANNEL,
        provenance=PROVENANCE,
        handoff_rules=(),
        handoff_repairs=repairs,
    )


def mutation(condition=CONDITION, state="FALSE"):
    historical_source = PROVENANCE
    committed = {
        "type": HISTORICAL_CONDITION_TYPE,
        "state": state,
        "source": HISTORICAL_REGISTRY_SOURCE,
        "historical_source": historical_source,
        "runtime_source": historical_source,
    }
    return HistoricalSiteEventSiteRegistryMutationExecution(
        boundary=MUTATION_BOUNDARY,
        mutation_target="RULE_ENGINE_SITE_REGISTRY_HISTORICAL_OVERLAY",
        authorization_present=True,
        authorization_boundary_matched=True,
        mutation_target_matched=True,
        mutation_commit_authorized=True,
        historical_condition_name_present=True,
        historical_condition_present=True,
        historical_type_preserved=True,
        state_valid=True,
        registry_source_matched=True,
        original_historical_source_preserved=True,
        authorized_snapshot_present=True,
        authorized_snapshot_aligned=True,
        authorization_contract_aligned=True,
        missing_gates=(),
        mutation_executed=True,
        site_registry_overlaid=True,
        committed_registry={condition: committed},
        committed_historical_condition_name=condition,
        committed_historical_condition=committed,
    )


def main():
    app = applicability()
    ho = handoff()
    consistency = authorize_historical_site_event_candidate_repair_consistency(app, ho)
    binding = authorize_historical_site_event_candidate_condition_binding(app, ho)
    assert consistency.authorized
    assert binding.authorized

    good = authorize_historical_site_event_site_truth_promotion_binding(app, consistency, binding, mutation())
    assert good.status == AUTHORIZED
    assert good.authorized
    assert good.canonical_pnu == PNU
    assert good.candidate_state == "FALSE"
    assert good.bound_condition == CONDITION
    assert good.committed_condition_name == CONDITION
    assert not good.site_truth_decision_allowed
    assert not good.site_truth_mutation_allowed
    assert not good.site_promotion_allowed
    assert not good.production_registration_allowed
    assert not good.runtime_registration_allowed

    wrong_condition = authorize_historical_site_event_site_truth_promotion_binding(
        app, consistency, binding, mutation(condition="OTHER_CONDITION")
    )
    assert wrong_condition.status == REJECTED
    assert not wrong_condition.authorized
    assert "condition_identity_matched" in wrong_condition.missing_gates

    wrong_state = authorize_historical_site_event_site_truth_promotion_binding(
        app, consistency, binding, mutation(state="TRUE")
    )
    assert wrong_state.status == REJECTED
    assert not wrong_state.authorized
    assert "state_matched" in wrong_state.missing_gates

    unauthorized_consistency = authorize_historical_site_event_site_truth_promotion_binding(
        app, replace(consistency, consistency_authorized=False), binding, mutation()
    )
    assert unauthorized_consistency.status == REJECTED
    assert not unauthorized_consistency.authorized

    unauthorized_binding = authorize_historical_site_event_site_truth_promotion_binding(
        app, consistency, replace(binding, binding_authorized=False), mutation()
    )
    assert unauthorized_binding.status == REJECTED
    assert not unauthorized_binding.authorized

    unexecuted = authorize_historical_site_event_site_truth_promotion_binding(
        app, consistency, binding, replace(mutation(), mutation_executed=False)
    )
    assert unexecuted.status == REJECTED
    assert not unexecuted.authorized

    print("HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_BINDING_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
