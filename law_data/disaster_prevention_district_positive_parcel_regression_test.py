# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-C
Disaster Prevention District Positive Parcel Regression

목표
======================================================================
C-16-7-B에서 발견한 현재 VWorld 방재지구 positive feature:

    LT_C_UQ125.22

내부 representative point를 기준으로:

1. VWorld Address API 역지오코딩
2. 지번주소 확보
3. VWorld Search API(parcel)로 PNU 확보
4. LP_PA_CBND_BUBUN Parcel Polygon 확보
5. PNU 직접 검증
6. LT_C_UQ125 query
7. Parcel Polygon ↔ 방재지구 geometry intersection

까지 검증한다.

중요
======================================================================
POINT가 방재지구 안에 있다는 것만으로 SITE TRUE를 확정하지 않는다.

반드시:

    현재 PNU Parcel Polygon
    +
    LT_C_UQ125 geometry
    +
    실제 intersects

를 확인한다.

안전 원칙
======================================================================
- reverse geocoding 성공 ≠ PNU 확보 성공
- Address API에 PNU가 없으면 지번주소를 Search API에 재조회
- Search API의 exact parcel address match를 우선
- PNU 직접 검증 전 Parcel geometry 사용 금지
- 방재지구 spatial TRUE ≠ clause 189 numeric 특례 자동 적용
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from dotenv import load_dotenv

from law_data.parcel_geometry_provider import (
    resolve_live_parcel_geometry,
)

from law_data.spatial_condition_evaluator import (
    compute_intersections,
    geometry_to_shape,
    query_spatial_dataset,
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


# ============================================================
# CONFIG
# ============================================================

VWORLD_ADDRESS_URL = (
    "https://api.vworld.kr/req/address"
)

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

DATASET = (
    "LT_C_UQ125"
)

EXPECTED_FEATURE_ID = (
    "LT_C_UQ125.22"
)

REPRESENTATIVE_X = (
    126.37369914302997
)

REPRESENTATIVE_Y = (
    34.801980483931146
)

REQUEST_TIMEOUT = 30


# ============================================================
# ENV
# ============================================================

load_dotenv(
    BASE_DIR
    / ".env"
)

API_KEY = (
    os.getenv(
        "VWORLD_API_KEY"
    )
    or os.getenv(
        "VWORLD_KEY"
    )
    or ""
).strip()


if not API_KEY:

    raise RuntimeError(
        "VWORLD API key not found"
    )


# ============================================================
# UTIL
# ============================================================

def safe_dict(
    value: Any,
) -> Dict[str, Any]:

    if isinstance(
        value,
        dict,
    ):

        return value

    return {}


def safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(
        value,
        list,
    ):

        return value

    return []


def normalize_address(
    value: Any,
) -> str:

    return (
        str(
            value
            or ""
        )
        .replace(
            "번지",
            "",
        )
        .strip()
    )


# ============================================================
# Address API result parsing
# ============================================================

def collect_address_results(
    response_obj: Dict[str, Any],
) -> List[Dict[str, Any]]:

    """
    VWorld Address API result 구조를 방어적으로 처리한다.

    가능한 형태:
    - result = [ {...}, {...} ]
    - result = {"items": [...]}
    - result = {...} 단일 결과
    """

    raw_result = (
        response_obj.get(
            "result"
        )
    )

    print(
        "Reverse address raw result:",
        raw_result,
    )

    results: List[
        Dict[str, Any]
    ] = []

    # --------------------------------------------------------
    # result 자체가 list
    # --------------------------------------------------------

    if isinstance(
        raw_result,
        list,
    ):

        for item in raw_result:

            if isinstance(
                item,
                dict,
            ):

                results.append(
                    item
                )

        return results

    # --------------------------------------------------------
    # result가 dict
    # --------------------------------------------------------

    if isinstance(
        raw_result,
        dict,
    ):

        raw_items = (
            raw_result.get(
                "items"
            )
        )

        if isinstance(
            raw_items,
            list,
        ):

            for item in raw_items:

                if isinstance(
                    item,
                    dict,
                ):

                    results.append(
                        item
                    )

            return results

        # ----------------------------------------------------
        # 단일 result object
        # ----------------------------------------------------

        if raw_result:

            results.append(
                raw_result
            )

    return results


# ============================================================
# Extract address / possible PNU
# ============================================================

def extract_address_identity(
    item: Dict[str, Any],
) -> Tuple[
    Optional[str],
    Optional[str],
]:

    """
    Address API result에서 가능한 PNU와 지번주소를 추출한다.

    PNU가 없더라도 address를 반환하여 Search API fallback에 사용한다.
    """

    address_obj = safe_dict(
        item.get(
            "address"
        )
    )

    structure = safe_dict(
        item.get(
            "structure"
        )
    )

    refined = safe_dict(
        item.get(
            "refined"
        )
    )

    simple = safe_dict(
        item.get(
            "simple"
        )
    )

    pnu = (
        str(
            item.get(
                "id"
            )
            or item.get(
                "pnu"
            )
            or structure.get(
                "pnu"
            )
            or refined.get(
                "pnu"
            )
            or simple.get(
                "pnu"
            )
            or ""
        ).strip()
        or None
    )

    parcel_address = (
        str(
            address_obj.get(
                "parcel"
            )
            or item.get(
                "text"
            )
            or refined.get(
                "text"
            )
            or simple.get(
                "text"
            )
            or ""
        ).strip()
        or None
    )

    return (
        pnu,
        parcel_address,
    )


# ============================================================
# Coordinate → address
# ============================================================

def reverse_search_parcel(
    *,
    x: float,
    y: float,
) -> Tuple[
    Optional[str],
    Optional[str],
]:

    """
    VWorld Address API를 이용하여 EPSG:4326 좌표가 속한
    지번주소를 역조회한다.

    Address API에 PNU가 있으면 함께 반환한다.
    없으면 후속 Search API에서 PNU를 확보한다.
    """

    params = {

        "service":
            "address",

        "request":
            "getAddress",

        "version":
            "2.0",

        "crs":
            "EPSG:4326",

        "point":
            f"{x},{y}",

        "format":
            "json",

        "type":
            "parcel",

        "zipcode":
            "true",

        "simple":
            "false",

        "key":
            API_KEY,
    }

    try:

        response = requests.get(
            VWORLD_ADDRESS_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:

        print(
            "Reverse address transport error:",
            repr(
                exc
            ),
        )

        return (
            None,
            None,
        )

    print(
        "Reverse address HTTP:",
        response.status_code,
    )

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        print(
            "Reverse address JSON error:",
            repr(
                exc
            ),
        )

        return (
            None,
            None,
        )

    response_obj = safe_dict(
        payload.get(
            "response"
        )
    )

    status = (
        response_obj.get(
            "status"
        )
    )

    print(
        "Reverse address status:",
        status,
    )

    if status != "OK":

        print(
            "Reverse address error:",
            safe_dict(
                response_obj.get(
                    "error"
                )
            ),
        )

        return (
            None,
            None,
        )

    items = (
        collect_address_results(
            response_obj
        )
    )

    print(
        "Reverse address item count:",
        len(
            items
        ),
    )

    if not items:

        return (
            None,
            None,
        )

    selected = None

    # --------------------------------------------------------
    # parcel type 결과 우선
    # --------------------------------------------------------

    for item in items:

        item_type = str(
            item.get(
                "type"
            )
            or ""
        ).strip().lower()

        if (
            item_type
            == "parcel"
        ):

            selected = item

            break

    if selected is None:

        selected = items[
            0
        ]

    print(
        "Reverse address raw item:",
        selected,
    )

    pnu, parcel_address = (
        extract_address_identity(
            selected
        )
    )

    print(
        "Reverse-address PNU:",
        pnu,
    )

    print(
        "Reverse-address parcel address:",
        parcel_address,
    )

    return (
        pnu,
        parcel_address,
    )


# ============================================================
# Parcel address → PNU
# ============================================================

def search_parcel_by_address(
    *,
    address: str,
) -> Tuple[
    Optional[str],
    Optional[str],
    Optional[float],
    Optional[float],
]:

    """
    역지오코딩 결과의 지번주소를 VWorld Search API에 넣어
    정확한 PNU를 확보한다.
    """

    address = str(
        address
        or ""
    ).strip()

    if not address:

        return (
            None,
            None,
            None,
            None,
        )

    params = {

        "service":
            "search",

        "request":
            "search",

        "version":
            "2.0",

        "crs":
            "EPSG:4326",

        "size":
            10,

        "page":
            1,

        "query":
            address,

        "type":
            "address",

        "category":
            "parcel",

        "format":
            "json",

        "errorformat":
            "json",

        "key":
            API_KEY,
    }

    try:

        response = requests.get(
            VWORLD_SEARCH_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:

        print(
            "Parcel search transport error:",
            repr(
                exc
            ),
        )

        return (
            None,
            None,
            None,
            None,
        )

    print(
        "Parcel search HTTP:",
        response.status_code,
    )

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        print(
            "Parcel search JSON error:",
            repr(
                exc
            ),
        )

        return (
            None,
            None,
            None,
            None,
        )

    response_obj = safe_dict(
        payload.get(
            "response"
        )
    )

    status = (
        response_obj.get(
            "status"
        )
    )

    print(
        "Parcel search status:",
        status,
    )

    result = safe_dict(
        response_obj.get(
            "result"
        )
    )

    items = safe_list(
        result.get(
            "items"
        )
    )

    print(
        "Parcel search item count:",
        len(
            items
        ),
    )

    if not items:

        return (
            None,
            None,
            None,
            None,
        )

    target_normalized = (
        normalize_address(
            address
        )
    )

    selected = None

    # --------------------------------------------------------
    # exact parcel address 우선
    # --------------------------------------------------------

    for item in items:

        if not isinstance(
            item,
            dict,
        ):

            continue

        address_obj = safe_dict(
            item.get(
                "address"
            )
        )

        candidate_address = (
            address_obj.get(
                "parcel"
            )
        )

        if (
            normalize_address(
                candidate_address
            )
            == target_normalized
        ):

            selected = item

            break

    # --------------------------------------------------------
    # exact match가 없으면 첫 parcel result
    # --------------------------------------------------------

    if selected is None:

        for item in items:

            if isinstance(
                item,
                dict,
            ):

                selected = item

                break

    if not isinstance(
        selected,
        dict,
    ):

        return (
            None,
            None,
            None,
            None,
        )

    print(
        "Parcel search raw item:",
        selected,
    )

    pnu = (
        str(
            selected.get(
                "id"
            )
            or ""
        ).strip()
        or None
    )

    address_obj = safe_dict(
        selected.get(
            "address"
        )
    )

    resolved_address = (
        str(
            address_obj.get(
                "parcel"
            )
            or ""
        ).strip()
        or None
    )

    point = safe_dict(
        selected.get(
            "point"
        )
    )

    try:

        x = float(
            point.get(
                "x"
            )
        )

        y = float(
            point.get(
                "y"
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        x = None
        y = None

    print(
        "Search-resolved PNU:",
        pnu,
    )

    print(
        "Search-resolved parcel address:",
        resolved_address,
    )

    print(
        "Search-resolved coordinate:",
        x,
        y,
    )

    return (
        pnu,
        resolved_address,
        x,
        y,
    )


# ============================================================
# Resolve Parcel identity
# ============================================================

def resolve_parcel_identity(
    *,
    x: float,
    y: float,
) -> Dict[str, Any]:

    """
    1. Coordinate reverse address
    2. PNU가 없으면 parcel address search
    """

    reverse_pnu, reverse_address = (
        reverse_search_parcel(
            x=x,
            y=y,
        )
    )

    # --------------------------------------------------------
    # Address API가 PNU까지 주는 경우
    # --------------------------------------------------------

    if (
        reverse_pnu
        and len(
            reverse_pnu
        )
        == 19
    ):

        return {

            "resolved":
                True,

            "pnu":
                reverse_pnu,

            "address":
                reverse_address,

            "source":
                "VWORLD_ADDRESS_API",

            "search_coordinate":
                None,
        }

    # --------------------------------------------------------
    # PNU 없으면 address → Search API
    # --------------------------------------------------------

    if not reverse_address:

        return {

            "resolved":
                False,

            "pnu":
                None,

            "address":
                None,

            "source":
                "UNRESOLVED",

            "search_coordinate":
                None,
        }

    (
        search_pnu,
        search_address,
        search_x,
        search_y,
    ) = (
        search_parcel_by_address(
            address=reverse_address
        )
    )

    if (
        search_pnu
        and len(
            search_pnu
        )
        == 19
    ):

        return {

            "resolved":
                True,

            "pnu":
                search_pnu,

            "address":
                (
                    search_address
                    or reverse_address
                ),

            "source":
                "VWORLD_ADDRESS_TO_SEARCH",

            "search_coordinate": {

                "x":
                    search_x,

                "y":
                    search_y,

                "crs":
                    "EPSG:4326",
            },
        }

    return {

        "resolved":
            False,

        "pnu":
            search_pnu,

        "address":
            (
                search_address
                or reverse_address
            ),

        "source":
            "VWORLD_ADDRESS_TO_SEARCH_FAILED",

        "search_coordinate":
            None,
    }


# ============================================================
# MAIN
# ============================================================

print(
    "============================================================"
)

print(
    "C-16-7-C DISASTER PREVENTION POSITIVE PARCEL REGRESSION"
)

print(
    "============================================================"
)

print(
    "Representative point:",
    REPRESENTATIVE_X,
    REPRESENTATIVE_Y,
)


# ============================================================
# 1. resolve Parcel identity
# ============================================================

identity = (
    resolve_parcel_identity(
        x=REPRESENTATIVE_X,
        y=REPRESENTATIVE_Y,
    )
)


pnu = (
    identity.get(
        "pnu"
    )
)

address = (
    identity.get(
        "address"
    )
)


print()

print(
    "--- RESOLVED PARCEL IDENTITY ---"
)

print(
    "Resolved:",
    identity.get(
        "resolved"
    ),
)

print(
    "Source:",
    identity.get(
        "source"
    ),
)

print(
    "PNU:",
    pnu,
)

print(
    "Address:",
    address,
)

print(
    "Search coordinate:",
    identity.get(
        "search_coordinate"
    ),
)


if (
    identity.get(
        "resolved"
    )
    is not True
):

    raise AssertionError(
        "Representative point에서 Parcel identity를 확보하지 못했습니다."
    )


if (
    not pnu
    or len(
        str(
            pnu
        )
    )
    != 19
):

    raise AssertionError(
        f"PNU 형식 오류: {pnu}"
    )


# ============================================================
# 2. live Parcel geometry
# ============================================================

parcel_result = (
    resolve_live_parcel_geometry(
        pnu=pnu,
        address=(
            address
            or ""
        ),
    )
)


parcel_source = safe_dict(
    parcel_result.get(
        "source"
    )
)


print()

print(
    "--- PARCEL ---"
)

print(
    "Loaded:",
    parcel_result.get(
        "geometry_loaded"
    ),
)

print(
    "Geometry type:",
    parcel_result.get(
        "geometry_type"
    ),
)

print(
    "Resolution:",
    parcel_result.get(
        "resolution"
    ),
)

print(
    "Feature PNU:",
    parcel_result.get(
        "feature_pnu"
    ),
)

print(
    "Strict PNU verified:",
    parcel_result.get(
        "strict_pnu_verified"
    ),
)

print(
    "Source:",
    parcel_source,
)


parcel_geometry = (
    geometry_to_shape(
        parcel_result.get(
            "geometry"
        )
    )
)


# ============================================================
# 3. query LT_C_UQ125
# ============================================================

district_result = (
    query_spatial_dataset(
        dataset=DATASET,
        api_key=API_KEY,
        x=REPRESENTATIVE_X,
        y=REPRESENTATIVE_Y,
    )
)


print()

print(
    "--- DISASTER PREVENTION DISTRICT QUERY ---"
)

print(
    "HTTP:",
    district_result.get(
        "http_status"
    ),
)

print(
    "VWorld status:",
    district_result.get(
        "vworld_status"
    ),
)

print(
    "Classification:",
    district_result.get(
        "classification"
    ),
)

print(
    "Feature count:",
    district_result.get(
        "feature_count"
    ),
)

print(
    "Geometry feature count:",
    district_result.get(
        "geometry_feature_count"
    ),
)


district_items = (
    district_result.get(
        "features",
        []
    )
)


# ============================================================
# 4. Parcel intersection
# ============================================================

if parcel_geometry is None:

    intersections = []

else:

    intersections = (
        compute_intersections(
            parcel_geometry=parcel_geometry,
            district_items=district_items,
        )
    )


print()

print(
    "--- INTERSECTIONS ---"
)

for item in intersections:

    print(
        item
    )


positive_intersections = [

    item
    for item
    in intersections
    if item.get(
        "intersects"
    )
    is True
]


positive_feature_ids = {

    str(
        item.get(
            "feature_id"
        )
        or ""
    ).strip()

    for item
    in positive_intersections
}


positive_names = {

    str(
        item.get(
            "district_name"
        )
        or ""
    ).strip()

    for item
    in positive_intersections
}


# ============================================================
# VALIDATION
# ============================================================

validations = {

    "identity resolved": (
        identity.get(
            "resolved"
        )
        is True
    ),

    "PNU resolved": (
        bool(
            pnu
        )
    ),

    "PNU length 19": (
        len(
            str(
                pnu
            )
        )
        == 19
    ),

    "parcel address resolved": (
        bool(
            address
        )
    ),

    "parcel loaded": (
        parcel_result.get(
            "geometry_loaded"
        )
        is True
    ),

    "parcel strict PNU verified": (
        parcel_result.get(
            "strict_pnu_verified"
        )
        is True
    ),

    "parcel feature PNU matches": (
        parcel_result.get(
            "feature_pnu"
        )
        == pnu
    ),

    "parcel geometry exists": (
        parcel_geometry
        is not None
    ),

    "district HTTP 200": (
        district_result.get(
            "http_status"
        )
        == 200
    ),

    "district status OK": (
        district_result.get(
            "vworld_status"
        )
        == "OK"
    ),

    "district query success": (
        district_result.get(
            "classification"
        )
        == "QUERY_SUCCESS"
    ),

    "district geometry exists": (
        district_result.get(
            "geometry_feature_count",
            0,
        )
        > 0
    ),

    "parcel intersects district": (
        len(
            positive_intersections
        )
        > 0
    ),

    "expected feature ID": (
        EXPECTED_FEATURE_ID
        in positive_feature_ids
    ),

    "district name": (
        "방재지구"
        in positive_names
    ),
}


print()

print(
    "============================================================"
)

print(
    "VALIDATION"
)

print(
    "============================================================"
)


for name, passed in (
    validations.items()
):

    print(
        f"{name}:",
        passed,
    )


all_pass = all(
    validations.values()
)


print()

print(
    "Positive feature IDs:",
    sorted(
        positive_feature_ids
    ),
)

print(
    "Positive district names:",
    sorted(
        positive_names
    ),
)

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Disaster prevention district positive parcel regression failed"
    )