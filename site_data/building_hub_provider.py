# -*- coding: utf-8 -*-
"""Building HUB provider boundary for SITE analysis."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

BUILDING_API_URL = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"


class BuildingAPIError(RuntimeError):
    pass


def fetch_building_items(
    *,
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    plat_gb_cd: str = "0",
    service_key: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    key = service_key or os.getenv("DATA_API_KEY")
    if not key:
        raise BuildingAPIError("DATA_API_KEY를 찾을 수 없습니다.")

    params = {
        "sigunguCd": str(sigungu_cd),
        "bjdongCd": str(bjdong_cd),
        "platGbCd": str(plat_gb_cd),
        "bun": str(bun),
        "ji": str(ji),
        "serviceKey": key,
        "numOfRows": "100",
        "pageNo": "1",
        "_type": "json",
    }
    try:
        response = requests.get(BUILDING_API_URL, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise BuildingAPIError(f"건축HUB 요청 실패: {exc}") from exc
    if response.status_code != 200:
        raise BuildingAPIError(f"건축HUB HTTP 오류: {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise BuildingAPIError("건축HUB 응답 JSON 파싱 실패") from exc

    api_response = data.get("response")
    if not isinstance(api_response, dict):
        raise BuildingAPIError("건축HUB response 없음")

    header = api_response.get("header", {})
    if header.get("resultCode") != "00":
        raise BuildingAPIError(
            f"건축HUB API 오류: {header.get('resultCode')} / {header.get('resultMsg')}"
        )

    body = api_response.get("body", {})
    items = (body.get("items") or {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []

    raw_total_count = body.get("totalCount")
    try:
        total_count = (
            int(raw_total_count)
            if raw_total_count is not None and str(raw_total_count).strip()
            else 0
        )
    except (TypeError, ValueError) as exc:
        raise BuildingAPIError(
            f"건축HUB totalCount 형식 오류: {raw_total_count}"
        ) from exc

    return {
        "items": items,
        "total_count": total_count,
        "result_code": header.get("resultCode"),
        "result_message": header.get("resultMsg"),
    }
