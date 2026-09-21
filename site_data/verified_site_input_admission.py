# -*- coding: utf-8 -*-
"""Verified historical / district SITE input admission boundary."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Optional

from law_data.district_unit_plan_verified_registry_candidate_envelope import (
    DistrictUnitPlanVerifiedRegistryCandidateEnvelope,
)
from law_data.historical_site_event_admitted_rule_input_adapter import (
    adapt_admitted_historical_site_event_rule_input,
)
from law_data.historical_site_event_candidate_condition_binding_authorization import (
    authorize_historical_site_event_candidate_condition_binding,
)
from law_data.historical_site_event_candidate_repair_consistency_authorization import (
    authorize_historical_site_event_candidate_repair_consistency,
)
from law_data.historical_site_event_site_applicability_admission import (
    HistoricalSiteEventSiteApplicabilityAdmissionResult,
)
from law_data.historical_site_event_site_truth_promotion_rule_input_bridge import (
    HistoricalSiteEventSiteTruthPromotionRuleInputBridge,
)
from law_data.historical_trusted_internal_source_handoff_authorization import (
    HistoricalTrustedInternalSourceHandoffAuthorization,
)
from law_data.historical_verified_rule_input_envelope import (
    seal_verified_historical_rule_input,
)
from site_data.site_analysis_service import site_to_analysis_input


class VerifiedSiteInputAdmissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedSiteInputs:
    historical_rule_input: Optional[Any]
    district_unit_plan_registry_candidate: Optional[Any]


def _actual_site_pnu(site: Any) -> str:
    try:
        pnu = str(site_to_analysis_input(site).get("pnu") or "").strip()
    except (TypeError, ValueError, AttributeError):
        return ""
    return pnu if len(pnu) == 19 and pnu.isdigit() else ""


def _admitted_canonical_pnu(applicability: Any) -> str:
    if (
        not isinstance(
            applicability,
            HistoricalSiteEventSiteApplicabilityAdmissionResult,
        )
        or not applicability.admitted
        or applicability.site_admission is None
    ):
        return ""
    return str(applicability.site_admission.canonical_pnu or "").strip()


def admit_verified_site_inputs(
    *,
    site: Any,
    historical_handoff_authorization: Optional[
        HistoricalTrustedInternalSourceHandoffAuthorization
    ] = None,
    historical_site_applicability_admission: Optional[
        HistoricalSiteEventSiteApplicabilityAdmissionResult
    ] = None,
    historical_promotion_rule_input_bridge: Optional[
        HistoricalSiteEventSiteTruthPromotionRuleInputBridge
    ] = None,
    district_unit_plan_registry_candidate: Optional[Any] = None,
) -> VerifiedSiteInputs:
    raw_historical_rule_input = None
    verified_historical_input = None
    verified_district_unit_plan_input = None
    actual_site_pnu = ""

    legacy_requested = bool(
        historical_handoff_authorization is not None
        or historical_site_applicability_admission is not None
    )
    promotion_requested = historical_promotion_rule_input_bridge is not None
    historical_requested = legacy_requested or promotion_requested
    district_requested = district_unit_plan_registry_candidate is not None

    if legacy_requested and promotion_requested:
        raise VerifiedSiteInputAdmissionError(
            "Historical SITE input is ambiguous: legacy and promotion paths cannot be used together"
        )
    if historical_requested and district_requested:
        raise VerifiedSiteInputAdmissionError(
            "Historical and district-unit verified SITE inputs cannot be combined"
        )

    if district_requested:
        envelope = district_unit_plan_registry_candidate
        if (
            not isinstance(
                envelope,
                DistrictUnitPlanVerifiedRegistryCandidateEnvelope,
            )
            or not envelope.ready
        ):
            raise VerifiedSiteInputAdmissionError(
                "District-unit verified registry candidate envelope is not ready"
            )
        actual_site_pnu = _actual_site_pnu(site)
        if not actual_site_pnu or actual_site_pnu != envelope.canonical_pnu:
            raise VerifiedSiteInputAdmissionError(
                "District-unit verified registry candidate PNU rebinding failed"
            )
        verified_district_unit_plan_input = envelope

    if promotion_requested:
        bridge = historical_promotion_rule_input_bridge
        if (
            not isinstance(
                bridge,
                HistoricalSiteEventSiteTruthPromotionRuleInputBridge,
            )
            or not bridge.ready
        ):
            raise VerifiedSiteInputAdmissionError(
                "Historical SITE promotion rule-input bridge is not ready"
            )
        actual_site_pnu = _actual_site_pnu(site)
        repairs = bridge.historical_rule_input.get("repairs")
        repair_pnus = {
            str(repair.get("pnu") or "").strip()
            for repair in repairs or []
            if isinstance(repair, dict)
        }
        if (
            not actual_site_pnu
            or len(repair_pnus) != 1
            or actual_site_pnu not in repair_pnus
        ):
            raise VerifiedSiteInputAdmissionError(
                "Historical SITE promotion PNU rebinding failed"
            )
        raw_historical_rule_input = copy.deepcopy(
            dict(bridge.historical_rule_input)
        )
    elif legacy_requested:
        actual_site_pnu = _actual_site_pnu(site)
        admitted_pnu = _admitted_canonical_pnu(
            historical_site_applicability_admission
        )
        if (
            not actual_site_pnu
            or not admitted_pnu
            or actual_site_pnu != admitted_pnu
        ):
            raise VerifiedSiteInputAdmissionError(
                "Historical SITE applicability PNU rebinding failed"
            )

        consistency = (
            authorize_historical_site_event_candidate_repair_consistency(
                historical_site_applicability_admission,
                historical_handoff_authorization,
            )
        )
        if not consistency.authorized:
            raise VerifiedSiteInputAdmissionError(
                "Historical SITE candidate/repair consistency failed: "
                f"{consistency.status} / {','.join(consistency.missing_gates)}"
            )

        binding = authorize_historical_site_event_candidate_condition_binding(
            historical_site_applicability_admission,
            historical_handoff_authorization,
        )
        if not binding.authorized:
            raise VerifiedSiteInputAdmissionError(
                "Historical SITE candidate/condition binding failed: "
                f"{binding.status} / {','.join(binding.missing_gates)}"
            )

        adapter = adapt_admitted_historical_site_event_rule_input(
            historical_site_applicability_admission,
            historical_handoff_authorization,
        )
        if not adapter.ready:
            raise VerifiedSiteInputAdmissionError(
                "Historical SITE applicability/handoff admission failed: "
                f"{adapter.status} / {','.join(adapter.missing_gates)}"
            )
        raw_historical_rule_input = copy.deepcopy(
            dict(adapter.historical_rule_input)
        )

    if raw_historical_rule_input is not None:
        verified_historical_input = seal_verified_historical_rule_input(
            canonical_pnu=actual_site_pnu,
            historical_rule_input=raw_historical_rule_input,
        )
        if not verified_historical_input.ready:
            raise VerifiedSiteInputAdmissionError(
                "Historical verified rule-input envelope is not ready"
            )

    return VerifiedSiteInputs(
        historical_rule_input=verified_historical_input,
        district_unit_plan_registry_candidate=verified_district_unit_plan_input,
    )
