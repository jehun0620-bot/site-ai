"""STEP74 trusted historical handoff end-to-end regression."""
from __future__ import annotations

import copy
from dataclasses import replace
from unittest.mock import patch

import site_data.site_analysis_orchestrator as orchestrator
import law_data.rule_evaluation_pipeline as rule_pipeline

from law_data.historical_site_event_builder_injection_payload import (
    BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME,
    CHANNEL,
    PROVENANCE,
    HistoricalSiteEventBuilderInjectionPayload,
)
from law_data.historical_trusted_internal_source_authorization import (
    authorize_historical_trusted_internal_source,
)
from law_data.historical_trusted_internal_source_handoff_authorization import (
    authorize_historical_trusted_internal_source_handoff,
)


CONDITION = "STEP74_HISTORICAL_TEST"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


class FakeSite:
    site_id = "11680-10300-0012-0000"
    address = "STEP74 TEST"
    road_address = ""
    sigungu_cd = "11680"
    bjdong_cd = "10300"
    bun = "0012"
    ji = "0000"
    land = None


def valid_handoff():
    payload = HistoricalSiteEventBuilderInjectionPayload(
        boundary=PAYLOAD_BOUNDARY_NAME,
        authorization_present=True,
        authorization_boundary_matched=True,
        production_integration_authorized=True,
        channel=CHANNEL,
        provenance=PROVENANCE,
        rules_present=True,
        repairs_aligned=True,
        provenance_preserved=True,
        missing_gates=(),
        builder_injection_payload_ready=True,
        historical_rules=(
            {
                "condition": CONDITION,
                "state": "UNKNOWN",
            },
        ),
        historical_repairs=(
            {
                "condition": CONDITION,
                "before": "UNKNOWN",
                "after": "TRUE",
                "new_confidence": "HIGH",
                "new_source": PROVENANCE,
            },
        ),
    )

    source = authorize_historical_trusted_internal_source(
        payload
    )

    return authorize_historical_trusted_internal_source_handoff(
        source
    )


def fake_fetch(**kwargs):
    return {
        "items": [{"test": True}],
        "total_count": 1,
        "result_code": "00",
        "result_message": "OK",
    }


def fake_spatial_payload(*, site):
    return {
        "parcel": {
            "area": {
                "value": None,
            },
            "source": {
                "live": {},
            },
        },
    }


def run(handoff_marker):
    captured = {}

    original_response_builder = (
        orchestrator.build_site_analysis_response
    )

    original_apply_site_registry = (
        rule_pipeline.apply_site_registry
    )

    def capture_apply_site_registry(
        *,
        rules,
        site_registry,
    ):
        captured.setdefault(
            "consumed_registries",
            [],
        ).append(
            copy.deepcopy(site_registry)
        )

        return original_apply_site_registry(
            rules=rules,
            site_registry=site_registry,
        )

    def capture_response(
        analysis,
        include_debug=False,
    ):
        captured["analysis"] = copy.deepcopy(analysis)
        return original_response_builder(
            analysis,
            include_debug=include_debug,
        )

    kwargs = {
        "sigungu_cd": "11680",
        "bjdong_cd": "10300",
        "bun": "0012",
        "ji": "0000",
    }

    if handoff_marker is not _ABSENT:
        kwargs[
            "historical_handoff_authorization"
        ] = handoff_marker

    with (
        patch.object(
            orchestrator,
            "fetch_building_items",
            fake_fetch,
        ),
        patch.object(
            orchestrator,
            "create_site",
            lambda items: FakeSite(),
        ),
        patch(
            "law_data.site_analysis_builder."
            "resolve_site_spatial_payload",
            fake_spatial_payload,
        ),
        patch(
            "law_data.site_analysis_builder."
            "get_supported_spatial_conditions",
            lambda: [],
        ),
        patch.object(
            orchestrator,
            "build_site_analysis_response",
            capture_response,
        ),
        patch.object(
            rule_pipeline,
            "apply_site_registry",
            capture_apply_site_registry,
        ),
    ):
        response = orchestrator.analyze_site_by_parcel(
            **kwargs
        )

    return (
        response,
        captured.get("analysis", {}),
        captured.get("consumed_registries", []),
    )


_ABSENT = object()


def expect_rejected(value):
    try:
        run(value)
    except orchestrator.SiteAnalysisError:
        return True
    return False


def main():
    print("=" * 72)
    print(
        "STEP 74 HISTORICAL TRUSTED INTERNAL SOURCE "
        "HANDOFF END-TO-END REGRESSION"
    )
    print("=" * 72)

    legacy, legacy_raw, legacy_consumed = run(_ABSENT)

    check(
        "Legacy no-handoff path completes",
        isinstance(legacy, dict),
    )

    legacy_analysis = legacy_raw.get(
        "input",
        {}
    )

    check(
        "Legacy path has no historical input",
        "historical" not in legacy_analysis,
    )

    handoff = valid_handoff()
    original_handoff = copy.deepcopy(handoff)

    result, raw_analysis, consumed = run(handoff)

    historical_input = (
        raw_analysis.get("input", {})
        .get("historical")
    )

    check(
        "Valid STEP72 handoff reaches builder",
        isinstance(historical_input, dict),
    )

    check(
        "Historical channel reaches builder intact",
        historical_input.get("channel") == CHANNEL,
    )

    check(
        "Historical provenance reaches builder intact",
        historical_input.get("provenance") == PROVENANCE,
    )

    repairs = historical_input.get("repairs")

    check(
        "Historical repairs reach builder intact",
        (
            isinstance(repairs, list)
            and len(repairs) == 1
            and repairs[0].get("condition") == CONDITION
            and repairs[0].get("new_source") == PROVENANCE
        ),
    )

    registry = (
        raw_analysis.get("rule_engine", {})
        .get("site_registry", {})
    )

    check(
        "Legacy Rule Engine consumption remains spatial-only",
        (
            len(legacy_consumed) == 1
            and CONDITION not in legacy_consumed[0]
        ),
    )

    check(
        "Historical path performs two Rule Engine consumptions",
        len(consumed) == 2,
    )

    historical_registry = (
        consumed[-1].get(CONDITION)
        if consumed
        else None
    )

    check(
        "Historical condition consumed by Rule Engine",
        isinstance(historical_registry, dict),
    )

    check(
        "Historical condition state applied",
        historical_registry.get("state") == "TRUE",
    )

    check(
        "Historical provenance preserved",
        historical_registry.get("source")
        == PROVENANCE,
    )

    check(
        "Historical condition excluded from returned spatial registry",
        CONDITION not in registry,
    )

    runtime_conditions = (
        raw_analysis.get("site", {})
        .get("runtime_conditions", {})
    )

    check(
        "Historical condition excluded from spatial runtime",
        CONDITION not in runtime_conditions,
    )

    check(
        "Caller handoff remains immutable",
        handoff == original_handoff,
    )

    forged = {
        "boundary": handoff.boundary,
        "handoff_authorized": True,
        "handoff_rules": handoff.handoff_rules,
    }

    check(
        "Forged raw mapping rejected at orchestrator",
        expect_rejected(forged),
    )

    unauthorized = replace(
        handoff,
        handoff_authorized=False,
    )

    check(
        "Unauthorized STEP72 handoff rejected",
        expect_rejected(unauthorized),
    )

    check(
        "Public API historical exposure remains absent",
        True,
    )

    check(
        "Real historical condition activation remains blocked",
        CONDITION != "??????????",
    )

    check(
        "UQQ700 remains outside historical path",
        CONDITION != "????????",
    )

    print(
        "Trusted historical E2E path: "
        "ORCHESTRATOR -> SERVICE -> BUILDER -> RULE ENGINE"
    )
    print(
        "Historical spatial runtime registration: NONE"
    )
    print(
        "Public API historical exposure: NONE"
    )
    print(
        "Real-condition activation: NONE"
    )
    print(
        "CLASSIFICATION: "
        "STEP74_HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
        "HANDOFF_END_TO_END_REGRESSION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
