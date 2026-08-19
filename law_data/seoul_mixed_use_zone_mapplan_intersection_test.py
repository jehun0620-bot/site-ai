import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-8A "
    "복합용도구역 UQQ904 MapPlan 실제 공간교차 검증"
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

URBAN_INNOVATION_PATH = (
    OUTPUT_DIR / "seoul_urban_innovation_zone_mapplan_intersection.json"
)

VERTICAL_MIXED_USE_A6_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_mapplan_live.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "seoul_mixed_use_zone_mapplan_intersection.json"
)


# ============================================================
# 대상 조건
# ============================================================

TARGET_NAME = "복합용도구역"
TARGET_CODE = "UQQ904"
TARGET_LAYER = "AC"

# 동일 MapPlan AC layer의 양성대조
POSITIVE_CONTROL_CODE = "UQQ300"


# ============================================================
# 토지이음
# ============================================================

EUM_MAP_URL = "https://www.eum.go.kr/web/mp/mpMapDet.jsp"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


# ============================================================
# 공통 함수
# ============================================================

def print_section(title):
    print()
    print("=" * 70)
    print(f"=== {title} ===")
    print("=" * 70)


def safe_load_json(path):
    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return None


def save_json(data):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def normalize_text(value):
    if value is None:
        return ""

    return str(value).strip()


def get_first_value(data, paths):
    """
    여러 JSON path 후보 중 첫 번째 유효값 반환
    """

    for path in paths:

        current = data

        try:
            for key in path:
                if isinstance(
                    key,
                    int
                ):
                    current = current[key]
                else:
                    current = current[key]

            if current not in (
                None,
                "",
            ):
                return current

        except (
            KeyError,
            TypeError,
            IndexError,
        ):
            continue

    return None


# ============================================================
# SITE 정보 복원
# ============================================================

def load_site():
    query_context = safe_load_json(
        QUERY_CONTEXT_PATH
    )

    urban_result = safe_load_json(
        URBAN_INNOVATION_PATH
    )

    a6_result = safe_load_json(
        VERTICAL_MIXED_USE_A6_PATH
    )

    sources = [
        query_context,
        urban_result,
        a6_result,
    ]

    site_id = None
    address = None
    pnu = None

    for data in sources:

        if not isinstance(
            data,
            dict
        ):
            continue

        if site_id is None:
            site_id = get_first_value(
                data,
                [
                    ["site", "site_id"],
                    ["site_id"],
                    ["query_context", "site_id"],
                ],
            )

        if address is None:
            address = get_first_value(
                data,
                [
                    ["site", "address"],
                    ["address"],
                    ["query_context", "address"],
                ],
            )

        if pnu is None:
            pnu = get_first_value(
                data,
                [
                    ["site", "pnu"],
                    ["pnu"],
                    ["query_context", "pnu"],
                ],
            )

    site_id = normalize_text(
        site_id
    )

    address = normalize_text(
        address
    )

    pnu = normalize_text(
        pnu
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": pnu,
    }


# ============================================================
# 기존 BBOX 복원
# ============================================================

def load_existing_bbox():
    """
    기존 A-6에서 검증된 EPSG:5179 BBOX를 우선 재사용
    """

    a6 = safe_load_json(
        VERTICAL_MIXED_USE_A6_PATH
    )

    if isinstance(
        a6,
        dict
    ):

        bbox = (
            a6
            .get(
                "parcel_bbox",
                {},
            )
            .get(
                "search_epsg5179"
            )
        )

        if (
            isinstance(
                bbox,
                list,
            )
            and len(
                bbox
            ) == 4
        ):
            return [
                float(
                    x
                )
                for x in bbox
            ]

    # 도시혁신구역 결과에도 저장했을 가능성
    urban = safe_load_json(
        URBAN_INNOVATION_PATH
    )

    if isinstance(
        urban,
        dict
    ):

        candidates = [
            urban.get(
                "parcel_bbox_epsg5179"
            ),
            urban.get(
                "search_bbox_epsg5179"
            ),
            urban.get(
                "bbox_epsg5179"
            ),
        ]

        for bbox in candidates:

            if (
                isinstance(
                    bbox,
                    list,
                )
                and len(
                    bbox
                ) == 4
            ):
                return [
                    float(
                        x
                    )
                    for x in bbox
                ]

    return None


# ============================================================
# EUM Session 초기화
# ============================================================

def initialize_eum_session(
    pnu
):
    session = requests.Session()

    session.headers.update(
        DEFAULT_HEADERS
    )

    params = {
        "add": "land",
        "pnu": pnu,
    }

    response = session.get(
        EUM_MAP_URL,
        params=params,
        timeout=30,
    )

    return (
        session,
        response,
    )


# ============================================================
# UQQ904 DOM 검증
# ============================================================

def verify_target_code(
    html
):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    expected_classes = [
        f"typeAC_{TARGET_CODE}",
        f"typeMiniAC_{TARGET_CODE}",
    ]

    matches = []

    for expected_class in expected_classes:

        elements = soup.find_all(
            class_=lambda value:
                value
                and expected_class
                in (
                    value
                    if isinstance(
                        value,
                        list,
                    )
                    else [value]
                )
        )

        for element in elements:

            matches.append(
                {
                    "tag": element.name,
                    "class": (
                        element.get(
                            "class"
                        )
                    ),
                    "title": (
                        element.get(
                            "title"
                        )
                    ),
                    "text": (
                        element.get_text(
                            " ",
                            strip=True,
                        )
                    ),
                }
            )

    direct_verified = False

    for item in matches:

        title = normalize_text(
            item.get(
                "title"
            )
        )

        text = normalize_text(
            item.get(
                "text"
            )
        )

        if (
            TARGET_NAME
            in title
            or TARGET_NAME
            in text
        ):
            direct_verified = True
            break

    return {
        "matches": matches,
        "code_present": (
            TARGET_CODE
            in html
        ),
        "name_present": (
            TARGET_NAME
            in html
        ),
        "direct_verified": (
            direct_verified
        ),
    }


# ============================================================
# MapPlan server 복원
# ============================================================

def extract_mapplan_server(
    html
):
    """
    실제 setinitData(..., gisServer, ...)
    호출에서 MapPlan server 복원
    """

    patterns = [
        r"setinitData\s*\((.*?)\)",
        r"\$\.fn\.setinitData\s*\((.*?)\)",
    ]

    calls = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            html,
            flags=re.S,
        ):

            raw = match.group(
                1
            )

            calls.append(
                raw
            )

    servers = []

    for raw in calls:

        found = re.findall(
            r"""['"](
                https://www\.eum\.ne\.kr:
                \d+
                /MapPlan
            )['"]""",
            raw,
            flags=(
                re.X
                | re.I
            ),
        )

        for server in found:

            if (
                server
                not in servers
            ):
                servers.append(
                    server
                )

    return {
        "calls": calls,
        "servers": servers,
    }


# ============================================================
# MapPlan version 복원
# ============================================================

def extract_versions(
    html
):
    versions = re.findall(
        r"\b20\d{6}\b",
        html,
    )

    unique = []

    for version in versions:

        if (
            version
            not in unique
        ):
            unique.append(
                version
            )

    unique.sort(
        reverse=True
    )

    return unique


# ============================================================
# MapPlan endpoint
# ============================================================

def normalize_mapplan_endpoint(
    server
):
    server = (
        server
        .rstrip(
            "/"
        )
    )

    if server.endswith(
        "/MapPlan/MapPlan"
    ):
        return server

    if server.endswith(
        "/MapPlan"
    ):
        return (
            server
            + "/MapPlan"
        )

    return (
        server
        + "/MapPlan"
    )


# ============================================================
# HTTP JSON 요청
# ============================================================

def request_json(
    session,
    url,
    params,
):
    try:

        response = session.get(
            url,
            params=params,
            timeout=30,
            headers={
                **DEFAULT_HEADERS,
                "Accept": (
                    "application/json,"
                    "text/javascript,"
                    "*/*;q=0.01"
                ),
                "Referer": EUM_MAP_URL,
                "X-Requested-With": (
                    "XMLHttpRequest"
                ),
            },
        )

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
        )

        try:
            payload = (
                response.json()
            )

            is_json = True

        except Exception:
            payload = None
            is_json = False

        return {
            "http_status": (
                response.status_code
            ),
            "content_type": (
                content_type
            ),
            "is_json": is_json,
            "payload": payload,
            "text": (
                response.text
            ),
        }

    except Exception as e:

        return {
            "http_status": None,
            "content_type": "",
            "is_json": False,
            "payload": None,
            "text": "",
            "error": str(
                e
            ),
        }


# ============================================================
# req=analysis parsing
# ============================================================

def parse_analysis(
    payload
):
    layers = []

    if not isinstance(
        payload,
        dict,
    ):
        return {
            "layers": [],
            "layer_count": 0,
            "code_count": 0,
        }

    raw_layers = payload.get(
        "layer"
    )

    if not isinstance(
        raw_layers,
        list,
    ):
        return {
            "layers": [],
            "layer_count": 0,
            "code_count": 0,
        }

    code_count = 0

    for raw_layer in raw_layers:

        if not isinstance(
            raw_layer,
            dict,
        ):
            continue

        name = normalize_text(
            raw_layer.get(
                "name"
            )
        ).upper()

        raw_codes = raw_layer.get(
            "codes"
        )

        codes = []

        if isinstance(
            raw_codes,
            list,
        ):

            for raw_code in raw_codes:

                if not isinstance(
                    raw_code,
                    dict,
                ):
                    continue

                code = normalize_text(
                    raw_code.get(
                        "code"
                    )
                ).upper()

                area = raw_code.get(
                    "area"
                )

                try:
                    area = float(
                        area
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    area = 0.0

                codes.append(
                    {
                        "code": code,
                        "area": area,
                    }
                )

                code_count += 1

        layers.append(
            {
                "name": name,
                "codes": codes,
            }
        )

    return {
        "layers": layers,
        "layer_count": len(
            layers
        ),
        "code_count": code_count,
    }


def find_analysis_code(
    analysis,
    layer_name,
    target_code,
):
    layer_name = (
        layer_name.upper()
    )

    target_code = (
        target_code.upper()
    )

    hits = []

    for layer in analysis.get(
        "layers",
        [],
    ):

        if (
            layer.get(
                "name"
            )
            != layer_name
        ):
            continue

        for item in layer.get(
            "codes",
            [],
        ):

            if (
                item.get(
                    "code"
                )
                == target_code
            ):

                hits.append(
                    item
                )

    total_area = sum(
        item.get(
            "area",
            0.0,
        )
        for item in hits
    )

    return {
        "found": (
            len(
                hits
            )
            > 0
        ),
        "count": len(
            hits
        ),
        "area": (
            total_area
        ),
        "hits": hits,
    }


# ============================================================
# GeoJSON parsing
# ============================================================

def parse_geojson(
    payload
):
    result = {
        "valid": False,
        "feature_count": 0,
        "geometry_types": [],
        "geometries": [],
    }

    if not isinstance(
        payload,
        dict,
    ):
        return result

    if (
        payload.get(
            "type"
        )
        != "FeatureCollection"
    ):
        return result

    features = payload.get(
        "features"
    )

    if not isinstance(
        features,
        list,
    ):
        return result

    result["valid"] = True
    result["feature_count"] = len(
        features
    )

    geometry_types = []
    geometries = []

    for feature in features:

        if not isinstance(
            feature,
            dict,
        ):
            continue

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            continue

        try:

            geom = shape(
                geometry
            )

            if (
                geom.is_empty
            ):
                continue

            geometry_types.append(
                geom.geom_type
            )

            geometries.append(
                geom
            )

        except Exception:
            continue

    result["geometry_types"] = sorted(
        set(
            geometry_types
        )
    )

    result["geometries"] = (
        geometries
    )

    return result


# ============================================================
# Polygon 교차
# ============================================================

def calculate_intersection(
    parcel_geometries,
    target_geometries,
):
    if not parcel_geometries:

        return {
            "parcel_area": 0.0,
            "target_area": 0.0,
            "intersection_area": 0.0,
            "intersection_ratio": 0.0,
            "has_area_intersection": False,
        }

    parcel_geom = unary_union(
        parcel_geometries
    )

    parcel_area = (
        parcel_geom.area
        if not parcel_geom.is_empty
        else 0.0
    )

    # 중요:
    # 대상 feature 0건이어도 parcel_area는 정상 기록
    if not target_geometries:

        return {
            "parcel_area": (
                float(
                    parcel_area
                )
            ),
            "target_area": 0.0,
            "intersection_area": 0.0,
            "intersection_ratio": 0.0,
            "has_area_intersection": False,
        }

    target_geom = unary_union(
        target_geometries
    )

    target_area = (
        target_geom.area
        if not target_geom.is_empty
        else 0.0
    )

    intersection = (
        parcel_geom
        .intersection(
            target_geom
        )
    )

    intersection_area = (
        intersection.area
        if not intersection.is_empty
        else 0.0
    )

    ratio = (
        intersection_area
        / parcel_area
        if parcel_area > 0
        else 0.0
    )

    return {
        "parcel_area": (
            float(
                parcel_area
            )
        ),
        "target_area": (
            float(
                target_area
            )
        ),
        "intersection_area": (
            float(
                intersection_area
            )
        ),
        "intersection_ratio": (
            float(
                ratio
            )
        ),
        "has_area_intersection": (
            intersection_area > 0
        ),
    }


# ============================================================
# Main
# ============================================================

def main():

    print(
        f"=== {STEP_NAME} ==="
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    site = load_site()

    site_id = site[
        "site_id"
    ]

    address = site[
        "address"
    ]

    pnu = site[
        "pnu"
    ]

    print_section(
        "대상 SITE"
    )

    print(
        f"SITE ID: {site_id or '-'}"
    )

    print(
        f"주소: {address or '-'}"
    )

    print(
        f"PNU: {pnu or '-'}"
    )

    if (
        len(
            pnu
        )
        != 19
        or not pnu.isdigit()
    ):
        raise RuntimeError(
            "PNU 19자리 검증 실패"
        )

    # --------------------------------------------------------
    # EUM 초기화
    # --------------------------------------------------------

    print_section(
        "1. 토지이음 지도 Session 초기화"
    )

    session, map_response = (
        initialize_eum_session(
            pnu
        )
    )

    print(
        f"HTTP: {map_response.status_code}"
    )

    print(
        "Content-Type: "
        f"{map_response.headers.get('Content-Type')}"
    )

    print(
        f"HTML length: {len(map_response.text)}"
    )

    html = map_response.text

    # --------------------------------------------------------
    # UQQ904 검증
    # --------------------------------------------------------

    print_section(
        "2. 복합용도구역 UQQ904 공식 코드 검증"
    )

    target_verify = (
        verify_target_code(
            html
        )
    )

    print(
        f"{TARGET_NAME} 존재: "
        f"{target_verify['name_present']}"
    )

    print(
        f"{TARGET_CODE} 존재: "
        f"{target_verify['code_present']}"
    )

    print(
        "명칭/코드 직접 연결: "
        f"{target_verify['direct_verified']}"
    )

    for index, item in enumerate(
        target_verify[
            "matches"
        ],
        start=1,
    ):

        print()
        print(
            f"Element {index}"
        )

        print(
            f"tag: {item['tag']}"
        )

        print(
            f"class: {item['class']}"
        )

        print(
            f"title: {item['title']}"
        )

        print(
            f"text: {item['text']}"
        )

    # --------------------------------------------------------
    # MapPlan server/version
    # --------------------------------------------------------

    print_section(
        "3. MapPlan Server / version 복원"
    )

    server_info = (
        extract_mapplan_server(
            html
        )
    )

    servers = server_info[
        "servers"
    ]

    versions = (
        extract_versions(
            html
        )
    )

    print(
        f"gisServer 후보 수: {len(servers)}"
    )

    for server in servers:
        print(
            f"- {server}"
        )

    print(
        f"version 후보 수: {len(versions)}"
    )

    for version in versions[:10]:
        print(
            f"- {version}"
        )

    if not servers:

        raise RuntimeError(
            "MapPlan gisServer 복원 실패"
        )

    if not versions:

        raise RuntimeError(
            "MapPlan version 복원 실패"
        )

    server = servers[0]

    endpoint = (
        normalize_mapplan_endpoint(
            server
        )
    )

    version = versions[0]

    print(
        f"선택 server: {server}"
    )

    print(
        f"MapPlan endpoint: {endpoint}"
    )

    print(
        f"선택 version: {version}"
    )

    # --------------------------------------------------------
    # BBOX
    # --------------------------------------------------------

    print_section(
        "4. Parcel 검색 BBOX 복원"
    )

    bbox = load_existing_bbox()

    print(
        f"기존 EPSG:5179 BBOX 존재: "
        f"{bbox is not None}"
    )

    if bbox is None:
        raise RuntimeError(
            "기존 EPSG:5179 Parcel BBOX 복원 실패"
        )

    mbr = ",".join(
        str(
            value
        )
        for value in bbox
    )

    print(
        f"EPSG:5179 BBOX: {bbox}"
    )

    print(
        f"MapPlan mbr: {mbr}"
    )

    # --------------------------------------------------------
    # req=analysis
    # --------------------------------------------------------

    print_section(
        "5. PNU req=analysis"
    )

    analysis_response = request_json(
        session=session,
        url=endpoint,
        params={
            "req": "analysis",
            "version": version,
            "pnus": pnu,
        },
    )

    print(
        "HTTP: "
        f"{analysis_response['http_status']}"
    )

    print(
        "Content-Type: "
        f"{analysis_response['content_type']}"
    )

    print(
        "JSON 정상: "
        f"{analysis_response['is_json']}"
    )

    analysis = parse_analysis(
        analysis_response[
            "payload"
        ]
    )

    print(
        f"analysis layer 수: "
        f"{analysis['layer_count']}"
    )

    print(
        f"analysis code 수: "
        f"{analysis['code_count']}"
    )

    print()
    print(
        "[Layer]"
    )

    for layer in analysis[
        "layers"
    ]:
        print(
            f"- {layer['name']}"
        )

    positive_control = (
        find_analysis_code(
            analysis,
            TARGET_LAYER,
            POSITIVE_CONTROL_CODE,
        )
    )

    target_analysis = (
        find_analysis_code(
            analysis,
            TARGET_LAYER,
            TARGET_CODE,
        )
    )

    print()
    print(
        f"[양성대조 {POSITIVE_CONTROL_CODE}]"
    )

    print(
        f"layer: {TARGET_LAYER}"
    )

    print(
        f"found: {positive_control['found']}"
    )

    print(
        f"count: {positive_control['count']}"
    )

    print(
        f"area: {positive_control['area']}"
    )

    print()
    print(
        f"[대상 {TARGET_CODE}]"
    )

    print(
        f"layer: {TARGET_LAYER}"
    )

    print(
        f"found: {target_analysis['found']}"
    )

    print(
        f"count: {target_analysis['count']}"
    )

    print(
        f"area: {target_analysis['area']}"
    )

    # --------------------------------------------------------
    # Parcel Geometry
    # --------------------------------------------------------

    print_section(
        "6. Parcel Polygon MapPlan 조회"
    )

    parcel_response = request_json(
        session=session,
        url=endpoint,
        params={
            "req": "search",
            "version": version,
            "layer": "FA",
            "code": pnu,
        },
    )

    parcel_geo = parse_geojson(
        parcel_response[
            "payload"
        ]
    )

    print(
        f"HTTP: {parcel_response['http_status']}"
    )

    print(
        f"GeoJSON: {parcel_geo['valid']}"
    )

    print(
        f"Feature 수: {parcel_geo['feature_count']}"
    )

    print(
        "geometry type: "
        f"{parcel_geo['geometry_types']}"
    )

    if parcel_geo[
        "geometries"
    ]:

        parcel_union = (
            unary_union(
                parcel_geo[
                    "geometries"
                ]
            )
        )

        print()
        print(
            "Parcel geometry: "
            f"{parcel_union.geom_type}"
        )

        print(
            f"Parcel area: {parcel_union.area}"
        )

        print(
            f"Parcel bounds: {parcel_union.bounds}"
        )

    # --------------------------------------------------------
    # UQQ904 Geometry
    # --------------------------------------------------------

    print_section(
        "7. UQQ904 복합용도구역 Geometry 조회"
    )

    target_response = request_json(
        session=session,
        url=endpoint,
        params={
            "req": "search",
            "version": version,
            "layer": TARGET_LAYER,
            "mbr": mbr,
            "code": TARGET_CODE,
        },
    )

    target_geo = parse_geojson(
        target_response[
            "payload"
        ]
    )

    print(
        f"HTTP: {target_response['http_status']}"
    )

    print(
        f"GeoJSON: {target_geo['valid']}"
    )

    print(
        f"Feature 수: {target_geo['feature_count']}"
    )

    print(
        "geometry type: "
        f"{target_geo['geometry_types']}"
    )

    if target_geo[
        "feature_count"
    ] == 0:

        print()
        print(
            f"{TARGET_CODE} geometry: 없음"
        )

    # --------------------------------------------------------
    # Intersection
    # --------------------------------------------------------

    print_section(
        "8. Parcel × 복합용도구역 공간교차"
    )

    intersection = (
        calculate_intersection(
            parcel_geo[
                "geometries"
            ],
            target_geo[
                "geometries"
            ],
        )
    )

    print(
        f"Parcel 면적: "
        f"{intersection['parcel_area']}"
    )

    print(
        f"조회된 UQQ904 면적: "
        f"{intersection['target_area']}"
    )

    print(
        f"실제 교차 면적: "
        f"{intersection['intersection_area']}"
    )

    print(
        f"필지 교차 비율: "
        f"{intersection['intersection_ratio']}"
    )

    print(
        "면적 교차 존재: "
        f"{intersection['has_area_intersection']}"
    )

    # --------------------------------------------------------
    # 최종 판정
    # --------------------------------------------------------

    print_section(
        "9. 복합용도구역 최종 판정"
    )

    analysis_ok = (
        analysis_response[
            "http_status"
        ]
        == 200
        and analysis_response[
            "is_json"
        ]
        and analysis[
            "layer_count"
        ]
        > 0
    )

    positive_control_ok = (
        positive_control[
            "found"
        ]
    )

    parcel_ok = (
        parcel_response[
            "http_status"
        ]
        == 200
        and parcel_geo[
            "valid"
        ]
        and parcel_geo[
            "feature_count"
        ]
        > 0
        and len(
            parcel_geo[
                "geometries"
            ]
        )
        > 0
    )

    target_search_ok = (
        target_response[
            "http_status"
        ]
        == 200
        and target_geo[
            "valid"
        ]
    )

    has_intersection = (
        intersection[
            "has_area_intersection"
        ]
    )

    if (
        parcel_ok
        and target_search_ok
        and has_intersection
    ):

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = "TRUE"

        confidence = "HIGH"

        evidence_state = (
            "TARGET_AREA_INTERSECTION_CONFIRMED"
        )

        reason = (
            "토지이음 MapPlan에서 복합용도구역 "
            "UQQ904 geometry를 정상 조회하고 "
            "대상 PNU Parcel Polygon과 실제 면적 "
            "교차를 확인하여 복합용도구역으로 판정함"
        )

    elif (
        analysis_ok
        and positive_control_ok
        and not target_analysis[
            "found"
        ]
        and parcel_ok
        and target_search_ok
        and not has_intersection
    ):

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = "FALSE"

        confidence = "HIGH"

        evidence_state = (
            "POSITIVE_CONTROL_VALID_"
            "TARGET_ANALYSIS_NEGATIVE_"
            "NO_AREA_INTERSECTION"
        )

        reason = (
            "동일 MapPlan req=analysis 체계에서 "
            f"AC 계열 양성대조 {POSITIVE_CONTROL_CODE}이 "
            "정상 검출되어 요청 의미가 유효함을 확인했고, "
            f"대상 PNU에서 {TARGET_CODE}은 analysis에 "
            "검출되지 않았으며 UQQ904 geometry 정상조회 "
            "결과에서도 대상 Parcel과 실제 면적 교차가 "
            "확인되지 않아 복합용도구역이 아닌 것으로 판정함"
        )

    else:

        query_status = (
            "QUERY_FAILED"
            if (
                not analysis_ok
                or not parcel_ok
                or not target_search_ok
            )
            else "QUERY_SUCCESS"
        )

        resolution = "UNKNOWN"

        confidence = (
            "NONE"
            if query_status
            == "QUERY_FAILED"
            else "LOW"
        )

        evidence_state = (
            "INSUFFICIENT_EVIDENCE"
        )

        reason = (
            "복합용도구역 UQQ904 판정을 위한 "
            "MapPlan evidence 중 일부가 충족되지 않아 "
            "TRUE/FALSE를 확정하지 않고 UNKNOWN으로 유지함"
        )

    print(
        f"query_status: {query_status}"
    )

    print(
        f"resolution: {resolution}"
    )

    print(
        f"confidence: {confidence}"
    )

    print(
        f"evidence_state: {evidence_state}"
    )

    print(
        f"reason: {reason}"
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validation = {
        "SITE ID 존재": bool(
            site_id
        ),
        "SITE 주소 존재": bool(
            address
        ),
        "PNU 19자리": (
            len(
                pnu
            )
            == 19
            and pnu.isdigit()
        ),
        "토지이음 지도 초기화": (
            map_response.status_code
            == 200
        ),
        "복합용도구역 명칭 확인": (
            target_verify[
                "name_present"
            ]
        ),
        "UQQ904 코드 확인": (
            target_verify[
                "code_present"
            ]
        ),
        "복합용도구역 UQQ904 직접 연결": (
            target_verify[
                "direct_verified"
            ]
        ),
        "MapPlan server 복원": bool(
            servers
        ),
        "MapPlan version 복원": bool(
            versions
        ),
        "EPSG:5179 BBOX 존재": (
            bbox is not None
        ),
        "MapPlan analysis 실행": (
            analysis_response[
                "http_status"
            ]
            is not None
        ),
        "UQQ300 양성대조 검사": (
            positive_control_ok
        ),
        "UQQ904 analysis 검사": True,
        "Parcel Geometry 요청 실행": (
            parcel_response[
                "http_status"
            ]
            is not None
        ),
        "UQQ904 Geometry 요청 실행": (
            target_response[
                "http_status"
            ]
            is not None
        ),
        "Polygon intersection 실행": True,
        "TRUE는 실제 면적교차 필요": (
            resolution != "TRUE"
            or has_intersection
        ),
        "FALSE는 양성대조 필요": (
            resolution != "FALSE"
            or positive_control_ok
        ),
        "FALSE는 UQQ904 analysis 음성 필요": (
            resolution != "FALSE"
            or not target_analysis[
                "found"
            ]
        ),
        "FALSE는 실제 교차 없음 필요": (
            resolution != "FALSE"
            or not has_intersection
        ),
        "HTTP 403을 FALSE 근거로 사용 안 함": (
            resolution != "FALSE"
            or (
                analysis_response[
                    "http_status"
                ]
                == 200
                and target_response[
                    "http_status"
                ]
                == 200
            )
        ),
        "query_status 허용값": (
            query_status
            in {
                "QUERY_SUCCESS",
                "QUERY_FAILED",
                "NOT_QUERIED",
                "NOT_CONNECTED",
            }
        ),
        "resolution 허용값": (
            resolution
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            }
        ),
        "confidence 허용값": (
            confidence
            in {
                "HIGH",
                "MEDIUM",
                "LOW",
                "NONE",
            }
        ),
    }

    print_section(
        "C-9-2-8A 검증"
    )

    for key, value in validation.items():

        print(
            f"{key}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,
        "site": site,
        "target": {
            "name": TARGET_NAME,
            "code": TARGET_CODE,
            "layer": TARGET_LAYER,
        },
        "source_verification": (
            target_verify
        ),
        "mapplan": {
            "server": server,
            "endpoint": endpoint,
            "version": version,
        },
        "parcel_bbox_epsg5179": bbox,
        "mapplan_analysis": {
            "http_status": (
                analysis_response[
                    "http_status"
                ]
            ),
            "content_type": (
                analysis_response[
                    "content_type"
                ]
            ),
            "is_json": (
                analysis_response[
                    "is_json"
                ]
            ),
            "analysis": analysis,
            "positive_control": (
                positive_control
            ),
            "target": (
                target_analysis
            ),
        },
        "parcel_geometry": {
            "http_status": (
                parcel_response[
                    "http_status"
                ]
            ),
            "geojson_valid": (
                parcel_geo[
                    "valid"
                ]
            ),
            "feature_count": (
                parcel_geo[
                    "feature_count"
                ]
            ),
            "geometry_types": (
                parcel_geo[
                    "geometry_types"
                ]
            ),
        },
        "target_geometry": {
            "http_status": (
                target_response[
                    "http_status"
                ]
            ),
            "geojson_valid": (
                target_geo[
                    "valid"
                ]
            ),
            "feature_count": (
                target_geo[
                    "feature_count"
                ]
            ),
            "geometry_types": (
                target_geo[
                    "geometry_types"
                ]
            ),
        },
        "intersection": intersection,
        "site_resolution": {
            "query_status": (
                query_status
            ),
            "resolution": resolution,
            "confidence": confidence,
            "evidence_state": (
                evidence_state
            ),
            "reason": reason,
        },
        "validation": validation,
    }

    save_json(
        output
    )

    print_section(
        "결과 저장"
    )

    print(
        OUTPUT_PATH
    )

    print()
    print(
        "STEP 17-21-C-9-2-8A 완료"
    )

    print()
    print(
        "복합용도구역 최종 판정:"
    )

    print(
        resolution
    )

    if resolution == "TRUE":

        print()
        print(
            "UQQ904와 대상 Parcel의 "
            "실제 면적교차가 확인되었습니다."
        )

    elif resolution == "FALSE":

        print()
        print(
            "MapPlan 양성대조 정상, "
            "UQQ904 analysis 음성, "
            "Parcel과 UQQ904 면적교차 없음이 "
            "확인되었습니다."
        )

    else:

        print()
        print(
            "현재 evidence만으로 "
            "TRUE/FALSE를 확정하지 않습니다."
        )

    print()
    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-9-2-9"
    )

    print(
        "→ 다음 미해결 공간조건으로 진행"
    )


if __name__ == "__main__":
    main()