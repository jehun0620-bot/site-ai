# -*- coding: utf-8 -*-

"""SITE Analysis Service Orchestrator.

Historical Rule Engine input is fail-closed: the existing trusted handoff and
PNU-bound SITE applicability admission must both pass before historical input
is forwarded to the existing service/builder path. The admitted PNU is also
rebound to the actual Site object created for this analysis request.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from site_data.site_builder import create_site
from site_data.site_analysis_service import analyze_site_object, site_to_analysis_input
from site_data.site_analysis_response import build_site_analysis_response

from law_data.historical_site_event_admitted_rule_input_adapter import (
    adapt_admitted_historical_site_event_rule_input,
)
from law_data.historical_site_event_site_applicability_admission import (
    HistoricalSiteEventSiteApplicabilityAdmissionResult,
)
from law_data.historical_trusted_internal_source_handoff_authorization import (
    HistoricalTrustedInternalSourceHandoffAuthorization,
)


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BUILDING_API_URL = (
    "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
)


class SiteAnalysisError(RuntimeError):
    pass


class BuildingAPIError(SiteAnalysisError):
    pass


class SiteBuildError(SiteAnalysisError):
    pass


def fetch_building_items(
    *,
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    service_key: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    key = service_key or os.getenv("DATA_API_KEY")
    if not key:
        raise BuildingAPIError("DATA_API_KEY를 찾을 수 없습니다.")

    params = {
        "sigunguCd": str(sigungu_cd),
        "bjdongCd": str(bjdong_cd),
        "bun": str(bun),
        "ji": str(ji),
        "serviceKey": key,
        "numOfRows": "100",
        "pageNo": "1",
        "_type": "json",
    }

    try:
        response = requests.get(
            BUILDING_API_URL,
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise BuildingAPIError(f"건축HUB 요청 실패: {exc}") from exc

    if response.status_code != 200:
        raise BuildingAPIError(f"건축HUB HTTP 오류: {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        content_type = response.headers.get("Content-Type", "")
        response_text = response.text or ""
        response_preview = response_text[:500].replace("\r", " ").replace("\n", " ")
        raise BuildingAPIError(
            "건축HUB 응답 JSON 파싱 실패"
            f" | HTTP={response.status_code}"
            f" | Content-Type={content_type}"
            f" | Length={len(response_text)}"
            f" | Preview={response_preview!r}"
        ) from exc

    api_response = data.get("response")
    if not isinstance(api_response, dict):
        raise BuildingAPIError("건축HUB response 없음")

    header = api_response.get("header", {})
    if header.get("resultCode") != "00":
        raise BuildingAPIError(
            "건축HUB API 오류: "
            f"{header.get('resultCode')} / {header.get('resultMsg')}"
        )

    body = api_response.get("body", {})
    items_container = body.get("items") or {}
    items = items_container.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []

    return {
        "items": items,
        "total_count": body.get("totalCount", 0),
        "result_code": header.get("resultCode"),
        "result_message": header.get("resultMsg"),
    }


def _actual_site_pnu(site: Any) -> str:
    """Reuse the existing service identity adapter to derive the actual Site PNU."""

    try:
        site_input = site_to_analysis_input(site)
    except (TypeError, ValueError, AttributeError):
        return ""

    pnu = str(site_input.get("pnu") or "").strip()
    if len(pnu) != 19 or not pnu.isdigit():
        return ""
    return pnu


def _admitted_canonical_pnu(
    applicability: HistoricalSiteEventSiteApplicabilityAdmissionResult | None,
) -> str:
    if not isinstance(applicability, HistoricalSiteEventSiteApplicabilityAdmissionResult):
        return ""
    if not applicability.admitted or applicability.site_admission is None:
        return ""
    return str(applicability.site_admission.canonical_pnu or "").strip()


def analyze_site_by_parcel(
    *,
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    project_profile: Optional[Dict[str, str]] = None,
    procedure_profile: Optional[Dict[str, str]] = None,
    production_condition_shadow_sources: Optional[Any] = None,
    historical_handoff_authorization: Optional[
        HistoricalTrustedInternalSourceHandoffAuthorization
    ] = None,
    historical_site_applicability_admission: Optional[
        HistoricalSiteEventSiteApplicabilityAdmissionResult
    ] = None,
    include_debug: bool = False,
    service_key: Optional[str] = None,
) -> Dict[str, Any]:
    building_result = fetch_building_items(
        sigungu_cd=sigungu_cd,
        bjdong_cd=bjdong_cd,
        bun=bun,
        ji=ji,
        service_key=service_key,
    )
    items = building_result["items"]
    if not items:
        raise SiteBuildError("건축HUB에서 건축물 데이터를 찾지 못했습니다.")

    site = create_site(items)
    if site is None:
        raise SiteBuildError("Site 객체 생성 실패")

    historical_rule_input = None
    historical_requested = bool(
        historical_handoff_authorization is not None
        or historical_site_applicability_admission is not None
    )

    if historical_requested:
        actual_site_pnu = _actual_site_pnu(site)
        admitted_pnu = _admitted_canonical_pnu(
            historical_site_applicability_admission
        )
        if not actual_site_pnu or not admitted_pnu or actual_site_pnu != admitted_pnu:
            raise SiteAnalysisError(
                "Historical SITE applicability PNU rebinding failed"
            )

        adapter_result = adapt_admitted_historical_site_event_rule_input(
            historical_site_applicability_admission,
            historical_handoff_authorization,
        )
        if not adapter_result.ready:
            raise SiteAnalysisError(
                "Historical SITE applicability/handoff admission failed: "
                f"{adapter_result.status} / "
                f"{','.join(adapter_result.missing_gates)}"
            )
        historical_rule_input = copy.deepcopy(
            dict(adapter_result.historical_rule_input)
        )

    analysis = analyze_site_object(
        site=site,
        project_profile=project_profile or {},
        procedure_profile=procedure_profile or {},
        production_condition_shadow_sources=production_condition_shadow_sources,
        historical_rule_input=historical_rule_input,
    )

    response = build_site_analysis_response(
        analysis,
        include_debug=include_debug,
    )
    response["service"] = {
        "building_count": len(items),
        "building_total_count": building_result.get("total_count"),
        "building_api_status": building_result.get("result_code"),
    }
    return response
