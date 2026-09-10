from __future__ import annotations

import copy
from dataclasses import dataclass
from unittest.mock import patch

import site_data.site_analysis_service as service


CLASSIFICATION = "STEP18_PRODUCTION_CONDITION_SHADOW_SERVICE_PASSTHROUGH_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


@dataclass
class SyntheticLand:
    zoning: str = "제2종일반주거지역"
    land_area: float = 1000.0
    land_category: str = "대"
    district: str = ""
    land_use_regulation: str = ""


@dataclass
class SyntheticSite:
    site_id: str = "11680-10300-0012-0000"
    address: str = "서울특별시 강남구 개포동 12"
    road_address: str = "서울특별시 강남구 개포로109길 21"
    sigungu_cd: str = "11680"
    bjdong_cd: str = "10300"
    bun: str = "0012"
    ji: str = "0000"
    land: SyntheticLand | None = None


def main() -> None:
    site = SyntheticSite(land=SyntheticLand())
    project_profile = {"use": "synthetic"}
    procedure_profile = {"permit": "synthetic"}
    historical_shadow = {
        "도시지역편입해제구역": {
            "name": "도시지역편입해제구역",
            "condition_type": "SITE_HISTORY",
            "resolution_type": "HISTORICAL_SITE_EVENT",
            "state": "UNKNOWN",
            "confidence": "MEDIUM",
            "source": "SYNTHETIC_PRENORMALIZED_SHADOW",
            "provenance": {
                "resolver_resolution": "UNKNOWN",
            },
            "production_eligible": False,
            "runtime_registered": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_promotion_allowed": False,
            "diagnostics": {
                "synthetic": True,
            },
        }
    }

    project_before = copy.deepcopy(project_profile)
    procedure_before = copy.deepcopy(procedure_profile)
    shadow_before = copy.deepcopy(historical_shadow)
    captured = {}

    def fake_build_site_analysis(**kwargs):
        captured.update(copy.deepcopy(kwargs))
        return {
            "site": {
                "production_condition_contracts": copy.deepcopy(
                    kwargs.get("production_condition_shadow_sources") or {}
                )
            },
            "synthetic": True,
        }

    with patch.object(
        service,
        "build_site_analysis",
        side_effect=fake_build_site_analysis,
    ):
        result = service.analyze_site_object(
            site,
            project_profile=project_profile,
            procedure_profile=procedure_profile,
            production_condition_shadow_sources=historical_shadow,
        )

    assert_equal(
        captured["production_condition_shadow_sources"],
        historical_shadow,
        "pre-normalized production shadow passthrough",
    )
    assert_equal(
        captured["project_profile"],
        project_profile,
        "project profile passthrough",
    )
    assert_equal(
        captured["procedure_profile"],
        procedure_profile,
        "procedure profile passthrough",
    )
    assert_equal(
        captured["site_input"]["pnu"],
        "1168010300100120000",
        "SITE input conversion preserved",
    )
    assert_equal(
        captured["site_input"]["land_area"],
        1000.0,
        "land area conversion preserved",
    )
    assert_equal(
        result["site"]["production_condition_contracts"],
        historical_shadow,
        "service result follows builder result",
    )

    assert_equal(project_profile, project_before, "project input mutation")
    assert_equal(procedure_profile, procedure_before, "procedure input mutation")
    assert_equal(historical_shadow, shadow_before, "shadow source mutation")

    # Backward compatibility: callers that do not provide a shadow source still
    # invoke the builder successfully and pass an explicit None only.
    captured.clear()
    with patch.object(
        service,
        "build_site_analysis",
        side_effect=fake_build_site_analysis,
    ):
        legacy_result = service.analyze_site_object(site)

    assert_true(legacy_result["synthetic"], "legacy call remains supported")
    assert_equal(
        captured["production_condition_shadow_sources"],
        None,
        "legacy call shadow source remains absent",
    )
    assert_equal(captured["project_profile"], {}, "legacy project default")
    assert_equal(captured["procedure_profile"], {}, "legacy procedure default")

    # The service must not interpret raw historical evidence. It passes any
    # supplied object through unchanged; contract validation remains a builder /
    # collector boundary responsibility.
    raw_uninterpreted = {
        "resolution": "TRUE_CANDIDATE",
        "verified_qualifying_event_present": True,
    }
    raw_before = copy.deepcopy(raw_uninterpreted)
    captured.clear()
    with patch.object(
        service,
        "build_site_analysis",
        side_effect=fake_build_site_analysis,
    ):
        service.analyze_site_object(
            site,
            production_condition_shadow_sources=raw_uninterpreted,
        )

    assert_equal(
        captured["production_condition_shadow_sources"],
        raw_uninterpreted,
        "raw object passed without interpretation",
    )
    assert_equal(raw_uninterpreted, raw_before, "raw object mutation")

    print("=" * 72)
    print("STEP 18 PRODUCTION CONDITION SHADOW SERVICE PASSTHROUGH REGRESSION")
    print("=" * 72)
    print("Existing service call compatibility: PASS")
    print("Pre-normalized shadow passthrough: PASS")
    print("SITE/project/procedure input preservation: PASS")
    print("Shadow source mutation: NONE")
    print("Raw historical evidence interpretation: NONE")
    print("Resolver/runtime/registration behavior added: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
