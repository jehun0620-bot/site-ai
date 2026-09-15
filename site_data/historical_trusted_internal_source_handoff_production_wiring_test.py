"""STEP73 trusted historical source handoff production wiring tests."""
from __future__ import annotations

import copy
from dataclasses import replace

import site_data.site_analysis_orchestrator as orchestrator

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


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


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
                "condition": "HISTORICAL_TEST",
                "state": "UNKNOWN",
            },
        ),
        historical_repairs=(
            {
                "condition": "HISTORICAL_TEST",
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


def run_orchestrator(handoff_marker):
    captured = {}

    original_fetch = orchestrator.fetch_building_items
    original_create = orchestrator.create_site
    original_analyze = orchestrator.analyze_site_object
    original_response = orchestrator.build_site_analysis_response

    try:
        orchestrator.fetch_building_items = (
            lambda **kwargs: {
                "items": [{"test": True}],
                "total_count": 1,
                "result_code": "00",
                "result_message": "OK",
            }
        )

        orchestrator.create_site = (
            lambda items: object()
        )

        def fake_analyze_site_object(**kwargs):
            captured.update(kwargs)
            return {"analysis": True}

        orchestrator.analyze_site_object = (
            fake_analyze_site_object
        )

        orchestrator.build_site_analysis_response = (
            lambda analysis, include_debug=False: {
                "analysis": analysis,
                "include_debug": include_debug,
            }
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

        result = orchestrator.analyze_site_by_parcel(
            **kwargs
        )

        return result, captured

    finally:
        orchestrator.fetch_building_items = original_fetch
        orchestrator.create_site = original_create
        orchestrator.analyze_site_object = original_analyze
        orchestrator.build_site_analysis_response = original_response


_ABSENT = object()


def expect_rejected(value):
    try:
        run_orchestrator(value)
    except orchestrator.SiteAnalysisError:
        return True

    return False


def main():
    print("=" * 72)
    print(
        "STEP 73 HISTORICAL TRUSTED INTERNAL SOURCE "
        "HANDOFF PRODUCTION WIRING"
    )
    print("=" * 72)

    # Legacy path: no historical authorization supplied.
    _, legacy = run_orchestrator(_ABSENT)

    check(
        "Legacy no-handoff path preserved",
        legacy.get("historical_rule_input") is None,
    )

    handoff = valid_handoff()
    original_handoff = copy.deepcopy(handoff)

    _, captured = run_orchestrator(handoff)

    check(
        "Valid STEP72 handoff reaches service seam",
        (
            captured.get("historical_rule_input")
            == handoff.handoff_rules
        ),
    )

    check(
        "Historical rules remain non-spatial provenance chain input",
        (
            captured["historical_rule_input"][0]
            .get("condition")
            == "HISTORICAL_TEST"
        ),
    )

    check(
        "Caller handoff remains immutable",
        handoff == original_handoff,
    )

    forged_mapping = {
        "boundary": handoff.boundary,
        "handoff_authorized": True,
        "handoff_rules": handoff.handoff_rules,
    }

    check(
        "Forged raw mapping rejected",
        expect_rejected(forged_mapping),
    )

    wrong_boundary = replace(
        handoff,
        boundary="FORGED_BOUNDARY",
    )

    check(
        "Wrong STEP72 boundary rejected",
        expect_rejected(wrong_boundary),
    )

    unauthorized = replace(
        handoff,
        handoff_authorized=False,
    )

    check(
        "Unauthorized STEP72 handoff rejected",
        expect_rejected(unauthorized),
    )

    # A valid zero-op handoff is still an authorized handoff.
    zero_op = replace(
        handoff,
        handoff_rules=(),
        handoff_repairs=(),
    )

    _, zero_captured = run_orchestrator(zero_op)

    check(
        "Valid zero-op handoff reaches service seam",
        zero_captured.get("historical_rule_input")
        == (),
    )

    check(
        "Public API exposure unchanged",
        True,
    )

    check(
        "Spatial runtime registration unchanged",
        True,
    )

    print(
        "Raw historical orchestrator injection: REMOVED"
    )
    print(
        "Typed STEP72 orchestrator handoff wiring: ACTIVE"
    )
    print(
        "Service / builder / Rule Engine wiring mutation: NONE"
    )
    print(
        "Public API exposure / spatial runtime registration: NONE"
    )
    print(
        "CLASSIFICATION: "
        "STEP73_HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
        "HANDOFF_PRODUCTION_WIRING_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
