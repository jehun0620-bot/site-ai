"""STEP68 historical orchestrator exposure authorization boundary audit.

Reconciled with the provenance-bound SITE applicability gate: raw historical
rule input is no longer an orchestrator seam. Typed handoff plus typed SITE
applicability admission remain internal-only inputs.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch

from api_app import SiteAnalysisRequest
from site_data.site_analysis_orchestrator import analyze_site_by_parcel

RAW_FIELD = "historical_rule_input"
HANDOFF_FIELD = "historical_handoff_authorization"
APPLICABILITY_FIELD = "historical_site_applicability_admission"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def api_fields():
    fields = getattr(SiteAnalysisRequest, "model_fields", None)
    if fields is None:
        fields = getattr(SiteAnalysisRequest, "__fields__", {})
    return fields


def main():
    print("=" * 72)
    print("STEP 68 HISTORICAL ORCHESTRATOR EXPOSURE AUTHORIZATION")
    print("=" * 72)

    parameters = inspect.signature(analyze_site_by_parcel).parameters
    fields = api_fields()

    check("Raw historical orchestrator seam removed", RAW_FIELD not in parameters)
    check("Typed handoff orchestrator seam exposed", HANDOFF_FIELD in parameters)
    check(
        "Typed SITE applicability orchestrator seam exposed",
        APPLICABILITY_FIELD in parameters,
    )
    check("API raw historical field absent", RAW_FIELD not in fields)
    check("API typed handoff field absent", HANDOFF_FIELD not in fields)
    check("API SITE applicability field absent", APPLICABILITY_FIELD not in fields)

    site = SimpleNamespace(
        site_id="STEP68-TEST-SITE",
        address="STEP68 TEST",
        road_address="",
        sigungu_cd="11680",
        bjdong_cd="10300",
        bun="0012",
        ji="0000",
        land=None,
    )

    captured = {}
    with (
        patch(
            "site_data.site_analysis_orchestrator.fetch_building_items",
            return_value={"items": [{"test": True}], "total_count": 1, "result_code": "00"},
        ),
        patch("site_data.site_analysis_orchestrator.create_site", return_value=site),
        patch(
            "site_data.site_analysis_orchestrator.analyze_site_object",
            side_effect=lambda **kwargs: captured.update(kwargs) or {"analysis": True},
        ),
        patch(
            "site_data.site_analysis_orchestrator.build_site_analysis_response",
            side_effect=lambda analysis, include_debug=False: dict(analysis),
        ),
    ):
        result = analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            include_debug=True,
        )

    check("Legacy orchestrator path preserved", result.get("analysis") is True)
    check("Legacy path has no historical input", captured.get("historical_rule_input") is None)

    raw_rejected = False
    try:
        analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            historical_rule_input={},
        )
    except TypeError:
        raw_rejected = True
    check("Raw historical caller injection unavailable", raw_rejected)

    print("Public API historical input exposure / direct spatial runtime registration: NONE")
    print(
        "CLASSIFICATION: "
        "STEP68_HISTORICAL_ORCHESTRATOR_API_EXPOSURE_"
        "AUTHORIZATION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
