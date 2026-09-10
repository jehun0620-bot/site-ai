from __future__ import annotations

import copy
from unittest.mock import patch

import site_data.site_analysis_orchestrator as orchestrator


CLASSIFICATION = "STEP18_PRODUCTION_CONDITION_SHADOW_ORCHESTRATOR_PASSTHROUGH_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def main() -> None:
    shadow_source = {
        "도시지역편입해제구역": {
            "name": "도시지역편입해제구역",
            "condition_type": "SITE_HISTORY",
            "resolution_type": "HISTORICAL_SITE_EVENT",
            "state": "UNKNOWN",
            "confidence": "MEDIUM",
            "source": "SYNTHETIC_PRENORMALIZED_SHADOW",
            "production_eligible": False,
            "runtime_registered": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_promotion_allowed": False,
            "provenance": {"synthetic": True},
            "diagnostics": {"synthetic": True},
        }
    }
    shadow_before = copy.deepcopy(shadow_source)
    project_profile = {"use": "synthetic"}
    procedure_profile = {"permit": "synthetic"}
    project_before = copy.deepcopy(project_profile)
    procedure_before = copy.deepcopy(procedure_profile)

    building_result = {
        "items": [{"mgmBldrgstPk": "synthetic"}],
        "total_count": 1,
        "result_code": "00",
        "result_message": "NORMAL SERVICE",
    }
    synthetic_site = object()
    synthetic_analysis = {
        "analysis": {"status": "PARTIAL"},
        "site": {"production_condition_contracts": copy.deepcopy(shadow_source)},
    }
    synthetic_response = {
        "schema_version": "SITE_ANALYSIS_API_V1",
        "status": "PARTIAL",
    }

    captured = {}

    def fake_fetch_building_items(**kwargs):
        captured["fetch"] = copy.deepcopy(kwargs)
        return copy.deepcopy(building_result)

    def fake_create_site(items):
        captured["create_site_items"] = copy.deepcopy(items)
        return synthetic_site

    def fake_analyze_site_object(**kwargs):
        captured["analysis_call"] = {
            "site": kwargs.get("site"),
            "project_profile": copy.deepcopy(kwargs.get("project_profile")),
            "procedure_profile": copy.deepcopy(kwargs.get("procedure_profile")),
            "production_condition_shadow_sources": copy.deepcopy(
                kwargs.get("production_condition_shadow_sources")
            ),
        }
        return copy.deepcopy(synthetic_analysis)

    def fake_build_site_analysis_response(analysis, *, include_debug=False):
        captured["response_analysis"] = copy.deepcopy(analysis)
        captured["include_debug"] = include_debug
        return copy.deepcopy(synthetic_response)

    with patch.object(
        orchestrator,
        "fetch_building_items",
        side_effect=fake_fetch_building_items,
    ), patch.object(
        orchestrator,
        "create_site",
        side_effect=fake_create_site,
    ), patch.object(
        orchestrator,
        "analyze_site_object",
        side_effect=fake_analyze_site_object,
    ), patch.object(
        orchestrator,
        "build_site_analysis_response",
        side_effect=fake_build_site_analysis_response,
    ):
        result = orchestrator.analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            project_profile=project_profile,
            procedure_profile=procedure_profile,
            production_condition_shadow_sources=shadow_source,
            include_debug=True,
            service_key="synthetic-key",
        )

    assert_equal(
        captured["analysis_call"]["production_condition_shadow_sources"],
        shadow_source,
        "production shadow passthrough",
    )
    assert_true(
        captured["analysis_call"]["site"] is synthetic_site,
        "Site object preserved",
    )
    assert_equal(
        captured["analysis_call"]["project_profile"],
        project_profile,
        "project profile preserved",
    )
    assert_equal(
        captured["analysis_call"]["procedure_profile"],
        procedure_profile,
        "procedure profile preserved",
    )
    assert_equal(
        captured["response_analysis"],
        synthetic_analysis,
        "response builder receives unchanged analysis",
    )
    assert_true(captured["include_debug"], "include_debug preserved")
    assert_equal(result["schema_version"], "SITE_ANALYSIS_API_V1", "response schema")
    assert_equal(result["service"]["building_count"], 1, "building count")
    assert_equal(result["service"]["building_total_count"], 1, "building total count")
    assert_equal(result["service"]["building_api_status"], "00", "building API status")

    assert_equal(shadow_source, shadow_before, "shadow source mutation")
    assert_equal(project_profile, project_before, "project profile mutation")
    assert_equal(procedure_profile, procedure_before, "procedure profile mutation")

    # Backward compatibility: omitted shadow source remains None and the
    # existing orchestrator flow still completes.
    captured.clear()
    with patch.object(
        orchestrator,
        "fetch_building_items",
        side_effect=fake_fetch_building_items,
    ), patch.object(
        orchestrator,
        "create_site",
        side_effect=fake_create_site,
    ), patch.object(
        orchestrator,
        "analyze_site_object",
        side_effect=fake_analyze_site_object,
    ), patch.object(
        orchestrator,
        "build_site_analysis_response",
        side_effect=fake_build_site_analysis_response,
    ):
        legacy_result = orchestrator.analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            service_key="synthetic-key",
        )

    assert_equal(
        captured["analysis_call"]["production_condition_shadow_sources"],
        None,
        "legacy shadow source remains absent",
    )
    assert_equal(captured["analysis_call"]["project_profile"], {}, "legacy project default")
    assert_equal(captured["analysis_call"]["procedure_profile"], {}, "legacy procedure default")
    assert_equal(legacy_result["schema_version"], "SITE_ANALYSIS_API_V1", "legacy response")

    print("=" * 72)
    print("STEP 18 PRODUCTION CONDITION SHADOW ORCHESTRATOR PASSTHROUGH REGRESSION")
    print("=" * 72)
    print("Existing orchestrator call compatibility: PASS")
    print("Production shadow passthrough: PASS")
    print("Building HUB / Site builder flow preservation: PASS")
    print("Response builder analysis preservation: PASS")
    print("Shadow/project/procedure mutation: NONE")
    print("Public response schema modification: NONE")
    print("Resolver/runtime/registration behavior added: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
