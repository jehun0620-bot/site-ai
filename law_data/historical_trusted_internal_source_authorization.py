"""STEP71 trusted internal historical source authorization; no production wiring."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_builder_injection_payload import (
    BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME,
    CHANNEL,
    PROVENANCE,
    HistoricalSiteEventBuilderInjectionPayload,
)


BOUNDARY_NAME = (
    "HISTORICAL_TRUSTED_INTERNAL_SOURCE_AUTHORIZATION"
)


@dataclass(frozen=True)
class HistoricalTrustedInternalSourceAuthorization:
    boundary: str
    payload_present: bool
    payload_boundary_matched: bool
    payload_ready: bool
    production_integration_authorized: bool
    channel_matched: bool
    provenance_matched: bool
    rules_present: bool
    repairs_aligned: bool
    provenance_preserved: bool
    missing_gates: tuple[str, ...]
    trusted_source_authorized: bool
    channel: str
    provenance: str
    authorized_rules: tuple[Mapping[str, Any], ...]
    authorized_repairs: tuple[Mapping[str, Any], ...]

    def to_dict(self):
        return {
            **self.__dict__,
            "missing_gates": list(
                self.missing_gates
            ),
            "authorized_rules": copy.deepcopy(
                list(self.authorized_rules)
            ),
            "authorized_repairs": copy.deepcopy(
                list(self.authorized_repairs)
            ),
            "orchestrator_wired": False,
            "service_wired": False,
            "builder_wired": False,
            "rule_engine_modified": False,
            "spatial_runtime_registered": False,
            "public_api_exposed": False,
            "production_wiring_applied": False,
        }


def authorize_historical_trusted_internal_source(
    payload: (
        HistoricalSiteEventBuilderInjectionPayload
        | None
    ),
) -> HistoricalTrustedInternalSourceAuthorization:
    payload_present = isinstance(
        payload,
        HistoricalSiteEventBuilderInjectionPayload,
    )

    payload_boundary_matched = bool(
        payload_present
        and payload.boundary
        == PAYLOAD_BOUNDARY_NAME
    )

    payload_ready = bool(
        payload_present
        and payload.builder_injection_payload_ready
        is True
    )

    production_integration_authorized = bool(
        payload_present
        and payload.production_integration_authorized
        is True
    )

    channel_matched = bool(
        payload_present
        and payload.channel == CHANNEL
    )

    provenance_matched = bool(
        payload_present
        and payload.provenance == PROVENANCE
    )

    rules = (
        copy.deepcopy(
            tuple(payload.historical_rules)
        )
        if payload_present
        else ()
    )

    repairs = (
        copy.deepcopy(
            tuple(payload.historical_repairs)
        )
        if payload_present
        else ()
    )

    rules_present = bool(
        payload_present
        and isinstance(
            payload.historical_rules,
            tuple,
        )
    )

    repairs_aligned = bool(
        payload_present
        and isinstance(
            payload.historical_repairs,
            tuple,
        )
        and payload.repairs_aligned is True
    )

    provenance_preserved = bool(
        payload_present
        and payload.provenance_preserved is True
    )

    if provenance_preserved:
        for repair in repairs:
            if (
                not isinstance(repair, Mapping)
                or repair.get("new_source")
                != PROVENANCE
            ):
                provenance_preserved = False
                break

    gates = (
        ("payload_present", payload_present),
        (
            "payload_boundary_matched",
            payload_boundary_matched,
        ),
        ("payload_ready", payload_ready),
        (
            "production_integration_authorized",
            production_integration_authorized,
        ),
        ("channel_matched", channel_matched),
        (
            "provenance_matched",
            provenance_matched,
        ),
        ("rules_present", rules_present),
        ("repairs_aligned", repairs_aligned),
        (
            "provenance_preserved",
            provenance_preserved,
        ),
    )

    missing_gates = tuple(
        name
        for name, passed in gates
        if not passed
    )

    trusted_source_authorized = (
        not missing_gates
    )

    return HistoricalTrustedInternalSourceAuthorization(
        boundary=BOUNDARY_NAME,
        payload_present=payload_present,
        payload_boundary_matched=(
            payload_boundary_matched
        ),
        payload_ready=payload_ready,
        production_integration_authorized=(
            production_integration_authorized
        ),
        channel_matched=channel_matched,
        provenance_matched=provenance_matched,
        rules_present=rules_present,
        repairs_aligned=repairs_aligned,
        provenance_preserved=(
            provenance_preserved
        ),
        missing_gates=missing_gates,
        trusted_source_authorized=(
            trusted_source_authorized
        ),
        channel=(
            CHANNEL
            if trusted_source_authorized
            else ""
        ),
        provenance=(
            PROVENANCE
            if trusted_source_authorized
            else ""
        ),
        authorized_rules=(
            rules
            if trusted_source_authorized
            else ()
        ),
        authorized_repairs=(
            repairs
            if trusted_source_authorized
            else ()
        ),
    )
