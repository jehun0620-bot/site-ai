from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from law_data.historical_history_completeness import (
    HistoricalHistoryCompletenessAssessment,
)
from law_data.historical_site_event_qualification import (
    HistoricalSiteEventQualificationAssessment,
)
from law_data.historical_site_event_resolution_composition import (
    TRUE_CANDIDATE,
    UNKNOWN,
    evaluate_historical_site_event_resolution_composition,
)
from law_data.regulation_authority_requirement import (
    RegulationAuthorityRequirementAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_source_policy_requirement import (
    RegulationSourcePolicyRequirementAssessment,
)


CLASSIFICATION = (
    "STEP26_HISTORICAL_SITE_EVENT_RESOLUTION_COMPOSITION_BOUNDARY_"
    "TERMINALLY_RECONCILED"
)


def _profile(*, resolution_type: str = "HISTORICAL_SITE_EVENT") -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type=resolution_type,
        standard_code=None,
        standard_code_verified=False,
        authority_requirements=("COMPETENT AUTHORITY VERIFIED",),
        source_policy_requirements=(
            "HISTORY COMPLETENESS VERIFIED",
            "PROVENANCE VERIFIED",
        ),
    )


def _qualification(verified: bool = True) -> HistoricalSiteEventQualificationAssessment:
    return HistoricalSiteEventQualificationAssessment(
        boundary="HISTORICAL_SITE_EVENT_QUALIFICATION",
        historical_event_identity_verified=verified,
        historical_site_applicability_verified=verified,
        temporal_relation_verified=verified,
        verified_gate_count=3 if verified else 0,
        required_gate_count=3,
        missing_gates=() if verified else ("historical_event_identity_verified",),
        qualifying_historical_event_verified=verified,
    )


def _completeness(verified: bool = True) -> HistoricalHistoryCompletenessAssessment:
    return HistoricalHistoryCompletenessAssessment(
        target_identity_verified=verified,
        coverage_scope_defined=verified,
        coverage_requirements_declared=verified,
        required_coverage_items=("OFFICIAL_HISTORY_SCOPE",) if verified else (),
        verified_coverage_items=("OFFICIAL_HISTORY_SCOPE",) if verified else (),
        missing_coverage_items=() if verified else ("OFFICIAL_HISTORY_SCOPE",),
        unexpected_verified_items=(),
        unresolved_gaps=(),
        unresolved_gap_present=False,
        history_completeness_verified=verified,
    )


def _authority(
    profile_name: str = "도시지역편입해제구역",
    satisfied: bool = True,
) -> RegulationAuthorityRequirementAssessment:
    return RegulationAuthorityRequirementAssessment(
        profile_present=True,
        profile_name=profile_name,
        scope_target_regulation=profile_name,
        condition_identity_aligned=True,
        authority_requirements=("COMPETENT AUTHORITY VERIFIED",),
        source_policy_requirements=(
            "HISTORY COMPLETENESS VERIFIED",
            "PROVENANCE VERIFIED",
        ),
        authority_requirements_declared=True,
        source_policy_requirements_declared=True,
        authority_chain_verified=satisfied,
        target_regulation_compatibility_verified=satisfied,
        target_regulation_compatible=True if satisfied else None,
        authority_requirement_satisfied=satisfied,
    )


def _source_policy(
    profile_name: str = "도시지역편입해제구역",
    satisfied: bool = True,
) -> RegulationSourcePolicyRequirementAssessment:
    requirements = (
        "HISTORY COMPLETENESS VERIFIED",
        "PROVENANCE VERIFIED",
    )
    return RegulationSourcePolicyRequirementAssessment(
        profile_present=True,
        profile_name=profile_name,
        source_policy_requirements=requirements,
        source_policy_requirements_declared=True,
        verified_requirements=requirements if satisfied else (),
        missing_requirements=() if satisfied else requirements,
        unexpected_requirements=(),
        source_policy_requirement_satisfied=satisfied,
    )


def _evaluate(
    *,
    profile: RegulationResolutionProfile | None = None,
    qualification: HistoricalSiteEventQualificationAssessment | None = None,
    completeness: HistoricalHistoryCompletenessAssessment | None = None,
    authority: RegulationAuthorityRequirementAssessment | None = None,
    source_policy: RegulationSourcePolicyRequirementAssessment | None = None,
):
    return evaluate_historical_site_event_resolution_composition(
        _profile() if profile is None else profile,
        _qualification() if qualification is None else qualification,
        _completeness() if completeness is None else completeness,
        _authority() if authority is None else authority,
        _source_policy() if source_policy is None else source_policy,
    )


def test_missing_inputs_fail_closed_to_unknown() -> None:
    result = evaluate_historical_site_event_resolution_composition(
        None, None, None, None, None
    )
    assert result.resolution_candidate == UNKNOWN
    assert result.positive_gate_satisfied is False


def test_each_required_positive_axis_is_independently_required() -> None:
    cases = (
        {"qualification": _qualification(False)},
        {"completeness": _completeness(False)},
        {"authority": _authority(satisfied=False)},
        {"source_policy": _source_policy(satisfied=False)},
    )
    for overrides in cases:
        result = _evaluate(**overrides)
        assert result.resolution_candidate == UNKNOWN
        assert result.positive_gate_satisfied is False


def test_profile_must_be_historical_site_event() -> None:
    result = _evaluate(profile=_profile(resolution_type="SNAPSHOT"))
    assert result.resolution_candidate == UNKNOWN
    assert result.historical_resolution_type_matched is False


def test_requirement_assessments_must_align_to_same_profile() -> None:
    authority_mismatch = _evaluate(authority=_authority(profile_name="OTHER"))
    source_policy_mismatch = _evaluate(
        source_policy=_source_policy(profile_name="OTHER")
    )
    assert authority_mismatch.resolution_candidate == UNKNOWN
    assert authority_mismatch.authority_profile_aligned is False
    assert source_policy_mismatch.resolution_candidate == UNKNOWN
    assert source_policy_mismatch.source_policy_profile_aligned is False


def test_truthy_non_bool_positive_fields_do_not_promote() -> None:
    qualification = replace(
        _qualification(), qualifying_historical_event_verified=1
    )
    completeness = replace(_completeness(), history_completeness_verified="yes")
    authority = replace(_authority(), authority_requirement_satisfied=1)
    source_policy = replace(
        _source_policy(), source_policy_requirement_satisfied="verified"
    )

    for overrides in (
        {"qualification": qualification},
        {"completeness": completeness},
        {"authority": authority},
        {"source_policy": source_policy},
    ):
        assert _evaluate(**overrides).resolution_candidate == UNKNOWN


def test_all_explicit_positive_gates_yield_true_candidate_only() -> None:
    result = _evaluate()
    assert result.positive_gate_satisfied is True
    assert result.missing_gates == ()
    assert result.resolution_candidate == TRUE_CANDIDATE

    payload = result.to_dict()
    assert payload["negative_evidence_inference_allowed"] is False
    assert payload["legal_absence_inference_allowed"] is False
    assert payload["negative_resolution_generated"] is False
    assert payload["site_state_mutated"] is False
    assert payload["rule_engine_state_mutated"] is False
    assert payload["production_wiring_applied"] is False
    assert payload["runtime_registry_mutated"] is False
    assert payload["public_api_exposed"] is False


def test_composition_has_no_runtime_search_registry_or_output_mutation_surface() -> None:
    source = Path(
        "law_data/historical_site_event_resolution_composition.py"
    ).read_text(encoding="utf-8")
    forbidden_tokens = (
        "requests.",
        "httpx.",
        "write_text(",
        "write_bytes(",
        "def register_",
        "def register_runtime",
        "def promote_",
    )
    for token in forbidden_tokens:
        assert token not in source, token


def test_no_auto_wiring_into_runtime_or_public_surfaces() -> None:
    token = "historical_site_event_resolution_composition"
    isolated_paths = (
        "law_data/spatial_condition_evaluator.py",
        "law_data/site_analysis_builder.py",
        "site_data/site_analysis_service.py",
        "site_data/site_analysis_orchestrator.py",
        "site_data/site_analysis_response.py",
    )
    for path in isolated_paths:
        source = Path(path).read_text(encoding="utf-8")
        assert token not in source, path


def main() -> None:
    test_missing_inputs_fail_closed_to_unknown()
    test_each_required_positive_axis_is_independently_required()
    test_profile_must_be_historical_site_event()
    test_requirement_assessments_must_align_to_same_profile()
    test_truthy_non_bool_positive_fields_do_not_promote()
    test_all_explicit_positive_gates_yield_true_candidate_only()
    test_composition_has_no_runtime_search_registry_or_output_mutation_surface()
    test_no_auto_wiring_into_runtime_or_public_surfaces()

    print("=" * 72)
    print("STEP 26 HISTORICAL SITE EVENT RESOLUTION COMPOSITION BOUNDARY")
    print("=" * 72)
    print("Missing / incomplete / mismatched inputs -> resolution: UNKNOWN")
    print("Truthy non-bool positive fields -> resolution promotion: NONE")
    print("Qualification alone -> final resolution: NONE")
    print("History completeness alone -> final resolution: NONE")
    print("Authority/source-policy missing -> final resolution: NONE")
    print("All explicit positive gates -> resolution: TRUE_CANDIDATE")
    print("FALSE / legal absence inference: NONE")
    print("SITE / Rule Engine / production/runtime mutation: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
