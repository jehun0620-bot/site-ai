"""STEP71 trusted internal historical source authorization tests."""
from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_builder_injection_payload import (
    BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME,
    CHANNEL,
    PROVENANCE,
    HistoricalSiteEventBuilderInjectionPayload,
)
from law_data.historical_trusted_internal_source_authorization import (
    BOUNDARY_NAME,
    authorize_historical_trusted_internal_source,
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


def main():
    print("=" * 72)
    print(
        "STEP 71 HISTORICAL TRUSTED INTERNAL "
        "SOURCE AUTHORIZATION"
    )
    print("=" * 72)

    payload = valid_payload()

    authorization = (
        authorize_historical_trusted_internal_source(
            payload
        )
    )

    check(
        "Authorization boundary exact",
        authorization.boundary == BOUNDARY_NAME,
    )

    check(
        "Valid typed payload authorized",
        authorization.trusted_source_authorized
        is True,
    )

    check(
        "Valid payload gates complete",
        authorization.missing_gates == (),
    )

    check(
        "Historical channel preserved",
        authorization.channel == CHANNEL,
    )

    check(
        "Historical provenance preserved",
        authorization.provenance == PROVENANCE,
    )

    check(
        "Authorized rules preserved",
        len(authorization.authorized_rules) == 1,
    )

    check(
        "Authorized repairs preserved",
        (
            len(authorization.authorized_repairs)
            == 1
            and authorization.authorized_repairs[
                0
            ].get("new_source")
            == PROVENANCE
        ),
    )

    # --------------------------------------------------------
    # Forged raw mapping must not establish trust.
    # --------------------------------------------------------

    forged = {
        "boundary": PAYLOAD_BOUNDARY_NAME,
        "builder_injection_payload_ready": True,
        "production_integration_authorized": True,
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "historical_rules": [],
        "historical_repairs": [],
    }

    forged_authorization = (
        authorize_historical_trusted_internal_source(
            forged
        )
    )

    check(
        "Forged raw mapping rejected",
        (
            forged_authorization
            .trusted_source_authorized
            is False
            and "payload_present"
            in forged_authorization.missing_gates
        ),
    )

    # --------------------------------------------------------
    # Exact boundary / channel / provenance / readiness gates.
    # --------------------------------------------------------

    wrong_boundary = replace(
        payload,
        boundary="FORGED_BOUNDARY",
    )

    check(
        "Wrong payload boundary rejected",
        not authorize_historical_trusted_internal_source(
            wrong_boundary
        ).trusted_source_authorized,
    )

    wrong_channel = replace(
        payload,
        channel="SPATIAL",
    )

    check(
        "Wrong channel rejected",
        not authorize_historical_trusted_internal_source(
            wrong_channel
        ).trusted_source_authorized,
    )

    wrong_provenance = replace(
        payload,
        provenance="FORGED_PROVENANCE",
    )

    check(
        "Wrong provenance rejected",
        not authorize_historical_trusted_internal_source(
            wrong_provenance
        ).trusted_source_authorized,
    )

    not_ready = replace(
        payload,
        builder_injection_payload_ready=False,
    )

    check(
        "Not-ready payload rejected",
        not authorize_historical_trusted_internal_source(
            not_ready
        ).trusted_source_authorized,
    )

    integration_unauthorized = replace(
        payload,
        production_integration_authorized=False,
    )

    check(
        "Production integration unauthorized rejected",
        not authorize_historical_trusted_internal_source(
            integration_unauthorized
        ).trusted_source_authorized,
    )

    forged_repair = replace(
        payload,
        historical_repairs=(
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
        not authorize_historical_trusted_internal_source(
            forged_repair
        ).trusted_source_authorized,
    )

    # --------------------------------------------------------
    # Zero-op payload remains valid when upstream STEP57
    # contract marks it ready and repairs aligned.
    # --------------------------------------------------------

    zero_op = replace(
        payload,
        historical_repairs=(),
    )

    zero_op_authorization = (
        authorize_historical_trusted_internal_source(
            zero_op
        )
    )

    check(
        "Valid zero-op payload authorized",
        zero_op_authorization
        .trusted_source_authorized
        is True,
    )

    # --------------------------------------------------------
    # Output isolation / no production wiring.
    # --------------------------------------------------------

    output = authorization.to_dict()

    output["authorized_rules"][0][
        "state"
    ] = "MUTATED"

    check(
        "Authorization output deep-copy isolated",
        (
            authorization.authorized_rules[
                0
            ].get("state")
            == "UNKNOWN"
            and payload.historical_rules[
                0
            ].get("state")
            == "UNKNOWN"
        ),
    )

    check(
        "Production wiring flags remain false",
        (
            output["orchestrator_wired"] is False
            and output["service_wired"] is False
            and output["builder_wired"] is False
            and output["rule_engine_modified"]
            is False
            and output[
                "spatial_runtime_registered"
            ] is False
            and output["public_api_exposed"]
            is False
            and output[
                "production_wiring_applied"
            ] is False
        ),
    )

    print(
        "Production historical source wiring: NONE"
    )

    print(
        "Public API exposure / spatial runtime "
        "registration: NONE"
    )

    print(
        "CLASSIFICATION: "
        "STEP71_HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
        "AUTHORIZATION_CONTRACT_RECONCILED"
    )


if __name__ == "__main__":
    main()
