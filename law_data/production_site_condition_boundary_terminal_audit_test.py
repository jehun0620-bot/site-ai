from __future__ import annotations

from pathlib import Path

from law_data.production_historical_site_event_adapter import (
    adapt_historical_site_event_to_production_contract,
)
from law_data.production_site_condition import UNKNOWN
from law_data.urban_area_conversion_production_condition_shadow_adapter import (
    adapt_urban_area_conversion_production_condition_shadow,
)


CLASSIFICATION = "STEP18_PRODUCTION_SITE_CONDITION_BOUNDARY_TERMINALLY_RECONCILED"
ROOT = Path(__file__).resolve().parent.parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def main() -> None:
    builder = read_text("law_data/site_analysis_builder.py")
    service = read_text("site_data/site_analysis_service.py")
    orchestrator = read_text("site_data/site_analysis_orchestrator.py")
    response = read_text("site_data/site_analysis_response.py")

    require(
        "production_condition_shadow_sources" in builder,
        "builder production shadow input seam missing",
    )
    require(
        "collect_production_site_condition_shadows" in builder,
        "builder common collector missing",
    )
    require(
        "site_condition_context=site_condition_context" in builder,
        "Rule Engine must retain legacy spatial context",
    )
    require(
        "production_condition_shadow_sources" in service,
        "service passthrough seam missing",
    )
    require(
        "production_condition_shadow_sources" in orchestrator,
        "orchestrator passthrough seam missing",
    )
    require(
        "production_condition_contracts" not in response,
        "production shadow must not be exposed by SITE_ANALYSIS_API_V1",
    )

    true_candidate = adapt_historical_site_event_to_production_contract(
        name="synthetic historical condition",
        resolver_result={"resolution": "TRUE_CANDIDATE"},
        confidence="MEDIUM",
        source="TERMINAL_AUDIT",
    ).to_dict()
    require(
        true_candidate["state"] == UNKNOWN,
        "TRUE_CANDIDATE must not promote to production TRUE",
    )
    require(
        true_candidate["production_eligible"] is False,
        "historical shadow must not become production eligible",
    )
    require(
        true_candidate["runtime_registered"] is False,
        "historical shadow must not become runtime registered",
    )
    require(
        true_candidate["negative_evidence_allowed"] is False,
        "negative evidence inference must remain disabled",
    )
    require(
        true_candidate["legal_absence_inference_allowed"] is False,
        "legal absence inference must remain disabled",
    )
    require(
        true_candidate["site_promotion_allowed"] is False,
        "SITE promotion must remain disabled",
    )

    urban = adapt_urban_area_conversion_production_condition_shadow({})
    urban_condition = urban["production_condition"]
    require(
        urban_condition["state"] == UNKNOWN,
        "urban-area-conversion historical condition must remain UNKNOWN",
    )
    require(
        urban_condition["production_eligible"] is False,
        "urban-area-conversion production wiring must remain blocked",
    )
    require(
        urban_condition["runtime_registered"] is False,
        "urban-area-conversion runtime registration must remain blocked",
    )
    require(
        urban["production_wiring_applied"] is False,
        "condition-specific production wiring must remain unapplied",
    )
    require(
        urban["runtime_registry_mutated"] is False,
        "condition-specific runtime registry must remain unmutated",
    )

    # UQQ700 safety is intentionally not re-resolved here. The terminal audit
    # only proves STEP18 did not introduce a public/runtime promotion path.
    uqq700_status = read_text("PROJECT_STATUS.md")
    require("UQQ700=UNKNOWN" in uqq700_status, "UQQ700 UNKNOWN lock missing")
    require(
        "negative_evidence_allowed=False" in uqq700_status,
        "UQQ700 negative-evidence lock missing",
    )
    require(
        "legal_absence_inference_allowed=False" in uqq700_status,
        "UQQ700 legal-absence lock missing",
    )

    print("=" * 72)
    print("STEP 18 PRODUCTION SITE CONDITION BOUNDARY TERMINAL AUDIT")
    print("=" * 72)
    print("Builder/service/orchestrator internal shadow path: PASS")
    print("Rule Engine spatial-context isolation: PASS")
    print("Public SITE_ANALYSIS_API_V1 shadow exposure: NONE")
    print("Historical TRUE_CANDIDATE promotion: NONE")
    print("Historical UNKNOWN preservation: PASS")
    print("Production eligibility/runtime registration promotion: NONE")
    print("Negative/legal absence/SITE promotion: DISABLED")
    print("Urban-area-conversion production wiring/runtime mutation: NONE")
    print("UQQ700 safety locks: PRESERVED")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
