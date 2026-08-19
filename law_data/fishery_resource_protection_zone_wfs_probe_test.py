# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-9A
수산자원보호구역 공식 WFS source / geometry probe

목표
--------------------------------------------------
1. 해양수산부 공식 수산자원보호구역 WFS API를
   FISHERY_RESOURCE_API_KEY로 호출한다.
2. 양성대조(영광보전지역)를 먼저 조회하여
   정상응답 / geometry 형식을 확인한다.
3. 기존 검증된 SITE EPSG:5179 BBOX를 복원하여 공간조회한다.
4. geometry 좌표계 / 파싱이 검증되기 전에는 FALSE를 확정하지 않는다.
5. 실제 Parcel Polygon intersection은 다음 단계에서 안전하게 수행할 수 있도록
   원문 evidence를 충분히 저장한다.

중요 판정 원칙
--------------------------------------------------
- HTTP 실패 -> UNKNOWN
- 양성대조 실패 -> UNKNOWN
- SITE BBOX 0건만으로 즉시 FALSE 확정 금지
- geom 파싱 실패 -> UNKNOWN
- source / CRS 미확정 -> UNKNOWN
- 실제 geometry evidence가 확보되어야 다음 intersection 단계로 진행
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from shapely import wkt
from shapely.geometry.base import BaseGeometry


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-9A "
    "수산자원보호구역 공식 WFS source / geometry probe"
)


# ============================================================
# 프로젝트 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

MAPPLAN_LIVE_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_mapplan_live.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "fishery_resource_protection_zone_wfs_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(BASE_DIR / ".env")

FISHERY_RESOURCE_API_KEY = os.getenv(
    "FISHERY_RESOURCE_API_KEY"
)


# ============================================================
# 공식 API
# ============================================================

API_URL = (
    "http://apis.data.go.kr/1192000/"
    "apVhdService_FshrsrcPzn/"
    "getOpnFshrsrcPznWFS"
)

POSITIVE_CONTROL_NAME = "영광보전지역"

REQUEST_TIMEOUT = 30
MAX_FEATURES = 100


# ============================================================
# 공통 함수
# ============================================================

def print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(f"=== {title} ===")
    print("=" * 72)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(data: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split(
            "}",
            1,
        )[1]

    return tag


def first_value(
    data: Dict[str, Any],
    *keys: str,
) -> Any:
    for key in keys:
        value = data.get(key)

        if value not in (
            None,
            "",
        ):
            return value

    return None


# ============================================================
# SITE context
# ============================================================

def get_site_context() -> Dict[str, Any]:
    data = load_json(
        QUERY_CONTEXT_PATH
    )

    query_context = data.get(
        "query_context",
        {},
    )

    return {
        "site_id": normalize_text(
            query_context.get("site_id")
        ),
        "address": normalize_text(
            query_context.get("address")
        ),
        "pnu": normalize_text(
            query_context.get("pnu")
        ),
    }


def get_site_bbox_epsg5179() -> Optional[List[float]]:
    """
    기존 MapPlan 단계에서 검증한 Parcel 검색 BBOX를 재사용한다.

    우선순위:
    1. search_epsg5179
    2. epsg5179
    """

    data = load_json(
        MAPPLAN_LIVE_PATH
    )

    parcel_bbox = data.get(
        "parcel_bbox",
        {},
    )

    bbox = parcel_bbox.get(
        "search_epsg5179"
    )

    if (
        isinstance(bbox, list)
        and len(bbox) == 4
    ):
        try:
            return [
                float(x)
                for x in bbox
            ]

        except (
            TypeError,
            ValueError,
        ):
            pass

    bbox = parcel_bbox.get(
        "epsg5179"
    )

    if (
        isinstance(bbox, list)
        and len(bbox) == 4
    ):
        try:
            return [
                float(x)
                for x in bbox
            ]

        except (
            TypeError,
            ValueError,
        ):
            pass

    return None


def bbox_to_text(
    bbox: List[float]
) -> str:
    return ",".join(
        str(x)
        for x in bbox
    )


# ============================================================
# HTTP
# ============================================================

def mask_api_key(
    value: str,
) -> str:
    """
    로그 / JSON evidence에 API Key가 남지 않도록 마스킹
    """

    if not FISHERY_RESOURCE_API_KEY:
        return value

    masked = value.replace(
        FISHERY_RESOURCE_API_KEY,
        "[HIDDEN]",
    )

    # requests가 URL encoding한 경우를 대비한 추가 보호
    try:
        from urllib.parse import quote

        encoded_key = quote(
            FISHERY_RESOURCE_API_KEY,
            safe="",
        )

        masked = masked.replace(
            encoded_key,
            "[HIDDEN]",
        )

    except Exception:
        pass

    return masked


def request_api(
    params: Dict[str, Any]
) -> Dict[str, Any]:

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Accept": (
                    "application/xml,"
                    "text/xml,"
                    "application/json,"
                    "*/*"
                ),
            },
        )

        text = response.text

        return {
            "http_status": (
                response.status_code
            ),
            "content_type": (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            ),
            "url": mask_api_key(
                response.url
            ),
            "text": text,
            "error": None,
        }

    except Exception as e:

        return {
            "http_status": None,
            "content_type": "",
            "url": API_URL,
            "text": "",
            "error": str(e),
        }


# ============================================================
# XML parsing
# ============================================================

def parse_xml_items(
    text: str
) -> Tuple[
    List[Dict[str, Any]],
    Dict[str, Any],
]:

    items: List[
        Dict[str, Any]
    ] = []

    meta = {
        "xml_parse_success": False,
        "result_code": None,
        "result_msg": None,
        "total_count": None,
    }

    try:
        root = ET.fromstring(
            text
        )

        meta[
            "xml_parse_success"
        ] = True

    except Exception:
        return (
            items,
            meta,
        )

    for elem in root.iter():

        name = strip_namespace(
            elem.tag
        )

        value = normalize_text(
            elem.text
        )

        if name in (
            "resultCode",
            "result_code",
        ):
            meta[
                "result_code"
            ] = value

        elif name in (
            "resultMsg",
            "result_msg",
        ):
            meta[
                "result_msg"
            ] = value

        elif name in (
            "totalCount",
            "total_count",
        ):
            meta[
                "total_count"
            ] = value

    # --------------------------------------------------------
    # 일반적인 <item> 구조
    # --------------------------------------------------------

    for elem in root.iter():

        if (
            strip_namespace(
                elem.tag
            ).lower()
            != "item"
        ):
            continue

        item: Dict[
            str,
            Any,
        ] = {}

        for child in list(
            elem
        ):

            key = strip_namespace(
                child.tag
            )

            if list(child):

                value = ET.tostring(
                    child,
                    encoding="unicode",
                )

            else:

                value = normalize_text(
                    child.text
                )

            item[key] = value

        if item:
            items.append(
                item
            )

    # --------------------------------------------------------
    # item wrapper가 없는 경우 보조 탐색
    # --------------------------------------------------------

    if not items:

        candidates = []

        for elem in root.iter():

            child_names = {
                strip_namespace(
                    c.tag
                )
                for c in list(elem)
            }

            if (
                "geom"
                in child_names
                or "fshrsrc_pzn_cd"
                in child_names
                or "fshrsrc_pzn_nm"
                in child_names
                or "fshrsr_pzn_cd"
                in child_names
                or "fshrsr_pzn_nm"
                in child_names
            ):
                candidates.append(
                    elem
                )

        for elem in candidates:

            item = {}

            for child in list(
                elem
            ):

                key = strip_namespace(
                    child.tag
                )

                if list(child):

                    value = ET.tostring(
                        child,
                        encoding="unicode",
                    )

                else:

                    value = normalize_text(
                        child.text
                    )

                item[key] = value

            if item:
                items.append(
                    item
                )

    return (
        items,
        meta,
    )


# ============================================================
# JSON parsing
# ============================================================

def parse_json_items(
    text: str
) -> Tuple[
    List[Dict[str, Any]],
    Dict[str, Any],
]:

    meta = {
        "json_parse_success": False,
        "result_code": None,
        "result_msg": None,
        "total_count": None,
    }

    try:
        data = json.loads(
            text
        )

        meta[
            "json_parse_success"
        ] = True

    except Exception:
        return (
            [],
            meta,
        )

    def walk(
        value: Any
    ) -> List[
        Dict[str, Any]
    ]:

        found: List[
            Dict[str, Any]
        ] = []

        if isinstance(
            value,
            dict,
        ):

            if (
                "geom" in value
                or "fshrsrc_pzn_cd"
                in value
                or "fshrsrc_pzn_nm"
                in value
                or "fshrsr_pzn_cd"
                in value
                or "fshrsr_pzn_nm"
                in value
            ):
                found.append(
                    value
                )

            for child in value.values():
                found.extend(
                    walk(child)
                )

        elif isinstance(
            value,
            list,
        ):

            for child in value:
                found.extend(
                    walk(child)
                )

        return found

    items = walk(
        data
    )

    def find_key(
        value: Any,
        target: str,
    ) -> Any:

        if isinstance(
            value,
            dict,
        ):

            if target in value:
                return value[
                    target
                ]

            for child in value.values():

                result = find_key(
                    child,
                    target,
                )

                if result is not None:
                    return result

        elif isinstance(
            value,
            list,
        ):

            for child in value:

                result = find_key(
                    child,
                    target,
                )

                if result is not None:
                    return result

        return None

    meta[
        "result_code"
    ] = find_key(
        data,
        "resultCode",
    )

    meta[
        "result_msg"
    ] = find_key(
        data,
        "resultMsg",
    )

    meta[
        "total_count"
    ] = find_key(
        data,
        "totalCount",
    )

    return (
        items,
        meta,
    )


def parse_response(
    text: str
) -> Dict[str, Any]:

    xml_items, xml_meta = (
        parse_xml_items(
            text
        )
    )

    if xml_meta[
        "xml_parse_success"
    ]:

        return {
            "format": "XML",
            "items": xml_items,
            "meta": xml_meta,
        }

    json_items, json_meta = (
        parse_json_items(
            text
        )
    )

    if json_meta[
        "json_parse_success"
    ]:

        return {
            "format": "JSON",
            "items": json_items,
            "meta": json_meta,
        }

    return {
        "format": "UNKNOWN",
        "items": [],
        "meta": {
            "xml_parse_success": False,
            "json_parse_success": False,
        },
    }


# ============================================================
# geometry parsing
# ============================================================

def get_geom_text(
    item: Dict[str, Any]
) -> str:

    for key in (
        "geom",
        "geometry",
        "GEOM",
    ):

        value = item.get(
            key
        )

        if value not in (
            None,
            "",
        ):

            return normalize_text(
                value
            )

    return ""


def try_parse_wkt(
    text: str
) -> Optional[
    BaseGeometry
]:

    if not text:
        return None

    candidates = [
        text
    ]

    # XML/GML wrapper 안에 WKT 문자열이 들어있는 경우 대비
    wkt_match = re.search(
        (
            r"("
            r"(?:MULTI)?POLYGON"
            r"\s*(?:Z|M|ZM)?"
            r"\s*\(\(?.*\)\)?"
            r")"
        ),
        text,
        flags=(
            re.I
            | re.S
        ),
    )

    if wkt_match:
        candidates.append(
            wkt_match.group(1)
        )

    for candidate in candidates:

        try:
            geom = wkt.loads(
                candidate
            )

            if (
                geom is not None
                and not geom.is_empty
            ):
                return geom

        except Exception:
            continue

    return None


def geometry_summary(
    item: Dict[str, Any]
) -> Dict[str, Any]:

    geom_text = get_geom_text(
        item
    )

    geom = try_parse_wkt(
        geom_text
    )

    if geom is None:

        number_tokens = re.findall(
            r"-?\d+(?:\.\d+)?",
            geom_text,
        )

        number_preview = []

        for value in number_tokens[
            :12
        ]:
            try:
                number_preview.append(
                    float(value)
                )
            except ValueError:
                pass

        return {
            "geom_present": (
                bool(geom_text)
            ),
            "wkt_parse_success": False,
            "geometry_type": None,
            "is_valid": None,
            "bounds": None,
            "area": None,
            "number_preview": (
                number_preview
            ),
            "geom_preview": (
                geom_text[:500]
            ),
        }

    return {
        "geom_present": True,
        "wkt_parse_success": True,
        "geometry_type": (
            geom.geom_type
        ),
        "is_valid": (
            bool(geom.is_valid)
        ),
        "bounds": [
            float(x)
            for x in geom.bounds
        ],
        "area": (
            float(geom.area)
        ),
        "number_preview": [],
        "geom_preview": (
            geom_text[:500]
        ),
    }


def summarize_items(
    items: List[
        Dict[str, Any]
    ]
) -> List[
    Dict[str, Any]
]:

    result = []

    for item in items:

        result.append(
            {
                "code": first_value(
                    item,
                    "fshrsrc_pzn_cd",
                    "fshrsr_pzn_cd",
                ),
                "name": first_value(
                    item,
                    "fshrsrc_pzn_nm",
                    "fshrsr_pzn_nm",
                ),
                "declared_area": first_value(
                    item,
                    "fshrsrc_pzn_ar",
                    "fshrsr_pzn_ar",
                ),
                "geometry": (
                    geometry_summary(
                        item
                    )
                ),
            }
        )

    return result


# ============================================================
# 판정 보조
# ============================================================

def is_http_success(
    result: Dict[str, Any]
) -> bool:

    status = result.get(
        "http_status"
    )

    return (
        isinstance(
            status,
            int,
        )
        and 200 <= status < 300
    )


def has_parseable_geometry(
    summaries: List[
        Dict[str, Any]
    ]
) -> bool:

    return any(
        item.get(
            "geometry",
            {},
        ).get(
            "wkt_parse_success"
        )
        for item in summaries
    )


def infer_crs_compatibility(
    positive_summaries: List[
        Dict[str, Any]
    ],
    site_bbox: List[float],
) -> Dict[str, Any]:

    """
    CRS를 코드만 보고 단정하지 않는다.

    양성대조 geometry의 좌표 크기와
    SITE EPSG:5179 BBOX 좌표 크기를 비교하여
    동일한 한국 TM 계열처럼 보이는지만 확인한다.

    공식 CRS 메타데이터가 확정되기 전에는
    동일 CRS로 최종 확정하지 않는다.
    """

    positive_bounds = [
        item[
            "geometry"
        ][
            "bounds"
        ]
        for item in positive_summaries
        if item.get(
            "geometry",
            {},
        ).get(
            "bounds"
        )
    ]

    if not positive_bounds:

        return {
            "status": "UNVERIFIED",
            "reason": (
                "양성대조 geometry bounds를 "
                "확보하지 못해 CRS 호환성을 "
                "검증할 수 없음"
            ),
        }

    sample = positive_bounds[
        0
    ]

    site_scale_ok = (
        100000
        <= abs(site_bbox[0])
        <= 3000000
        and
        100000
        <= abs(site_bbox[1])
        <= 3000000
    )

    positive_scale_ok = (
        100000
        <= abs(sample[0])
        <= 3000000
        and
        100000
        <= abs(sample[1])
        <= 3000000
    )

    if (
        site_scale_ok
        and positive_scale_ok
    ):

        return {
            "status": (
                "COMPATIBLE_CANDIDATE"
            ),
            "reason": (
                "양성대조와 SITE BBOX가 모두 "
                "미터 단위 한국 TM 계열로 보이는 "
                "좌표 범위를 사용함. "
                "단, 공식 CRS 메타데이터 확정 전에는 "
                "동일 CRS로 단정하지 않음"
            ),
            "positive_bounds_sample": (
                sample
            ),
        }

    return {
        "status": "UNVERIFIED",
        "reason": (
            "양성대조 geometry와 SITE BBOX의 "
            "좌표 범위 호환성을 확인하지 못함"
        ),
        "positive_bounds_sample": (
            sample
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    print_section(
        STEP_NAME
    )

    site = get_site_context()

    site_bbox = (
        get_site_bbox_epsg5179()
    )

    print(
        "SITE ID:",
        site.get("site_id"),
    )

    print(
        "주소:",
        site.get("address"),
    )

    print(
        "PNU:",
        site.get("pnu"),
    )

    print(
        "FISHERY_RESOURCE_API_KEY:",
        (
            "FOUND"
            if FISHERY_RESOURCE_API_KEY
            else "MISSING"
        ),
    )

    # --------------------------------------------------------
    # API Key 없음
    # --------------------------------------------------------

    if not FISHERY_RESOURCE_API_KEY:

        result = {
            "step": STEP_NAME,
            "site": site,
            "api": {
                "provider": "해양수산부",
                "endpoint": API_URL,
                "environment_variable": (
                    "FISHERY_RESOURCE_API_KEY"
                ),
            },
            "site_resolution": {
                "query_status": (
                    "NOT_CONNECTED"
                ),
                "resolution": "UNKNOWN",
                "confidence": "NONE",
                "reason": (
                    "FISHERY_RESOURCE_API_KEY "
                    "환경변수를 읽지 못함"
                ),
            },
        }

        save_json(
            result
        )

        print()
        print(
            "ERROR: "
            "FISHERY_RESOURCE_API_KEY를 "
            "찾을 수 없습니다."
        )

        print(
            "OUTPUT:",
            OUTPUT_PATH,
        )

        return 1

    # --------------------------------------------------------
    # SITE BBOX 없음
    # --------------------------------------------------------

    if not site_bbox:

        result = {
            "step": STEP_NAME,
            "site": site,
            "api": {
                "provider": "해양수산부",
                "endpoint": API_URL,
                "environment_variable": (
                    "FISHERY_RESOURCE_API_KEY"
                ),
            },
            "site_resolution": {
                "query_status": (
                    "NOT_QUERIED"
                ),
                "resolution": "UNKNOWN",
                "confidence": "NONE",
                "reason": (
                    "기존 검증된 EPSG:5179 "
                    "Parcel BBOX를 복원하지 못함"
                ),
            },
        }

        save_json(
            result
        )

        print()

        print(
            "ERROR: SITE EPSG:5179 "
            "BBOX를 복원하지 못했습니다."
        )

        print(
            "OUTPUT:",
            OUTPUT_PATH,
        )

        return 1

    print(
        "SITE search BBOX:",
        site_bbox,
    )

    # ========================================================
    # 1. 양성대조
    # ========================================================

    print_section(
        "1. 양성대조 조회"
    )

    positive_params = {
        "serviceKey": (
            FISHERY_RESOURCE_API_KEY
        ),
        "fshrsr_pzn_nm": (
            POSITIVE_CONTROL_NAME
        ),
        "maxFeatures": (
            MAX_FEATURES
        ),
    }

    positive_http = request_api(
        positive_params
    )

    positive_parsed = (
        parse_response(
            positive_http.get(
                "text",
                "",
            )
        )
    )

    positive_items = (
        positive_parsed.get(
            "items",
            [],
        )
    )

    positive_summaries = (
        summarize_items(
            positive_items
        )
    )

    print(
        "HTTP:",
        positive_http.get(
            "http_status"
        ),
    )

    print(
        "Content-Type:",
        positive_http.get(
            "content_type"
        ),
    )

    print(
        "format:",
        positive_parsed.get(
            "format"
        ),
    )

    print(
        "resultCode:",
        positive_parsed.get(
            "meta",
            {},
        ).get(
            "result_code"
        ),
    )

    print(
        "resultMsg:",
        positive_parsed.get(
            "meta",
            {},
        ).get(
            "result_msg"
        ),
    )

    print(
        "feature count:",
        len(
            positive_items
        ),
    )

    print(
        "parseable geometry:",
        has_parseable_geometry(
            positive_summaries
        ),
    )

    # ========================================================
    # 2. SITE BBOX 조회
    # ========================================================

    print_section(
        "2. SITE BBOX 조회"
    )

    site_params = {
        "serviceKey": (
            FISHERY_RESOURCE_API_KEY
        ),
        "bbox": bbox_to_text(
            site_bbox
        ),
        "maxFeatures": (
            MAX_FEATURES
        ),
    }

    site_http = request_api(
        site_params
    )

    site_parsed = (
        parse_response(
            site_http.get(
                "text",
                "",
            )
        )
    )

    site_items = (
        site_parsed.get(
            "items",
            [],
        )
    )

    site_summaries = (
        summarize_items(
            site_items
        )
    )

    print(
        "HTTP:",
        site_http.get(
            "http_status"
        ),
    )

    print(
        "Content-Type:",
        site_http.get(
            "content_type"
        ),
    )

    print(
        "format:",
        site_parsed.get(
            "format"
        ),
    )

    print(
        "resultCode:",
        site_parsed.get(
            "meta",
            {},
        ).get(
            "result_code"
        ),
    )

    print(
        "resultMsg:",
        site_parsed.get(
            "meta",
            {},
        ).get(
            "result_msg"
        ),
    )

    print(
        "feature count:",
        len(
            site_items
        ),
    )

    print(
        "parseable geometry:",
        has_parseable_geometry(
            site_summaries
        ),
    )

    # ========================================================
    # 3. CRS / evidence 상태
    # ========================================================

    crs_check = (
        infer_crs_compatibility(
            positive_summaries,
            site_bbox,
        )
    )

    positive_ok = (
        is_http_success(
            positive_http
        )
        and len(
            positive_items
        ) > 0
        and has_parseable_geometry(
            positive_summaries
        )
    )

    site_query_ok = (
        is_http_success(
            site_http
        )
    )

    # --------------------------------------------------------
    # 판정
    # --------------------------------------------------------

    if not positive_ok:

        query_status = (
            "QUERY_FAILED"
            if not is_http_success(
                positive_http
            )
            else "QUERY_SUCCESS"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "공식 API 양성대조에서 정상 geometry evidence를 "
            "확보하지 못했으므로 SITE TRUE/FALSE 판정을 진행하지 않음"
        )

    elif not site_query_ok:

        query_status = (
            "QUERY_FAILED"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "양성대조는 확인되었으나 SITE BBOX 요청이 "
            "정상 완료되지 않아 UNKNOWN 유지"
        )

    elif len(
        site_items
    ) == 0:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "공식 API 양성대조 및 SITE BBOX 조회는 정상 수행되었고 "
            "SITE BBOX 결과가 0건임. 그러나 CRS 공식 확정 및 "
            "Parcel Polygon intersection 검증 전이므로 "
            "FALSE를 아직 확정하지 않고 다음 단계로 전달"
        )

    else:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "SITE BBOX에서 수산자원보호구역 feature를 확보함. "
            "실제 Parcel Polygon과 geometry 면적교차를 확인해야 "
            "TRUE/FALSE 확정 가능"
        )

    # ========================================================
    # 결과 JSON
    # ========================================================

    result = {

        "step": STEP_NAME,

        "site": site,

        "source": {
            "provider": (
                "해양수산부"
            ),
            "dataset": (
                "수산자원보호구역"
            ),
            "api_type": (
                "WFS"
            ),
            "endpoint": (
                API_URL
            ),
            "environment_variable": (
                "FISHERY_RESOURCE_API_KEY"
            ),
            "official_request_fields": [
                "serviceKey",
                "bbox",
                "maxFeatures",
                "fshrsr_pzn_nm",
            ],
            "official_response_fields": [
                "fshrsrc_pzn_cd",
                "fshrsrc_pzn_nm",
                "fshrsrc_pzn_ar",
                "geom",
            ],
        },

        "parcel_bbox": {
            "crs_candidate": (
                "EPSG:5179"
            ),
            "source": str(
                MAPPLAN_LIVE_PATH
            ),
            "search_bbox": (
                site_bbox
            ),
        },

        "positive_control": {
            "name": (
                POSITIVE_CONTROL_NAME
            ),
            "request": {
                "params": {
                    "serviceKey": (
                        "[HIDDEN]"
                    ),
                    "fshrsr_pzn_nm": (
                        POSITIVE_CONTROL_NAME
                    ),
                    "maxFeatures": (
                        MAX_FEATURES
                    ),
                },
            },
            "http": {
                "status": (
                    positive_http.get(
                        "http_status"
                    )
                ),
                "content_type": (
                    positive_http.get(
                        "content_type"
                    )
                ),
                "url": (
                    positive_http.get(
                        "url"
                    )
                ),
                "error": (
                    positive_http.get(
                        "error"
                    )
                ),
            },
            "response": {
                "format": (
                    positive_parsed.get(
                        "format"
                    )
                ),
                "meta": (
                    positive_parsed.get(
                        "meta"
                    )
                ),
                "feature_count": len(
                    positive_items
                ),
                "features": (
                    positive_summaries
                ),
                "raw_preview": (
                    positive_http.get(
                        "text",
                        "",
                    )[:2000]
                ),
            },
        },

        "site_bbox_query": {
            "request": {
                "params": {
                    "serviceKey": (
                        "[HIDDEN]"
                    ),
                    "bbox": (
                        bbox_to_text(
                            site_bbox
                        )
                    ),
                    "maxFeatures": (
                        MAX_FEATURES
                    ),
                },
            },
            "http": {
                "status": (
                    site_http.get(
                        "http_status"
                    )
                ),
                "content_type": (
                    site_http.get(
                        "content_type"
                    )
                ),
                "url": (
                    site_http.get(
                        "url"
                    )
                ),
                "error": (
                    site_http.get(
                        "error"
                    )
                ),
            },
            "response": {
                "format": (
                    site_parsed.get(
                        "format"
                    )
                ),
                "meta": (
                    site_parsed.get(
                        "meta"
                    )
                ),
                "feature_count": len(
                    site_items
                ),
                "features": (
                    site_summaries
                ),
                "raw_preview": (
                    site_http.get(
                        "text",
                        "",
                    )[:2000]
                ),
            },
        },

        "crs_validation": (
            crs_check
        ),

        "site_resolution": {
            "query_status": (
                query_status
            ),
            "resolution": (
                resolution
            ),
            "confidence": (
                confidence
            ),
            "reason": (
                reason
            ),
        },

        "validation": {

            "FISHERY_RESOURCE_API_KEY 로드": (
                bool(
                    FISHERY_RESOURCE_API_KEY
                )
            ),

            "SITE PNU 19자리": (
                len(
                    site.get(
                        "pnu",
                        "",
                    )
                )
                == 19
            ),

            "기존 EPSG:5179 BBOX 복원": (
                bool(
                    site_bbox
                )
            ),

            "공식 API 양성대조 HTTP 성공": (
                is_http_success(
                    positive_http
                )
            ),

            "양성대조 Feature 존재": (
                len(
                    positive_items
                )
                > 0
            ),

            "양성대조 geometry 파싱": (
                has_parseable_geometry(
                    positive_summaries
                )
            ),

            "SITE BBOX HTTP 성공": (
                site_query_ok
            ),

            "SITE BBOX 결과만으로 FALSE 금지": (
                True
            ),

            "Parcel intersection 전 TRUE 금지": (
                True
            ),

            "CRS 미확정 시 UNKNOWN 유지": (
                True
            ),
        },

        "next_step": (
            "STEP 17-21-C-9-2-9B: "
            "응답 CRS/geometry 확정 후 "
            "Parcel Polygon 실제 intersection"
        ),
    }

    save_json(
        result
    )

    # ========================================================
    # 최종 출력
    # ========================================================

    print_section(
        "3. 최종 probe 상태"
    )

    print(
        "query_status:",
        query_status,
    )

    print(
        "resolution:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
    )

    print(
        "CRS check:",
        crs_check.get(
            "status"
        ),
    )

    print(
        "reason:",
        reason,
    )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )