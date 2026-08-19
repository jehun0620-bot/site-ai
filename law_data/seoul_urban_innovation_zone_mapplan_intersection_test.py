import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

try:
    from shapely.geometry import shape
    from shapely.ops import unary_union
except ImportError:
    raise RuntimeError(
        "shapely가 설치되어 있지 않습니다.\n"
        "pip install shapely"
    )


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-7B "
    "도시혁신구역 UQQ903 MapPlan 실제 공간교차 검증"
)

TARGET_NAME = "도시혁신구역"
TARGET_CODE = "UQQ903"
TARGET_LAYER = "AC"

POSITIVE_CONTROL_CODE = "UQQ300"
POSITIVE_CONTROL_LAYER = "AC"

PARCEL_LAYER = "FA"


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

SOURCE_PROBE_PATH = (
    OUTPUT_DIR
    / "seoul_urban_innovation_zone_source_probe.json"
)

A6_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_mapplan_live.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_urban_innovation_zone_mapplan_intersection.json"
)


# ============================================================
# URL
# ============================================================

EUM_MAP_URL = (
    "https://www.eum.go.kr/web/mp/mpMapDet.jsp"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ============================================================
# PRINT
# ============================================================

def line():
    print("=" * 70)


def subline():
    print("-" * 70)


# ============================================================
# JSON
# ============================================================

def load_json(path: Path):
    if not path.exists():
        return None

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def recursive_find(obj, keys):
    if isinstance(obj, dict):
        for key in keys:
            if key in obj:
                value = obj[key]

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    return value

        for value in obj.values():
            found = recursive_find(
                value,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = recursive_find(
                item,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    return None


# ============================================================
# SITE
# ============================================================

def extract_site(data):
    data = (
        data
        if isinstance(data, dict)
        else {}
    )

    site_id = recursive_find(
        data,
        [
            "site_id",
            "SITE_ID",
        ],
    )

    address = recursive_find(
        data,
        [
            "address",
            "jibun_address",
            "lot_address",
            "SITE_ADDRESS",
        ],
    )

    pnu = recursive_find(
        data,
        [
            "pnu",
            "PNU",
        ],
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": (
            str(pnu)
            if pnu
            else None
        ),
    }


# ============================================================
# STRING / URL NORMALIZE
# ============================================================

def clean_url(value):
    if not value:
        return None

    value = str(value).strip()

    # markdown URL 혹은 과거 출력 문자열 보정
    markdown_match = re.search(
        r"\((https?://[^)]+)\)",
        value,
    )

    if markdown_match:
        value = markdown_match.group(1)

    value = value.strip(
        "\"'<> "
    )

    return value


def normalize_mapplan_url(value):
    """
    setinitData에서 얻는 값:
        https://www.eum.ne.kr:9002/MapPlan

    실제 요청:
        https://www.eum.ne.kr:9002/MapPlan/MapPlan
    """

    value = clean_url(value)

    if not value:
        return None

    value = value.rstrip("/")

    if value.endswith(
        "/MapPlan/MapPlan"
    ):
        return value

    if value.endswith(
        "/MapPlan"
    ):
        return (
            value
            + "/MapPlan"
        )

    return (
        value
        + "/MapPlan"
    )


# ============================================================
# MAP PAGE
# ============================================================

def initialize_eum_session(
    session,
    pnu,
):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8"
        ),
        "Referer": (
            "https://www.eum.go.kr/"
        ),
    }

    response = session.get(
        EUM_MAP_URL,
        params={
            "add": "land",
            "pnu": pnu,
        },
        headers=headers,
        timeout=30,
    )

    response.encoding = (
        response.apparent_encoding
        or "euc-kr"
    )

    return response


# ============================================================
# GIS SERVER
# ============================================================

def extract_gis_server(
    html,
    pnu,
):
    """
    $.fn.setinitData(
        'PNU',
        '',
        '',
        'https://.../MapPlan',
        'PC'
    )
    """

    patterns = [
        (
            r"setinitData\s*\("
            r"\s*['\"]"
            + re.escape(pnu)
            + r"['\"]"
            r"\s*,.*?"
            r"['\"]"
            r"(https?://[^'\"]+)"
            r"['\"]"
            r"\s*,\s*['\"]PC['\"]"
            r"\s*\)"
        ),
        (
            r"setinitData\s*\("
            r".{0,1000}?"
            r"['\"]"
            r"(https?://[^'\"]+/MapPlan)"
            r"['\"]"
            r".{0,200}?"
            r"['\"]PC['\"]"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            html,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        )

        if match:
            return clean_url(
                match.group(1)
            )

    return None


# ============================================================
# VERSION
# ============================================================

def extract_versions(html):
    """
    자료생성시점 select / class 등에서 YYYYMMDD 추출
    """

    versions = re.findall(
        r"\b20\d{6}\b",
        html,
    )

    versions = list(
        dict.fromkeys(
            versions
        )
    )

    versions.sort(
        reverse=True
    )

    return versions


def recover_version_from_a6():
    data = load_json(
        A6_PATH
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    value = (
        data.get(
            "selected_version"
        )
        or recursive_find(
            data,
            [
                "selected_version",
                "version",
            ],
        )
    )

    if value:
        value = str(value)

    if (
        value
        and re.fullmatch(
            r"20\d{6}",
            value,
        )
    ):
        return value

    return None


# ============================================================
# BBOX
# ============================================================

def recover_bbox_from_a6():
    data = load_json(
        A6_PATH
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    bbox = (
        data
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
        and len(bbox) == 4
    ):
        return [
            float(x)
            for x in bbox
        ]

    return None


# ============================================================
# MAPPLAN REQUEST
# ============================================================

def request_mapplan(
    session,
    url,
    params,
    referer_url,
):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "application/json,"
            "text/javascript,"
            "*/*;q=0.8"
        ),
        "Referer": referer_url,
        "Origin": (
            "https://www.eum.go.kr"
        ),
    }

    result = {
        "url": url,
        "params": params,
        "http_status": None,
        "content_type": None,
        "json": None,
        "json_ok": False,
        "preview": None,
        "error": None,
    }

    try:
        response = session.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
        )

    except Exception as exc:
        result["error"] = repr(
            exc
        )

        return result

    result["http_status"] = (
        response.status_code
    )

    result["content_type"] = (
        response.headers.get(
            "Content-Type"
        )
    )

    text = response.text

    result["preview"] = (
        text[:2000]
        if text
        else ""
    )

    if response.status_code != 200:
        return result

    try:
        payload = response.json()

        result["json"] = payload
        result["json_ok"] = True

    except Exception as exc:
        result["error"] = (
            f"JSON parse error: {exc}"
        )

    return result


# ============================================================
# ANALYSIS
# ============================================================

def parse_analysis(payload):
    """
    MapPlan req=analysis:

    {
      "layer": [
        {
          "name": "ac",
          "codes": [
            {
              "code": "UQQ300",
              "area": ...
            }
          ]
        }
      ]
    }
    """

    result = {
        "layer_count": 0,
        "code_count": 0,
        "layers": {},
    }

    if not isinstance(
        payload,
        dict,
    ):
        return result

    layers = (
        payload.get("layer")
        or []
    )

    if not isinstance(
        layers,
        list,
    ):
        return result

    result["layer_count"] = (
        len(layers)
    )

    for layer in layers:
        if not isinstance(
            layer,
            dict,
        ):
            continue

        name = str(
            layer.get("name")
            or ""
        ).upper()

        codes = (
            layer.get("codes")
            or []
        )

        parsed_codes = []

        for item in codes:
            if not isinstance(
                item,
                dict,
            ):
                continue

            code = str(
                item.get("code")
                or ""
            ).upper()

            try:
                area = float(
                    item.get(
                        "area",
                        0,
                    )
                    or 0
                )
            except Exception:
                area = 0.0

            parsed_codes.append(
                {
                    "code": code,
                    "area": area,
                }
            )

            result[
                "code_count"
            ] += 1

        result["layers"][
            name
        ] = parsed_codes

    return result


def find_analysis_code(
    analysis,
    layer_name,
    code,
):
    layer_name = (
        layer_name.upper()
    )

    code = code.upper()

    codes = (
        analysis
        .get(
            "layers",
            {},
        )
        .get(
            layer_name,
            [],
        )
    )

    hits = [
        item
        for item in codes
        if item.get(
            "code"
        ) == code
    ]

    area = sum(
        float(
            item.get(
                "area",
                0,
            )
            or 0
        )
        for item in hits
    )

    return {
        "found": (
            len(hits) > 0
        ),
        "count": len(hits),
        "area": area,
        "hits": hits,
    }


# ============================================================
# GEOJSON
# ============================================================

def parse_geojson(payload):
    result = {
        "valid": False,
        "feature_count": 0,
        "geometry_types": [],
        "features": [],
    }

    if not isinstance(
        payload,
        dict,
    ):
        return result

    if (
        payload.get("type")
        != "FeatureCollection"
    ):
        return result

    features = (
        payload.get("features")
        or []
    )

    if not isinstance(
        features,
        list,
    ):
        return result

    geometry_types = []

    for feature in features:
        if not isinstance(
            feature,
            dict,
        ):
            continue

        geometry = (
            feature.get(
                "geometry"
            )
        )

        if isinstance(
            geometry,
            dict,
        ):
            geometry_type = (
                geometry.get(
                    "type"
                )
            )

            if geometry_type:
                geometry_types.append(
                    geometry_type
                )

    result["valid"] = True
    result["feature_count"] = (
        len(features)
    )

    result["geometry_types"] = (
        sorted(
            set(
                geometry_types
            )
        )
    )

    result["features"] = features

    return result


def shapely_union_from_geojson(
    geojson_result,
):
    geometries = []

    for feature in (
        geojson_result.get(
            "features",
            []
        )
    ):
        geometry = (
            feature.get(
                "geometry"
            )
            if isinstance(
                feature,
                dict,
            )
            else None
        )

        if not geometry:
            continue

        try:
            geom = shape(
                geometry
            )

        except Exception:
            continue

        if geom.is_empty:
            continue

        if not geom.is_valid:
            try:
                geom = (
                    geom.buffer(0)
                )
            except Exception:
                continue

        if not geom.is_empty:
            geometries.append(
                geom
            )

    if not geometries:
        return None

    try:
        return unary_union(
            geometries
        )

    except Exception:
        return None


# ============================================================
# INTERSECTION
# ============================================================

def analyze_intersection(
    parcel_geom,
    target_geom,
):
    result = {
        "parcel_area": 0.0,
        "target_area": 0.0,
        "intersection_area": 0.0,
        "intersection_ratio": 0.0,
        "has_area_intersection": False,
    }

    if (
        parcel_geom is None
        or target_geom is None
    ):
        return result

    try:
        parcel_area = float(
            parcel_geom.area
        )

        target_area = float(
            target_geom.area
        )

        intersection = (
            parcel_geom.intersection(
                target_geom
            )
        )

        intersection_area = float(
            intersection.area
        )

    except Exception:
        return result

    ratio = 0.0

    if parcel_area > 0:
        ratio = (
            intersection_area
            / parcel_area
        )

    result.update(
        {
            "parcel_area":
                parcel_area,

            "target_area":
                target_area,

            "intersection_area":
                intersection_area,

            "intersection_ratio":
                ratio,

            "has_area_intersection":
                intersection_area > 0,
        }
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        f"=== {STEP_NAME} ==="
    )
    print()

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    query_context = load_json(
        QUERY_CONTEXT_PATH
    )

    if not isinstance(
        query_context,
        dict,
    ):
        raise RuntimeError(
            "Query Context를 읽을 수 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    site = extract_site(
        query_context
    )

    line()
    print(
        "=== 대상 SITE ==="
    )
    line()

    print(
        "SITE ID:",
        site["site_id"]
        or "-",
    )

    print(
        "주소:",
        site["address"]
        or "-",
    )

    print(
        "PNU:",
        site["pnu"]
        or "-",
    )

    print()

    pnu = site["pnu"]

    pnu_valid = (
        isinstance(
            pnu,
            str,
        )
        and len(pnu) == 19
        and pnu.isdigit()
    )

    if not pnu_valid:
        raise RuntimeError(
            "PNU 19자리 검증 실패"
        )

    # --------------------------------------------------------
    # SOURCE PROBE
    # --------------------------------------------------------

    line()
    print(
        "=== 1. 7A Source Probe 결과 확인 ==="
    )
    line()

    source_probe = load_json(
        SOURCE_PROBE_PATH
    )

    source_probe_exists = (
        isinstance(
            source_probe,
            dict,
        )
    )

    source_text = (
        json.dumps(
            source_probe,
            ensure_ascii=False,
        )
        if source_probe_exists
        else ""
    )

    source_code_verified = (
        TARGET_CODE
        in source_text
        and TARGET_NAME
        in source_text
    )

    print(
        "7A 파일 존재:",
        source_probe_exists,
    )

    print(
        "도시혁신구역 확인:",
        TARGET_NAME
        in source_text,
    )

    print(
        "UQQ903 확인:",
        TARGET_CODE
        in source_text,
    )

    print(
        "source code verified:",
        source_code_verified,
    )

    print()

    if not source_code_verified:
        raise RuntimeError(
            "7A에서 도시혁신구역/UQQ903 "
            "관리코드 검증이 완료되지 않았습니다."
        )

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    line()
    print(
        "=== 2. 토지이음 지도 Session 초기화 ==="
    )
    line()

    session = requests.Session()

    map_response = (
        initialize_eum_session(
            session,
            pnu,
        )
    )

    print(
        "HTTP:",
        map_response.status_code,
    )

    print(
        "Content-Type:",
        map_response.headers.get(
            "Content-Type"
        ),
    )

    print(
        "HTML length:",
        len(
            map_response.text
        ),
    )

    print()

    map_page_ok = (
        map_response.status_code
        == 200
    )

    html = (
        map_response.text
        if map_page_ok
        else ""
    )

    # --------------------------------------------------------
    # SERVER / VERSION
    # --------------------------------------------------------

    line()
    print(
        "=== 3. MapPlan Server / version 복원 ==="
    )
    line()

    gis_server = extract_gis_server(
        html,
        pnu,
    )

    mapplan_url = (
        normalize_mapplan_url(
            gis_server
        )
    )

    versions = (
        extract_versions(
            html
        )
    )

    a6_version = (
        recover_version_from_a6()
    )

    version = (
        versions[0]
        if versions
        else a6_version
    )

    print(
        "gisServer:",
        gis_server or "-",
    )

    print(
        "MapPlan endpoint:",
        mapplan_url or "-",
    )

    print(
        "HTML version 후보 수:",
        len(versions),
    )

    if versions:
        for value in (
            versions[:10]
        ):
            print(
                "-",
                value,
            )

    print(
        "선택 version:",
        version or "-",
    )

    print()

    # --------------------------------------------------------
    # BBOX
    # --------------------------------------------------------

    line()
    print(
        "=== 4. Parcel 검색 BBOX 복원 ==="
    )
    line()

    bbox = (
        recover_bbox_from_a6()
    )

    print(
        "A-6 BBOX 존재:",
        bool(bbox),
    )

    if bbox:
        print(
            "EPSG:5179 BBOX:",
            bbox,
        )

        mbr = ",".join(
            str(x)
            for x in bbox
        )

        print(
            "MapPlan mbr:",
            mbr,
        )
    else:
        mbr = None

    print()

    # --------------------------------------------------------
    # REQUIRED CHECK
    # --------------------------------------------------------

    if (
        not map_page_ok
        or not mapplan_url
        or not version
        or not mbr
    ):
        final = {
            "query_status":
                "QUERY_FAILED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "MapPlan 요청에 필요한 "
                    "map page/server/version/BBOX 중 "
                    "일부를 복원하지 못해 "
                    "도시혁신구역 공간판정을 수행할 수 없음"
                ),
        }

        result = {
            "step": STEP_NAME,
            "site": site,
            "target": {
                "name": TARGET_NAME,
                "code": TARGET_CODE,
                "layer": TARGET_LAYER,
            },
            "site_resolution": final,
        }

        save_json(
            OUTPUT_PATH,
            result,
        )

        print(
            final
        )

        return

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    line()
    print(
        "=== 5. PNU req=analysis ==="
    )
    line()

    analysis_request = (
        request_mapplan(
            session,
            mapplan_url,
            {
                "req":
                    "analysis",

                "version":
                    version,

                "pnus":
                    pnu,
            },
            map_response.url,
        )
    )

    print(
        "HTTP:",
        analysis_request[
            "http_status"
        ],
    )

    print(
        "Content-Type:",
        analysis_request[
            "content_type"
        ],
    )

    print(
        "JSON 정상:",
        analysis_request[
            "json_ok"
        ],
    )

    if not analysis_request[
        "json_ok"
    ]:
        print(
            "preview:",
            analysis_request[
                "preview"
            ],
        )

    analysis = parse_analysis(
        analysis_request[
            "json"
        ]
    )

    print(
        "analysis layer 수:",
        analysis[
            "layer_count"
        ],
    )

    print(
        "analysis code 수:",
        analysis[
            "code_count"
        ],
    )

    print()

    print(
        "[Layer]"
    )

    for layer_name in sorted(
        analysis[
            "layers"
        ].keys()
    ):
        print(
            "-",
            layer_name,
        )

    print()

    positive = find_analysis_code(
        analysis,
        POSITIVE_CONTROL_LAYER,
        POSITIVE_CONTROL_CODE,
    )

    target_analysis = (
        find_analysis_code(
            analysis,
            TARGET_LAYER,
            TARGET_CODE,
        )
    )

    print(
        "[양성대조 UQQ300]"
    )

    print(
        "layer:",
        POSITIVE_CONTROL_LAYER,
    )

    print(
        "found:",
        positive["found"],
    )

    print(
        "count:",
        positive["count"],
    )

    print(
        "area:",
        positive["area"],
    )

    print()

    print(
        "[대상 UQQ903]"
    )

    print(
        "layer:",
        TARGET_LAYER,
    )

    print(
        "found:",
        target_analysis[
            "found"
        ],
    )

    print(
        "count:",
        target_analysis[
            "count"
        ],
    )

    print(
        "area:",
        target_analysis[
            "area"
        ],
    )

    print()

    # --------------------------------------------------------
    # PARCEL GEOMETRY
    # --------------------------------------------------------

    line()
    print(
        "=== 6. Parcel Polygon MapPlan 조회 ==="
    )
    line()

    parcel_request = (
        request_mapplan(
            session,
            mapplan_url,
            {
                "req":
                    "search",

                "version":
                    version,

                "layer":
                    PARCEL_LAYER,

                "code":
                    pnu,
            },
            map_response.url,
        )
    )

    parcel_geojson = (
        parse_geojson(
            parcel_request[
                "json"
            ]
        )
    )

    print(
        "HTTP:",
        parcel_request[
            "http_status"
        ],
    )

    print(
        "GeoJSON:",
        parcel_geojson[
            "valid"
        ],
    )

    print(
        "Feature 수:",
        parcel_geojson[
            "feature_count"
        ],
    )

    print(
        "geometry type:",
        parcel_geojson[
            "geometry_types"
        ],
    )

    if not parcel_geojson[
        "valid"
    ]:
        print(
            "preview:",
            parcel_request[
                "preview"
            ],
        )

    print()

    parcel_geom = (
        shapely_union_from_geojson(
            parcel_geojson
        )
    )

    if parcel_geom is not None:
        print(
            "Parcel geometry:",
            parcel_geom.geom_type,
        )

        print(
            "Parcel area:",
            parcel_geom.area,
        )

        print(
            "Parcel bounds:",
            parcel_geom.bounds,
        )
    else:
        print(
            "Parcel geometry: 없음"
        )

    print()

    # --------------------------------------------------------
    # TARGET GEOMETRY
    # --------------------------------------------------------

    line()
    print(
        "=== 7. UQQ903 도시혁신구역 Geometry 조회 ==="
    )
    line()

    target_request = (
        request_mapplan(
            session,
            mapplan_url,
            {
                "req":
                    "search",

                "version":
                    version,

                "layer":
                    TARGET_LAYER,

                "mbr":
                    mbr,

                "code":
                    TARGET_CODE,
            },
            map_response.url,
        )
    )

    target_geojson = (
        parse_geojson(
            target_request[
                "json"
            ]
        )
    )

    print(
        "HTTP:",
        target_request[
            "http_status"
        ],
    )

    print(
        "GeoJSON:",
        target_geojson[
            "valid"
        ],
    )

    print(
        "Feature 수:",
        target_geojson[
            "feature_count"
        ],
    )

    print(
        "geometry type:",
        target_geojson[
            "geometry_types"
        ],
    )

    if not target_geojson[
        "valid"
    ]:
        print(
            "preview:",
            target_request[
                "preview"
            ],
        )

    print()

    target_geom = (
        shapely_union_from_geojson(
            target_geojson
        )
    )

    if target_geom is not None:
        print(
            "UQQ903 geometry:",
            target_geom.geom_type,
        )

        print(
            "UQQ903 조회 geometry area:",
            target_geom.area,
        )

        print(
            "UQQ903 bounds:",
            target_geom.bounds,
        )
    else:
        print(
            "UQQ903 geometry: 없음"
        )

    print()

    # --------------------------------------------------------
    # INTERSECTION
    # --------------------------------------------------------

    line()
    print(
        "=== 8. Parcel × 도시혁신구역 공간교차 ==="
    )
    line()

    intersection = (
        analyze_intersection(
            parcel_geom,
            target_geom,
        )
    )

    print(
        "Parcel 면적:",
        intersection[
            "parcel_area"
        ],
    )

    print(
        "조회된 UQQ903 면적:",
        intersection[
            "target_area"
        ],
    )

    print(
        "실제 교차 면적:",
        intersection[
            "intersection_area"
        ],
    )

    print(
        "필지 교차 비율:",
        intersection[
            "intersection_ratio"
        ],
    )

    print(
        "면적 교차 존재:",
        intersection[
            "has_area_intersection"
        ],
    )

    print()

    # --------------------------------------------------------
    # EVIDENCE STATES
    # --------------------------------------------------------

    analysis_http_ok = (
        analysis_request[
            "http_status"
        ]
        == 200
        and analysis_request[
            "json_ok"
        ]
    )

    positive_control_valid = (
        analysis_http_ok
        and positive[
            "found"
        ]
        and positive[
            "area"
        ] > 0
    )

    target_analysis_positive = (
        target_analysis[
            "found"
        ]
        and target_analysis[
            "area"
        ] > 0
    )

    target_analysis_negative = (
        analysis_http_ok
        and not target_analysis[
            "found"
        ]
    )

    parcel_geometry_valid = (
        parcel_request[
            "http_status"
        ]
        == 200
        and parcel_geojson[
            "valid"
        ]
        and parcel_geojson[
            "feature_count"
        ] > 0
        and parcel_geom
        is not None
    )

    target_geometry_request_valid = (
        target_request[
            "http_status"
        ]
        == 200
        and target_geojson[
            "valid"
        ]
    )

    target_geometry_negative = (
        target_geometry_request_valid
        and target_geojson[
            "feature_count"
        ]
        == 0
    )

    target_geometry_positive = (
        target_geometry_request_valid
        and target_geojson[
            "feature_count"
        ]
        > 0
    )

    actual_intersection = (
        intersection[
            "has_area_intersection"
        ]
    )

    # --------------------------------------------------------
    # FINAL RESOLUTION
    # --------------------------------------------------------

    line()
    print(
        "=== 9. 도시혁신구역 최종 판정 ==="
    )
    line()

    if (
        parcel_geometry_valid
        and target_geometry_positive
        and actual_intersection
    ):
        final = {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "TRUE",

            "confidence":
                "HIGH",

            "evidence_state":
                "ACTUAL_POLYGON_INTERSECTION",

            "reason":
                (
                    "토지이음 MapPlan에서 대상 PNU의 "
                    "Parcel Polygon과 도시혁신구역 UQQ903 "
                    "Polygon을 각각 정상 조회하였고 "
                    "두 Polygon 사이에 실제 면적 교차가 "
                    "확인되어 도시혁신구역으로 판정함"
                ),
        }

    elif (
        positive_control_valid
        and target_analysis_negative
        and parcel_geometry_valid
        and target_geometry_request_valid
        and not actual_intersection
    ):
        final = {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "FALSE",

            "confidence":
                "HIGH",

            "evidence_state":
                (
                    "POSITIVE_CONTROL_VALID_"
                    "TARGET_ANALYSIS_NEGATIVE_"
                    "NO_AREA_INTERSECTION"
                ),

            "reason":
                (
                    "동일 MapPlan req=analysis 체계에서 "
                    "AC 계열 양성대조 UQQ300이 정상 검출되어 "
                    "요청 의미가 유효함을 확인했고, 대상 PNU에서 "
                    "UQQ903은 analysis에 검출되지 않았으며 "
                    "UQQ903 geometry 정상조회 결과에서도 "
                    "대상 Parcel과 실제 면적 교차가 확인되지 않아 "
                    "도시혁신구역이 아닌 것으로 판정함"
                ),
        }

    else:
        reasons = []

        if not analysis_http_ok:
            reasons.append(
                "MapPlan analysis 정상응답 미확보"
            )

        if not positive_control_valid:
            reasons.append(
                "UQQ300 양성대조 미검증"
            )

        if not parcel_geometry_valid:
            reasons.append(
                "Parcel geometry 정상조회 실패"
            )

        if not target_geometry_request_valid:
            reasons.append(
                "UQQ903 geometry 정상조회 실패"
            )

        if target_analysis_positive:
            reasons.append(
                "UQQ903 analysis 양성이나 실제 Polygon "
                "intersection을 확정하지 못함"
            )

        final = {
            "query_status":
                (
                    "QUERY_FAILED"
                    if (
                        not analysis_http_ok
                        or not parcel_geometry_valid
                        or not target_geometry_request_valid
                    )
                    else "QUERY_SUCCESS"
                ),

            "resolution":
                "UNKNOWN",

            "confidence":
                (
                    "LOW"
                    if analysis_http_ok
                    else "NONE"
                ),

            "evidence_state":
                "INSUFFICIENT_EVIDENCE",

            "reason":
                "; ".join(
                    reasons
                )
                or (
                    "도시혁신구역 TRUE/FALSE 판정에 "
                    "필요한 evidence 조건을 충족하지 못함"
                ),
        }

    for key in [
        "query_status",
        "resolution",
        "confidence",
        "evidence_state",
        "reason",
    ]:
        print(
            f"{key}:",
            final[key],
        )

    print()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    validation = {
        "SITE ID 존재":
            bool(
                site["site_id"]
            ),

        "SITE 주소 존재":
            bool(
                site["address"]
            ),

        "PNU 19자리":
            pnu_valid,

        "7A Source Probe 존재":
            source_probe_exists,

        "도시혁신구역 UQQ903 검증":
            source_code_verified,

        "토지이음 지도 초기화":
            map_page_ok,

        "MapPlan server 복원":
            bool(
                mapplan_url
            ),

        "MapPlan version 복원":
            bool(
                version
            ),

        "EPSG:5179 BBOX 존재":
            bool(
                bbox
            ),

        "MapPlan analysis 실행":
            analysis_request[
                "http_status"
            ]
            is not None,

        "UQQ300 양성대조 검사":
            True,

        "UQQ903 analysis 검사":
            True,

        "Parcel Geometry 요청 실행":
            parcel_request[
                "http_status"
            ]
            is not None,

        "UQQ903 Geometry 요청 실행":
            target_request[
                "http_status"
            ]
            is not None,

        "Polygon intersection 실행":
            True,

        "TRUE는 실제 면적교차 필요":
            (
                final[
                    "resolution"
                ]
                != "TRUE"
                or actual_intersection
            ),

        "FALSE는 양성대조 필요":
            (
                final[
                    "resolution"
                ]
                != "FALSE"
                or positive_control_valid
            ),

        "FALSE는 UQQ903 analysis 음성 필요":
            (
                final[
                    "resolution"
                ]
                != "FALSE"
                or target_analysis_negative
            ),

        "FALSE는 실제 교차 없음 필요":
            (
                final[
                    "resolution"
                ]
                != "FALSE"
                or not actual_intersection
            ),

        "HTTP 403을 FALSE 근거로 사용 안 함":
            not (
                final[
                    "resolution"
                ]
                == "FALSE"
                and (
                    analysis_request[
                        "http_status"
                    ]
                    == 403
                    or parcel_request[
                        "http_status"
                    ]
                    == 403
                    or target_request[
                        "http_status"
                    ]
                    == 403
                )
            ),

        "query_status 허용값":
            final[
                "query_status"
            ]
            in {
                "QUERY_SUCCESS",
                "QUERY_FAILED",
                "NOT_QUERIED",
                "NOT_CONNECTED",
            },

        "resolution 허용값":
            final[
                "resolution"
            ]
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            },

        "confidence 허용값":
            final[
                "confidence"
            ]
            in {
                "HIGH",
                "MEDIUM",
                "LOW",
                "NONE",
            },
    }

    line()
    print(
        "=== C-9-2-7B 검증 ==="
    )
    line()

    for name, passed in (
        validation.items()
    ):
        print(
            f"{name}:",
            (
                "PASS"
                if passed
                else "FAIL"
            ),
        )

    print()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    result = {
        "step": STEP_NAME,

        "site": site,

        "target": {
            "name":
                TARGET_NAME,

            "code":
                TARGET_CODE,

            "layer":
                TARGET_LAYER,
        },

        "mapplan": {
            "gis_server":
                gis_server,

            "endpoint":
                mapplan_url,

            "version":
                version,

            "bbox_epsg5179":
                bbox,

            "mbr":
                mbr,
        },

        "analysis": {
            "request":
                analysis_request,

            "parsed":
                analysis,

            "positive_control": {
                "layer":
                    POSITIVE_CONTROL_LAYER,

                "code":
                    POSITIVE_CONTROL_CODE,

                **positive,
            },

            "target": {
                "layer":
                    TARGET_LAYER,

                "code":
                    TARGET_CODE,

                **target_analysis,
            },
        },

        "parcel_geometry": {
            "request":
                parcel_request,

            "geojson": {
                "valid":
                    parcel_geojson[
                        "valid"
                    ],

                "feature_count":
                    parcel_geojson[
                        "feature_count"
                    ],

                "geometry_types":
                    parcel_geojson[
                        "geometry_types"
                    ],
            },

            "geometry_valid":
                parcel_geometry_valid,

            "geometry_type":
                (
                    parcel_geom.geom_type
                    if parcel_geom
                    is not None
                    else None
                ),

            "area":
                (
                    float(
                        parcel_geom.area
                    )
                    if parcel_geom
                    is not None
                    else 0.0
                ),

            "bounds":
                (
                    list(
                        parcel_geom.bounds
                    )
                    if parcel_geom
                    is not None
                    else None
                ),
        },

        "target_geometry": {
            "request":
                target_request,

            "geojson": {
                "valid":
                    target_geojson[
                        "valid"
                    ],

                "feature_count":
                    target_geojson[
                        "feature_count"
                    ],

                "geometry_types":
                    target_geojson[
                        "geometry_types"
                    ],
            },

            "geometry_request_valid":
                target_geometry_request_valid,

            "geometry_negative":
                target_geometry_negative,

            "geometry_type":
                (
                    target_geom.geom_type
                    if target_geom
                    is not None
                    else None
                ),

            "area":
                (
                    float(
                        target_geom.area
                    )
                    if target_geom
                    is not None
                    else 0.0
                ),

            "bounds":
                (
                    list(
                        target_geom.bounds
                    )
                    if target_geom
                    is not None
                    else None
                ),
        },

        "intersection":
            intersection,

        "evidence": {
            "analysis_http_ok":
                analysis_http_ok,

            "positive_control_valid":
                positive_control_valid,

            "target_analysis_positive":
                target_analysis_positive,

            "target_analysis_negative":
                target_analysis_negative,

            "parcel_geometry_valid":
                parcel_geometry_valid,

            "target_geometry_request_valid":
                target_geometry_request_valid,

            "target_geometry_negative":
                target_geometry_negative,

            "target_geometry_positive":
                target_geometry_positive,

            "actual_intersection":
                actual_intersection,
        },

        "site_resolution":
            final,

        "validation":
            validation,
    }

    save_json(
        OUTPUT_PATH,
        result,
    )

    line()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    line()
    print()

    # --------------------------------------------------------
    # END
    # --------------------------------------------------------

    if all(
        validation.values()
    ):
        print(
            "STEP 17-21-C-9-2-7B 완료"
        )
    else:
        print(
            "STEP 17-21-C-9-2-7B "
            "검증 일부 미완료"
        )

    print()

    print(
        "도시혁신구역 최종 판정:"
    )

    print(
        final[
            "resolution"
        ]
    )

    print()

    if final[
        "resolution"
    ] == "TRUE":
        print(
            "Parcel Polygon × "
            "도시혁신구역 UQQ903 Polygon의 "
            "실제 면적교차를 확인했습니다."
        )

    elif final[
        "resolution"
    ] == "FALSE":
        print(
            "MapPlan 양성대조 정상, "
            "UQQ903 analysis 음성, "
            "Parcel과 UQQ903 면적교차 없음이 "
            "확인되었습니다."
        )

    else:
        print(
            "현재 evidence로 TRUE/FALSE를 "
            "확정하지 않고 UNKNOWN을 유지합니다."
        )

    print()

    if (
        analysis_request[
            "http_status"
        ]
        == 403
        or parcel_request[
            "http_status"
        ]
        == 403
        or target_request[
            "http_status"
        ]
        == 403
    ):
        print(
            "주의:"
        )
        print(
            "MapPlan HTTP 403이 확인되었습니다."
        )
        print(
            "403은 도시혁신구역 FALSE 근거가 아닙니다."
        )
        print(
            "접근 상태 회귀로 처리하고 UNKNOWN을 유지해야 합니다."
        )

    print()

    print(
        "다음 단계:"
    )

    if final[
        "resolution"
    ] in {
        "TRUE",
        "FALSE",
    }:
        print(
            "STEP 17-21-C-9-2-8"
        )
        print(
            "→ 다음 미해결 공간조건으로 진행"
        )
    else:
        print(
            "STEP 17-21-C-9-2-7B-1"
        )
        print(
            "→ MapPlan 요청/geometry 보정"
        )


if __name__ == "__main__":
    main()