"""STEP72 trusted historical source handoff authorization; no wiring."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_builder_injection_payload import (
    CHANNEL,
    PROVENANCE,
)
from law_data.historical_trusted_internal_source_authorization import (
    BOUNDARY_NAME as SOURCE_AUTHORIZATION_BOUNDARY_NAME,
    HistoricalTrustedInternalSourceAuthorization,
)


BOUNDARY_NAME = (
    "HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
    "HANDOFF_AUTHORIZATION"
)


@dataclass(frozen=True)
class HistoricalTrustedInternalSourceHandoffAuthorization:
    boundary: str
    source_authorization_present: bool
    source_authorization_boundary_matched: bool
    trusted_source_authorized: bool
    channel_matched: bool
    provenance_matched: bool
    rules_present: bool
    repairs_present: bool
    repair_provenance_preserved: bool
    missing_gates: tuple[str, ...]
    handoff_authorized: bool
    channel: str
    provenance: str
    handoff_rules: tuple[Mapping[str, Any], ...]
    handoff_repairs: tuple[Mapping[str, Any], ...]

    def to_dict(self):
        return {
            **self.__dict__,
            "missing_gates": list(
                self.missing_gates
            ),
            "handoff_rules": copy.deepcopy(
                list(self.handoff_rules)
            ),
            "handoff_repairs": copy.deepcopy(
                list(self.handoff_repairs)
            ),
            "orchestrator_wired": False,
            "service_wired": False,
            "builder_wired": False,
            "rule_engine_modified": False,
            "public_api_exposed": False,
            "spatial_runtime_registered": False,
            "production_wiring_applied": False,
        }


def authorize_historical_trusted_internal_source_handoff(
    source_authorization: (
        HistoricalTrustedInternalSourceAuthorization
        | None
    ),
) -> HistoricalTrustedInternalSourceHandoffAuthorization:
    source_authorization_present = isinstance(
        source_authorization,
        HistoricalTrustedInternalSourceAuthorization,
    )

    source_authorization_boundary_matched = bool(
        source_authorization_present
        and source_authorization.boundary
        == SOURCE_AUTHORIZATION_BOUNDARY_NAME
    )

    trusted_source_authorized = bool(
        source_authorization_present
        and source_authorization.trusted_source_authorized
        is True
    )

    channel_matched = bool(
        source_authorization_present
        and source_authorization.channel == CHANNEL
    )

    provenance_matched = bool(
        source_authorization_present
        and source_authorization.provenance == PROVENANCE
    )

    rules = (
        copy.deepcopy(
            tuple(
                source_authorization.authorized_rules
            )
        )
        if source_authorization_present
        else ()
    )

    repairs = (
        copy.deepcopy(
            tuple(
                source_authorization.authorized_repairs
            )
        )
        if source_authorization_present
        else ()
    )

    rules_present = bool(
        source_authorization_present
        and isinstance(
            source_authorization.authorized_rules,
            tuple,
        )
    )

    repairs_present = bool(
        source_authorization_present
        and isinstance(
            source_authorization.authorized_repairs,
            tuple,
        )
    )

    repair_provenance_preserved = bool(
        source_authorization_present
    )

    if repair_provenance_preserved:
        for repair in repairs:
            if (
                not isinstance(repair, Mapping)
                or repair.get("new_source")
                != PROVENANCE
            ):
                repair_provenance_preserved = False
                break

    gates = (
        (
            "source_authorization_present",
            source_authorization_present,
        ),
        (
            "source_authorization_boundary_matched",
            source_authorization_boundary_matched,
        ),
        (
            "trusted_source_authorized",
            trusted_source_authorized,
        ),
        ("channel_matched", channel_matched),
        (
            "provenance_matched",
            provenance_matched,
        ),
        ("rules_present", rules_present),
        ("repairs_present", repairs_present),
        (
            "repair_provenance_preserved",
            repair_provenance_preserved,
        ),
    )

    missing_gates = tuple(
        name
        for name, passed in gates
        if not passed
    )

    handoff_authorized = not missing_gates

    return HistoricalTrustedInternalSourceHandoffAuthorization(
        boundary=BOUNDARY_NAME,
        source_authorization_present=(
            source_authorization_present
        ),
        source_authorization_boundary_matched=(
            source_authorization_boundary_matched
        ),
        trusted_source_authorized=(
            trusted_source_authorized
        ),
        channel_matched=channel_matched,
        provenance_matched=provenance_matched,
        rules_present=rules_present,
        repairs_present=repairs_present,
        repair_provenance_preserved=(
            repair_provenance_preserved
        ),
        missing_gates=missing_gates,
        handoff_authorized=handoff_authorized,
        channel=(
            CHANNEL
            if handoff_authorized
            else ""
        ),
        provenance=(
            PROVENANCE
            if handoff_authorized
            else ""
        ),
        handoff_rules=(
            rules
            if handoff_authorized
            else ()
        ),
        handoff_repairs=(
            repairs
            if handoff_authorized
            else ()
        ),
    )
