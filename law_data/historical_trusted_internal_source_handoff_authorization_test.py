"""STEP72 trusted historical source handoff authorization tests."""
from __future__ import annotations

from dataclasses import replace

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
    BOUNDARY_NAME,
    authorize_historical_trusted_internal_source_handoff,
)


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not passed:
        raise AssertionError(name)


def valid_payload():
    return HistoricalSiteEventBuilderInjectionPayload(
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


def valid_source_authorization():
    return authorize_historical_trusted_internal_source(
        valid_payload()
    )


def main():
    print("=" * 72)
    print(
        "STEP 72 HISTORICAL TRUSTED INTERNAL "
        "SOURCE HANDOFF AUTHORIZATION"
    )
    print("=" * 72)

    source_authorization = (
        valid_source_authorization()
    )

    handoff = (
        authorize_historical_trusted_internal_source_handoff(
            source_authorization
        )
    )

    check(
        "Handoff boundary exact",
        handoff.boundary == BOUNDARY_NAME,
    )

    check(
        "Valid STEP71 authorization accepted",
        handoff.handoff_authorized is True,
    )

    check(
        "Valid handoff gates complete",
        handoff.missing_gates == (),
    )

    check(
        "Historical channel preserved",
        handoff.channel == CHANNEL,
    )

    check(
        "Historical provenance preserved",
        handoff.provenance == PROVENANCE,
    )

    check(
        "Handoff rules preserved",
        len(handoff.handoff_rules) == 1,
    )

    check(
        "Handoff repairs preserved",
        (
            len(handoff.handoff_repairs) == 1
            and handoff.handoff_repairs[
                0
            ].get("new_source")
            == PROVENANCE
        ),
    )

    # --------------------------------------------------------
    # Raw/forged values must never become a trusted handoff.
    # --------------------------------------------------------

    forged_mapping = {
        "trusted_source_authorized": True,
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "authorized_rules": (),
        "authorized_repairs": (),
    }

    forged_handoff = (
        authorize_historical_trusted_internal_source_handoff(
            forged_mapping
        )
    )

    check(
        "Forged raw mapping rejected",
        (
            forged_handoff.handoff_authorized
            is False
            and "source_authorization_present"
            in forged_handoff.missing_gates
        ),
    )

    # --------------------------------------------------------
    # Exact STEP71 boundary / authorization / channel /
    # provenance gates.
    # --------------------------------------------------------

    wrong_boundary = replace(
        source_authorization,
        boundary="FORGED_BOUNDARY",
    )

    check(
        "Wrong STEP71 boundary rejected",
        not authorize_historical_trusted_internal_source_handoff(
            wrong_boundary
        ).handoff_authorized,
    )

    unauthorized_source = replace(
        source_authorization,
        trusted_source_authorized=False,
    )

    check(
        "Unauthorized STEP71 source rejected",
        not authorize_historical_trusted_internal_source_handoff(
            unauthorized_source
        ).handoff_authorized,
    )

    wrong_channel = replace(
        source_authorization,
        channel="SPATIAL",
    )

    check(
        "Wrong channel rejected",
        not authorize_historical_trusted_internal_source_handoff(
            wrong_channel
        ).handoff_authorized,
    )

    wrong_provenance = replace(
        source_authorization,
        provenance="FORGED_PROVENANCE",
    )

    check(
        "Wrong provenance rejected",
        not authorize_historical_trusted_internal_source_handoff(
            wrong_provenance
        ).handoff_authorized,
    )

    forged_repair = replace(
        source_authorization,
        authorized_repairs=(
            {
                "condition": "HISTORICAL_TEST",
                "before": "UNKNOWN",
                "after": "TRUE",
                "new_confidence": "HIGH",
                "new_source": "FORGED_SOURCE",
            },
        ),
    )

    check(
        "Repair provenance forgery rejected",
        not authorize_historical_trusted_internal_source_handoff(
            forged_repair
        ).handoff_authorized,
    )

    # --------------------------------------------------------
    # Valid zero-op STEP71 authorization remains acceptable.
    # --------------------------------------------------------

    zero_op_payload = replace(
        valid_payload(),
        historical_repairs=(),
    )

    zero_op_source = (
        authorize_historical_trusted_internal_source(
            zero_op_payload
        )
    )

    zero_op_handoff = (
        authorize_historical_trusted_internal_source_handoff(
            zero_op_source
        )
    )

    check(
        "Valid zero-op handoff authorized",
        zero_op_handoff.handoff_authorized
        is True,
    )

    # --------------------------------------------------------
    # Output isolation and explicit non-wiring.
    # --------------------------------------------------------

    output = handoff.to_dict()

    output["handoff_rules"][0][
        "state"
    ] = "MUTATED"

    check(
        "Handoff output deep-copy isolated",
        (
            handoff.handoff_rules[
                0
            ].get("state")
            == "UNKNOWN"
            and source_authorization
            .authorized_rules[
                0
            ].get("state")
            == "UNKNOWN"
        ),
    )

    check(
        "Production wiring flags remain false",
        (
            output["orchestrator_wired"]
            is False
            and output["service_wired"]
            is False
            and output["builder_wired"]
            is False
            and output["rule_engine_modified"]
            is False
            and output["public_api_exposed"]
            is False
            and output[
                "spatial_runtime_registered"
            ] is False
            and output[
                "production_wiring_applied"
            ] is False
        ),
    )

    print(
        "Raw internal historical injection: "
        "NOT AUTHORIZED"
    )

    print(
        "Production orchestrator handoff wiring: NONE"
    )

    print(
        "Public API exposure / spatial runtime "
        "registration: NONE"
    )

    print(
        "CLASSIFICATION: "
        "STEP72_HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
        "HANDOFF_AUTHORIZATION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
