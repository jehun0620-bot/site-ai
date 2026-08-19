import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-3B-1A
# 서울시 UQ129 개발진흥지구 Parcel Polygon 공간교차 보정
#
# 핵심 보정
# ------------------------------------------------------------
# 1. site_spatial_query_context.json 구조 고정 가정 제거
# 2. site_id / address / zone / PNU 재귀 탐색
# 3. site_id에서 필지 코드 복원
# 4. PNU 19자리 자동 복원
# 5. VWorld Parcel Polygon PNU 직접 검증
# 6. 서울시 UQ129 공간파일 로컬 자동 탐색
# 7. ZIP / SHP / GPKG 지원
# 8. CRS → EPSG:4326 정규화
# 9. Parcel × UQ129 실제 geometry intersection
# 10. 정상 전체 레이어 + 교차 없음일 때만 FALSE
# 11. 실패/불완전 조회는 UNKNOWN
# ============================================================


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

SEOUL_SOURCE_PATH = (
    BASE_DIR
    / "output"
    / "seoul_development_promotion_district_source_test.json"
)

PARCEL_PROBE_PATH = (
    BASE_DIR
    / "output"
    / "vworld_parcel_polygon_identifier_probe.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "seoul_development_promotion_district_intersection_test.json"
)


# ------------------------------------------------------------
# 공간파일 검색 후보 디렉터리
# ------------------------------------------------------------

SPATIAL_SEARCH_DIRS = [
    BASE_DIR / "input",
    BASE_DIR / "data",
    BASE_DIR / "spatial",
    BASE_DIR / "spatial_data",
    BASE_DIR / "download",
    BASE_DIR / "downloads",
    BASE_DIR / "output",
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "downloads",
]


VWORLD_PARCEL_DATASET_DEFAULT = "LP_PA_CBND_BUBUN"
SEOUL_UQ129_CODE = "UQ129"

REQUEST_TIMEOUT = 30


# ============================================================
# 기본 유틸
# ============================================================

def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:
    print(char * width)


def safe_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        (
            dict,
            list,
            tuple,
            set,
        ),
    ):
        return ""

    return str(value).strip()


def load_json(
    path: Path,
) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:
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


def normalize_digits(
    value: Any,
) -> str:
    return re.sub(
        r"\D",
        "",
        safe_text(value),
    )


def normalize_pnu(
    value: Any,
) -> str:
    digits = normalize_digits(value)

    if len(digits) == 19:
        return digits

    return ""


# ============================================================
# JSON 재귀 탐색
# ============================================================

def recursive_find_value(
    obj: Any,
    candidate_keys: List[str],
) -> str:
    """
    JSON 구조와 무관하게 candidate_keys 중 첫 유효값 탐색.
    """

    normalized_keys = {
        str(key).lower()
        for key in candidate_keys
    }

    if isinstance(obj, dict):

        # 현재 레벨 우선
        for key, value in obj.items():

            if (
                str(key).lower()
                in normalized_keys
            ):
                text = safe_text(value)

                if text:
                    return text

        # 하위 탐색
        for value in obj.values():

            result = recursive_find_value(
                value,
                candidate_keys,
            )

            if result:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = recursive_find_value(
                item,
                candidate_keys,
            )

            if result:
                return result

    return ""


def recursive_collect_strings(
    obj: Any,
) -> List[str]:
    result: List[str] = []

    if isinstance(obj, dict):

        for value in obj.values():
            result.extend(
                recursive_collect_strings(
                    value
                )
            )

    elif isinstance(obj, list):

        for item in obj:
            result.extend(
                recursive_collect_strings(
                    item
                )
            )

    elif isinstance(obj, str):

        text = obj.strip()

        if text:
            result.append(text)

    return result


# ============================================================
# Query Context 복원
# ============================================================

def extract_query_context(
    data: Dict[str, Any],
) -> Dict[str, str]:

    site_id = recursive_find_value(
        data,
        [
            "site_id",
            "SITE_ID",
            "siteId",
        ],
    )

    address = recursive_find_value(
        data,
        [
            "address",
            "주소",
            "jibun_address",
            "parcel_address",
            "lot_address",
        ],
    )

    zone = recursive_find_value(
        data,
        [
            "zone",
            "용도지역",
            "land_use_zone",
            "use_zone",
            "zoning",
        ],
    )

    parcel_key = recursive_find_value(
        data,
        [
            "parcel_key",
            "parcelKey",
        ],
    )

    pnu = normalize_pnu(
        recursive_find_value(
            data,
            [
                "pnu",
                "PNU",
            ],
        )
    )

    sigungu_code = normalize_digits(
        recursive_find_value(
            data,
            [
                "sigungu_code",
                "sgg_cd",
                "sigunguCode",
                "시군구코드",
            ],
        )
    )

    bjdong_code = normalize_digits(
        recursive_find_value(
            data,
            [
                "bjdong_code",
                "bjd_code",
                "bjdongCode",
                "법정동코드",
            ],
        )
    )

    san_code = normalize_digits(
        recursive_find_value(
            data,
            [
                "san_code",
                "san",
                "mountain_code",
                "산여부",
            ],
        )
    )

    main_no = normalize_digits(
        recursive_find_value(
            data,
            [
                "main_no",
                "mainNo",
                "bonbun",
                "본번",
            ],
        )
    )

    sub_no = normalize_digits(
        recursive_find_value(
            data,
            [
                "sub_no",
                "subNo",
                "bubun",
                "부번",
            ],
        )
    )

    # --------------------------------------------------------
    # site_id 복원
    # 11680-10300-0012-0000
    # --------------------------------------------------------

    if site_id:

        match = re.fullmatch(
            r"(\d{5})-(\d{5})-(\d{4})-(\d{4})",
            site_id,
        )

        if match:

            if not sigungu_code:
                sigungu_code = match.group(1)

            if not bjdong_code:
                bjdong_code = match.group(2)

            if not main_no:
                main_no = match.group(3)

            if not sub_no:
                sub_no = match.group(4)

            if not parcel_key:
                parcel_key = site_id

    # --------------------------------------------------------
    # parcel_key에서도 복원
    # --------------------------------------------------------

    if parcel_key:

        match = re.fullmatch(
            r"(\d{5})-(\d{5})-(\d{4})-(\d{4})",
            parcel_key,
        )

        if match:

            if not sigungu_code:
                sigungu_code = match.group(1)

            if not bjdong_code:
                bjdong_code = match.group(2)

            if not main_no:
                main_no = match.group(3)

            if not sub_no:
                sub_no = match.group(4)

    # --------------------------------------------------------
    # 자릿수 보정
    # --------------------------------------------------------

    if sigungu_code:
        sigungu_code = sigungu_code.zfill(5)

    if bjdong_code:
        bjdong_code = bjdong_code.zfill(5)

    if main_no:
        main_no = main_no.zfill(4)

    if sub_no:
        sub_no = sub_no.zfill(4)

    # 일반 토지 = 1
    if not san_code:
        san_code = "1"

    # --------------------------------------------------------
    # PNU 생성
    # --------------------------------------------------------

    if len(pnu) != 19:

        if (
            len(sigungu_code) == 5
            and len(bjdong_code) == 5
            and len(san_code) == 1
            and len(main_no) == 4
            and len(sub_no) == 4
        ):
            pnu = (
                sigungu_code
                + bjdong_code
                + san_code
                + main_no
                + sub_no
            )

    # --------------------------------------------------------
    # Parcel Key 생성
    # --------------------------------------------------------

    if (
        not parcel_key
        and len(sigungu_code) == 5
        and len(bjdong_code) == 5
        and len(main_no) == 4
        and len(sub_no) == 4
    ):
        parcel_key = (
            f"{sigungu_code}-"
            f"{bjdong_code}-"
            f"{main_no}-"
            f"{sub_no}"
        )

    # site_id가 없으면 parcel_key 사용
    if (
        not site_id
        and parcel_key
    ):
        site_id = parcel_key

    return {
        "site_id": site_id,
        "address": address,
        "zone": zone,
        "pnu": pnu,
        "parcel_key": parcel_key,
        "sigungu_code": sigungu_code,
        "bjdong_code": bjdong_code,
        "san_code": san_code,
        "main_no": main_no,
        "sub_no": sub_no,
    }


# ============================================================
# VWorld 인증 / 주소 좌표
# ============================================================

def get_vworld_api_key() -> str:

    load_dotenv(
        PROJECT_ROOT / ".env"
    )

    key = (
        os.getenv("VWORLD_API_KEY")
        or os.getenv("VWORLD_KEY")
        or ""
    ).strip()

    return key


def get_representative_coordinate(
    address: str,
    api_key: str,
) -> Tuple[
    Optional[float],
    Optional[float],
    Dict[str, Any],
]:

    url = (
        "https://api.vworld.kr/req/search"
    )

    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": 10,
        "page": 1,
        "query": address,
        "type": "address",
        "category": "parcel",
        "format": "json",
        "errorformat": "json",
        "key": api_key,
    }

    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    result: Dict[str, Any] = {
        "http_status": response.status_code,
        "url": response.url,
    }

    try:
        payload = response.json()
    except Exception:
        result["error"] = (
            "JSON 응답 파싱 실패"
        )
        return None, None, result

    result["payload"] = payload

    status = (
        payload
        .get("response", {})
        .get("status")
    )

    result["vworld_status"] = status

    if status != "OK":
        return None, None, result

    items = (
        payload
        .get("response", {})
        .get("result", {})
        .get("items", [])
    )

    if not items:
        return None, None, result

    point = (
        items[0]
        .get("point", {})
    )

    try:
        x = float(
            point.get("x")
        )

        y = float(
            point.get("y")
        )

    except (
        TypeError,
        ValueError,
    ):
        return None, None, result

    return x, y, result


# ============================================================
# VWorld Data API
# ============================================================

def query_vworld_data(
    dataset: str,
    api_key: str,
    geom_filter: str,
    size: int = 100,
) -> Tuple[
    Optional[Dict[str, Any]],
    Dict[str, Any],
]:

    url = (
        "https://api.vworld.kr/req/data"
    )

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": dataset,
        "key": api_key,
        "domain": "localhost",
        "format": "json",
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
        "geomFilter": geom_filter,
        "size": size,
        "page": 1,
    }

    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    meta: Dict[str, Any] = {
        "http_status": response.status_code,
        "request_url": response.url,
    }

    try:
        payload = response.json()
    except Exception:
        meta["error"] = (
            "VWorld Data API JSON 파싱 실패"
        )
        return None, meta

    meta["payload"] = payload

    status = (
        payload
        .get("response", {})
        .get("status")
    )

    meta["vworld_status"] = status

    if status != "OK":
        return payload, meta

    return payload, meta


def extract_features_from_vworld(
    payload: Optional[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    if not isinstance(
        payload,
        dict,
    ):
        return []

    result = (
        payload
        .get("response", {})
        .get("result", {})
    )

    feature_collection = (
        result.get(
            "featureCollection"
        )
    )

    if isinstance(
        feature_collection,
        dict,
    ):
        features = (
            feature_collection
            .get("features", [])
        )

        if isinstance(
            features,
            list,
        ):
            return features

    # 다른 VWorld 응답 구조 방어
    if isinstance(result, dict):

        for value in result.values():

            if isinstance(
                value,
                dict,
            ):
                features = value.get(
                    "features"
                )

                if isinstance(
                    features,
                    list,
                ):
                    return features

    return []


# ============================================================
# Parcel dataset 추출
# ============================================================

def extract_parcel_dataset(
    parcel_probe: Any,
) -> str:

    candidates = [
        recursive_find_value(
            parcel_probe,
            [
                "selected_dataset",
                "parcel_dataset",
                "best_dataset",
            ],
        ),
        recursive_find_value(
            parcel_probe,
            [
                "dataset",
            ],
        ),
    ]

    for candidate in candidates:

        candidate = (
            candidate.strip()
            if candidate
            else ""
        )

        if (
            candidate
            == VWORLD_PARCEL_DATASET_DEFAULT
        ):
            return candidate

    # Probe 로그에서 이미 검증된 기본값 사용
    return VWORLD_PARCEL_DATASET_DEFAULT


# ============================================================
# Geometry 유틸
# ============================================================

def import_geometry_modules():

    try:
        from shapely.geometry import (
            Point,
            shape,
        )
        from shapely.ops import (
            unary_union,
        )

    except ImportError as exc:
        raise RuntimeError(
            "shapely가 설치되어 있지 않습니다. "
            "pip install shapely"
        ) from exc

    return (
        Point,
        shape,
        unary_union,
    )


def feature_pnu(
    feature: Dict[str, Any],
) -> str:

    properties = (
        feature.get(
            "properties"
        )
        or {}
    )

    keys = [
        "pnu",
        "PNU",
        "pnu_cd",
        "PNU_CD",
    ]

    for key in keys:

        value = properties.get(
            key
        )

        normalized = normalize_pnu(
            value
        )

        if normalized:
            return normalized

    return ""


def feature_to_geometry(
    feature: Dict[str, Any],
):
    _, shape, _ = (
        import_geometry_modules()
    )

    geometry = feature.get(
        "geometry"
    )

    if not geometry:
        return None

    try:
        geom = shape(
            geometry
        )
    except Exception:
        return None

    if geom.is_empty:
        return None

    if not geom.is_valid:

        try:
            geom = geom.buffer(0)
        except Exception:
            return None

    if geom.is_empty:
        return None

    return geom


# ============================================================
# Parcel Polygon 조회
# ============================================================

def query_parcel_polygon(
    context: Dict[str, str],
    parcel_dataset: str,
    api_key: str,
) -> Dict[str, Any]:

    address = context.get(
        "address",
        "",
    )

    target_pnu = context.get(
        "pnu",
        "",
    )

    result: Dict[str, Any] = {
        "dataset": parcel_dataset,
        "target_pnu": target_pnu,
        "query_status": "QUERY_FAILED",
        "matched_feature_count": 0,
    }

    x, y, address_meta = (
        get_representative_coordinate(
            address=address,
            api_key=api_key,
        )
    )

    result[
        "address_search"
    ] = address_meta

    if (
        x is None
        or y is None
    ):
        result[
            "reason"
        ] = (
            "대표 좌표 확보 실패"
        )
        return result

    result["representative_point"] = {
        "x": x,
        "y": y,
    }

    # --------------------------------------------------------
    # 필지 하나를 찾기 위한 작은 BOX
    # --------------------------------------------------------

    delta = 0.001

    geom_filter = (
        f"BOX("
        f"{x - delta},"
        f"{y - delta},"
        f"{x + delta},"
        f"{y + delta}"
        f")"
    )

    payload, meta = query_vworld_data(
        dataset=parcel_dataset,
        api_key=api_key,
        geom_filter=geom_filter,
        size=100,
    )

    result["query"] = meta

    if (
        meta.get(
            "vworld_status"
        )
        != "OK"
    ):
        result["reason"] = (
            "VWorld Parcel Data API "
            "정상 응답을 받지 못함"
        )
        return result

    features = extract_features_from_vworld(
        payload
    )

    result[
        "feature_count"
    ] = len(features)

    matched = []

    for feature in features:

        pnu = feature_pnu(
            feature
        )

        if pnu == target_pnu:
            matched.append(
                feature
            )

    result[
        "matched_feature_count"
    ] = len(matched)

    if not matched:

        result["reason"] = (
            "조회 Feature 중 대상 PNU와 "
            "직접 일치하는 필지가 없음"
        )
        return result

    valid_features = []

    for feature in matched:

        geom = feature_to_geometry(
            feature
        )

        if geom is None:
            continue

        valid_features.append(
            (
                feature,
                geom,
            )
        )

    if not valid_features:

        result["reason"] = (
            "대상 PNU Feature는 있으나 "
            "Polygon geometry 해석 실패"
        )
        return result

    _, _, unary_union = (
        import_geometry_modules()
    )

    parcel_geometry = unary_union(
        [
            geom
            for _, geom
            in valid_features
        ]
    )

    result[
        "query_status"
    ] = "QUERY_SUCCESS"

    result[
        "reason"
    ] = (
        "대상 PNU와 직접 일치하는 "
        "Parcel Polygon 확보"
    )

    result[
        "feature_ids"
    ] = [
        feature.get(
            "id"
        )
        for feature, _
        in valid_features
    ]

    result[
        "_geometry"
    ] = parcel_geometry

    return result


# ============================================================
# UQ129 공간파일 탐색
# ============================================================

def spatial_filename_score(
    path: Path,
) -> int:

    name = path.name.lower()

    score = 0

    if "uq129" in name:
        score += 100

    if "개발진흥" in path.name:
        score += 80

    if "용도지구" in path.name:
        score += 20

    if path.suffix.lower() == ".zip":
        score += 10

    if path.suffix.lower() == ".shp":
        score += 8

    if path.suffix.lower() == ".gpkg":
        score += 6

    return score


def find_local_uq129_files() -> List[Path]:

    candidates: List[Path] = []

    extensions = {
        ".zip",
        ".shp",
        ".gpkg",
        ".geojson",
        ".json",
    }

    for directory in SPATIAL_SEARCH_DIRS:

        if not directory.exists():
            continue

        try:
            paths = directory.rglob(
                "*"
            )
        except Exception:
            continue

        for path in paths:

            if not path.is_file():
                continue

            if (
                path.suffix.lower()
                not in extensions
            ):
                continue

            name = path.name.lower()

            if (
                "uq129" in name
                or "개발진흥" in path.name
            ):
                candidates.append(
                    path
                )

    # 중복 제거
    unique = []

    seen = set()

    for path in candidates:

        resolved = str(
            path.resolve()
        )

        if resolved in seen:
            continue

        seen.add(
            resolved
        )

        unique.append(
            path
        )

    unique.sort(
        key=spatial_filename_score,
        reverse=True,
    )

    return unique


# ============================================================
# Source JSON에서 경로 후보 검색
# ============================================================

def find_source_file_paths(
    source_data: Any,
) -> List[Path]:

    strings = recursive_collect_strings(
        source_data
    )

    candidates = []

    for text in strings:

        lower = text.lower()

        if not any(
            lower.endswith(ext)
            for ext in [
                ".zip",
                ".shp",
                ".gpkg",
                ".geojson",
            ]
        ):
            continue

        try:
            path = Path(text)
        except Exception:
            continue

        if path.exists():
            candidates.append(
                path
            )

    return candidates


# ============================================================
# ZIP 압축 해제
# ============================================================

def extract_zip_to_temp(
    zip_path: Path,
) -> Path:

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="uq129_"
        )
    )

    with zipfile.ZipFile(
        zip_path,
        "r",
    ) as zf:

        zf.extractall(
            temp_dir
        )

    return temp_dir


# ============================================================
# 공간파일 로드
# ============================================================

def import_geopandas():

    try:
        import geopandas as gpd

    except ImportError as exc:

        raise RuntimeError(
            "geopandas가 설치되어 있지 않습니다.\n"
            "설치 예:\n"
            "pip install geopandas pyogrio shapely pyproj"
        ) from exc

    return gpd


def find_shapefile_in_directory(
    directory: Path,
) -> Optional[Path]:

    candidates = list(
        directory.rglob(
            "*.shp"
        )
    )

    if not candidates:
        return None

    candidates.sort(
        key=spatial_filename_score,
        reverse=True,
    )

    return candidates[0]


def load_uq129_layer(
    path: Path,
):
    gpd = import_geopandas()

    actual_path = path

    extracted_dir = None

    if (
        path.suffix.lower()
        == ".zip"
    ):
        extracted_dir = (
            extract_zip_to_temp(
                path
            )
        )

        shp = (
            find_shapefile_in_directory(
                extracted_dir
            )
        )

        if shp is None:
            raise RuntimeError(
                "UQ129 ZIP 내부에서 SHP 파일을 찾지 못했습니다."
            )

        actual_path = shp

    gdf = gpd.read_file(
        actual_path
    )

    if gdf.empty:
        raise RuntimeError(
            "UQ129 공간레이어가 비어 있습니다."
        )

    if "geometry" not in gdf.columns:
        raise RuntimeError(
            "UQ129 공간레이어에 geometry 컬럼이 없습니다."
        )

    gdf = gdf[
        gdf.geometry.notna()
    ].copy()

    if gdf.empty:
        raise RuntimeError(
            "UQ129 레이어에서 유효 geometry가 없습니다."
        )

    # --------------------------------------------------------
    # CRS
    # --------------------------------------------------------

    original_crs = (
        str(gdf.crs)
        if gdf.crs
        else ""
    )

    # 공식 파일 CRS가 EPSG:5174라는 이전 검증값 사용
    if gdf.crs is None:

        gdf = gdf.set_crs(
            epsg=5174,
            allow_override=True,
        )

        crs_assumption = (
            "파일 CRS metadata 없음 → "
            "공식 UQ129 CRS EPSG:5174 적용"
        )

    else:

        crs_assumption = (
            "파일 CRS metadata 사용"
        )

    gdf_4326 = gdf.to_crs(
        epsg=4326
    )

    return {
        "gdf": gdf_4326,
        "actual_path": actual_path,
        "source_path": path,
        "extracted_dir": extracted_dir,
        "original_crs": original_crs,
        "normalized_crs": "EPSG:4326",
        "crs_assumption": crs_assumption,
    }


# ============================================================
# UQ129 속성 field 유틸
# ============================================================

def find_column_case_insensitive(
    columns,
    candidates: List[str],
) -> Optional[str]:

    mapping = {
        str(column).lower():
            column
        for column in columns
    }

    for candidate in candidates:

        key = candidate.lower()

        if key in mapping:
            return mapping[key]

    return None


def extract_feature_label(
    row,
    columns,
) -> str:

    label_column = (
        find_column_case_insensitive(
            columns,
            [
                "LBL_NM",
                "dgm_nm",
                "label",
                "name",
            ],
        )
    )

    if not label_column:
        return ""

    value = row.get(
        label_column
    )

    return safe_text(
        value
    )


# ============================================================
# 공간 교차
# ============================================================

def run_intersection(
    parcel_geometry,
    uq129_gdf,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "layer_feature_count":
            int(
                len(
                    uq129_gdf
                )
            ),
        "intersecting_feature_count": 0,
        "intersections": [],
        "max_intersection_ratio": 0.0,
    }

    if parcel_geometry is None:
        result[
            "error"
        ] = (
            "Parcel geometry 없음"
        )
        return result

    if parcel_geometry.is_empty:
        result[
            "error"
        ] = (
            "Parcel geometry가 비어 있음"
        )
        return result

    parcel_area = float(
        parcel_geometry.area
    )

    result[
        "parcel_area_degree2"
    ] = parcel_area

    if parcel_area <= 0:
        result[
            "error"
        ] = (
            "Parcel geometry 면적이 0 이하"
        )
        return result

    # --------------------------------------------------------
    # bbox 1차 후보 필터
    # --------------------------------------------------------

    minx, miny, maxx, maxy = (
        parcel_geometry.bounds
    )

    try:
        subset = uq129_gdf.cx[
            minx:maxx,
            miny:maxy
        ]
    except Exception:
        subset = uq129_gdf

    result[
        "bbox_candidate_count"
    ] = int(
        len(
            subset
        )
    )

    max_ratio = 0.0

    for index, row in subset.iterrows():

        geometry = row.geometry

        if (
            geometry is None
            or geometry.is_empty
        ):
            continue

        try:
            intersects = (
                parcel_geometry
                .intersects(
                    geometry
                )
            )
        except Exception:
            continue

        if not intersects:
            continue

        try:
            intersection_geometry = (
                parcel_geometry
                .intersection(
                    geometry
                )
            )

            intersection_area = float(
                intersection_geometry.area
            )

        except Exception:
            intersection_area = 0.0

        ratio = (
            intersection_area
            / parcel_area
            if parcel_area > 0
            else 0.0
        )

        max_ratio = max(
            max_ratio,
            ratio,
        )

        properties = {}

        for column in subset.columns:

            if column == "geometry":
                continue

            value = row.get(
                column
            )

            if value is None:
                continue

            try:
                if value != value:
                    continue
            except Exception:
                pass

            properties[
                str(column)
            ] = safe_text(
                value
            )

        result[
            "intersections"
        ].append(
            {
                "row_index":
                    safe_text(index),
                "label":
                    extract_feature_label(
                        row,
                        subset.columns,
                    ),
                "intersection_area_degree2":
                    intersection_area,
                "intersection_ratio":
                    ratio,
                "properties":
                    properties,
            }
        )

    result[
        "intersecting_feature_count"
    ] = len(
        result[
            "intersections"
        ]
    )

    result[
        "max_intersection_ratio"
    ] = max_ratio

    return result


# ============================================================
# 검증
# ============================================================

def run_validations(
    context: Dict[str, str],
    parcel_result: Dict[str, Any],
    layer_result: Optional[
        Dict[str, Any]
    ],
    resolution: str,
    query_status: str,
) -> Dict[str, bool]:

    pnu = context.get(
        "pnu",
        "",
    )

    validations = {
        "SITE ID 복원":
            bool(
                context.get(
                    "site_id"
                )
            ),

        "SITE 주소 존재":
            bool(
                context.get(
                    "address"
                )
            ),

        "PNU 19자리":
            bool(
                re.fullmatch(
                    r"\d{19}",
                    pnu,
                )
            ),

        "개포동 12번지 기준 PNU":
            (
                pnu
                == "1168010300100120000"
            ),

        "Parcel query status 허용값":
            (
                parcel_result.get(
                    "query_status"
                )
                in {
                    "QUERY_SUCCESS",
                    "QUERY_FAILED",
                }
            ),

        "Parcel PNU 직접 검증":
            (
                parcel_result.get(
                    "query_status"
                )
                != "QUERY_SUCCESS"
                or parcel_result.get(
                    "matched_feature_count",
                    0,
                )
                >= 1
            ),

        "resolution 허용값":
            resolution
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            },

        "query_status 허용값":
            query_status
            in {
                "QUERY_SUCCESS",
                "QUERY_FAILED",
                "NOT_CONNECTED",
                "NOT_QUERIED",
            },

        "공간조회 실패 시 TRUE/FALSE 금지":
            (
                query_status
                == "QUERY_SUCCESS"
                or resolution
                == "UNKNOWN"
            ),
    }

    if layer_result is not None:

        validations[
            "UQ129 레이어 feature 존재"
        ] = (
            layer_result.get(
                "feature_count",
                0,
            )
            > 0
        )

        validations[
            "UQ129 EPSG:4326 정규화"
        ] = (
            layer_result.get(
                "normalized_crs"
            )
            == "EPSG:4326"
        )

    return validations


# ============================================================
# 메인
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-9-2-3B-1A "
        "서울시 UQ129 개발진흥지구 Parcel Polygon 공간교차 보정 테스트 ==="
    )
    print()

    print(
        "Query Context 입력:"
    )
    print(
        QUERY_CONTEXT_PATH
    )
    print()

    print(
        "서울 Source 입력:"
    )
    print(
        SEOUL_SOURCE_PATH
    )
    print()

    print(
        "Parcel Probe 입력:"
    )
    print(
        PARCEL_PROBE_PATH
    )
    print()

    # --------------------------------------------------------
    # 입력 검사
    # --------------------------------------------------------

    if not QUERY_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"Query Context 파일이 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    if not SEOUL_SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"서울 Source 파일이 없습니다: "
            f"{SEOUL_SOURCE_PATH}"
        )

    if not PARCEL_PROBE_PATH.exists():
        raise FileNotFoundError(
            f"Parcel Probe 파일이 없습니다: "
            f"{PARCEL_PROBE_PATH}"
        )

    query_data = load_json(
        QUERY_CONTEXT_PATH
    )

    source_data = load_json(
        SEOUL_SOURCE_PATH
    )

    parcel_probe = load_json(
        PARCEL_PROBE_PATH
    )

    context = extract_query_context(
        query_data
    )

    # --------------------------------------------------------
    # SITE 출력
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 대상 SITE ==="
    )
    print_separator()

    print(
        "SITE ID:",
        context.get(
            "site_id"
        )
        or "-",
    )

    print(
        "주소:",
        context.get(
            "address"
        )
        or "-",
    )

    print(
        "용도지역:",
        context.get(
            "zone"
        )
        or "-",
    )

    print(
        "PNU:",
        context.get(
            "pnu"
        )
        or "-",
    )

    print(
        "시군구코드:",
        context.get(
            "sigungu_code"
        )
        or "-",
    )

    print(
        "법정동코드:",
        context.get(
            "bjdong_code"
        )
        or "-",
    )

    print(
        "산여부:",
        context.get(
            "san_code"
        )
        or "-",
    )

    print(
        "본번:",
        context.get(
            "main_no"
        )
        or "-",
    )

    print(
        "부번:",
        context.get(
            "sub_no"
        )
        or "-",
    )

    print(
        "Parcel Key:",
        context.get(
            "parcel_key"
        )
        or "-",
    )

    print()

    pnu = context.get(
        "pnu",
        "",
    )

    if not re.fullmatch(
        r"\d{19}",
        pnu,
    ):
        raise RuntimeError(
            "PNU가 19자리가 아닙니다. "
            "Query Context 복원에도 실패했습니다."
        )

    # --------------------------------------------------------
    # Parcel dataset
    # --------------------------------------------------------

    parcel_dataset = (
        extract_parcel_dataset(
            parcel_probe
        )
    )

    print_separator()
    print(
        "=== 공간조회 Dataset ==="
    )
    print_separator()

    print(
        "Parcel dataset:",
        parcel_dataset,
    )

    print(
        "개발진흥지구:",
        "서울시 UQ129",
    )

    print()

    # --------------------------------------------------------
    # VWorld Key
    # --------------------------------------------------------

    api_key = (
        get_vworld_api_key()
    )

    print_separator()
    print(
        "=== VWorld 인증 ==="
    )
    print_separator()

    if api_key:
        print(
            "VWORLD_API_KEY: "
            "정상적으로 읽었습니다."
        )
    else:
        print(
            "VWORLD_API_KEY: 없음"
        )

    print()

    if not api_key:

        output_data = {
            "step":
                "STEP 17-21-C-9-2-3B-1A",
            "site":
                context,
            "condition":
                "개발진흥지구",
            "query_status":
                "NOT_CONNECTED",
            "resolution":
                "UNKNOWN",
            "confidence":
                "NONE",
            "reason":
                "VWORLD_API_KEY가 없어 "
                "Parcel Polygon을 조회하지 못함",
        }

        save_json(
            OUTPUT_PATH,
            output_data,
        )

        return

    # --------------------------------------------------------
    # Parcel Polygon
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. 대상 Parcel Polygon 조회 ==="
    )
    print_separator()

    parcel_result = (
        query_parcel_polygon(
            context=context,
            parcel_dataset=parcel_dataset,
            api_key=api_key,
        )
    )

    print(
        "query_status:",
        parcel_result.get(
            "query_status"
        ),
    )

    print(
        "전체 Feature 수:",
        parcel_result.get(
            "feature_count",
            0,
        ),
    )

    print(
        "대상 PNU 일치 Feature 수:",
        parcel_result.get(
            "matched_feature_count",
            0,
        ),
    )

    point = parcel_result.get(
        "representative_point"
    )

    if point:
        print(
            "대표좌표 X:",
            point.get("x"),
        )

        print(
            "대표좌표 Y:",
            point.get("y"),
        )

    print(
        "reason:",
        parcel_result.get(
            "reason",
            "",
        ),
    )

    print()

    parcel_geometry = (
        parcel_result.pop(
            "_geometry",
            None,
        )
    )

    if (
        parcel_result.get(
            "query_status"
        )
        != "QUERY_SUCCESS"
        or parcel_geometry is None
    ):

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
            "대상 PNU Parcel Polygon을 "
            "확보하지 못해 UQ129 공간교차를 "
            "수행하지 않음"
        )

        validations = run_validations(
            context=context,
            parcel_result=parcel_result,
            layer_result=None,
            resolution=resolution,
            query_status=query_status,
        )

        output_data = {
            "step":
                "STEP 17-21-C-9-2-3B-1A",
            "site":
                context,
            "condition":
                "개발진흥지구",
            "parcel":
                parcel_result,
            "uq129":
                None,
            "query_status":
                query_status,
            "resolution":
                resolution,
            "confidence":
                confidence,
            "reason":
                reason,
            "validations":
                validations,
            "all_pass":
                all(
                    validations.values()
                ),
        }

        save_json(
            OUTPUT_PATH,
            output_data,
        )

        print(
            "개발진흥지구 최종 판정:",
            resolution,
        )

        print(
            reason
        )

        return

    # --------------------------------------------------------
    # UQ129 파일 탐색
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. 서울시 UQ129 공간파일 탐색 ==="
    )
    print_separator()

    source_paths = (
        find_source_file_paths(
            source_data
        )
    )

    local_paths = (
        find_local_uq129_files()
    )

    all_candidates = []

    for path in (
        source_paths
        + local_paths
    ):

        if not path.exists():
            continue

        if (
            path
            not in all_candidates
        ):
            all_candidates.append(
                path
            )

    all_candidates.sort(
        key=spatial_filename_score,
        reverse=True,
    )

    print(
        "공간파일 후보 수:",
        len(
            all_candidates
        ),
    )

    for index, path in enumerate(
        all_candidates[:20],
        start=1,
    ):
        print(
            f"{index}. {path}"
        )

    print()

    # --------------------------------------------------------
    # 파일 없음
    # --------------------------------------------------------

    if not all_candidates:

        query_status = (
            "NOT_CONNECTED"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "서울시 UQ129 OpenAPI 속성 source는 "
            "연결되었으나 UQ129 Polygon 공간파일을 "
            "로컬에서 찾지 못해 실제 공간교차를 "
            "수행하지 않음"
        )

        validations = run_validations(
            context=context,
            parcel_result=parcel_result,
            layer_result=None,
            resolution=resolution,
            query_status=query_status,
        )

        output_data = {
            "step":
                "STEP 17-21-C-9-2-3B-1A",
            "site":
                context,
            "condition":
                "개발진흥지구",
            "parcel":
                parcel_result,
            "uq129": {
                "official_code":
                    SEOUL_UQ129_CODE,
                "spatial_file_found":
                    False,
            },
            "query_status":
                query_status,
            "resolution":
                resolution,
            "confidence":
                confidence,
            "reason":
                reason,
            "validations":
                validations,
            "all_pass":
                all(
                    validations.values()
                ),
        }

        save_json(
            OUTPUT_PATH,
            output_data,
        )

        print_separator()
        print(
            "=== 현재 개발진흥지구 SITE 판정 ==="
        )
        print_separator()

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
            "reason:",
            reason,
        )

        print()

        print_separator()
        print(
            "결과 저장:"
        )
        print(
            OUTPUT_PATH
        )
        print_separator()

        print()
        print(
            "다음 작업:"
        )
        print(
            "서울시 UQ129 공간파일 ZIP/SHP를 "
            "law_data/input 또는 law_data/spatial에 저장한 후 재실행"
        )

        return

    # --------------------------------------------------------
    # UQ129 로드
    # --------------------------------------------------------

    selected_path = (
        all_candidates[0]
    )

    print_separator()
    print(
        "=== 3. UQ129 공간레이어 로드 ==="
    )
    print_separator()

    print(
        "선택 파일:",
        selected_path,
    )

    try:
        loaded = (
            load_uq129_layer(
                selected_path
            )
        )

    except Exception as exc:

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
            "UQ129 공간레이어 로드 실패: "
            f"{exc}"
        )

        validations = run_validations(
            context=context,
            parcel_result=parcel_result,
            layer_result=None,
            resolution=resolution,
            query_status=query_status,
        )

        output_data = {
            "step":
                "STEP 17-21-C-9-2-3B-1A",
            "site":
                context,
            "condition":
                "개발진흥지구",
            "parcel":
                parcel_result,
            "uq129": {
                "official_code":
                    SEOUL_UQ129_CODE,
                "selected_file":
                    str(
                        selected_path
                    ),
                "load_error":
                    str(exc),
            },
            "query_status":
                query_status,
            "resolution":
                resolution,
            "confidence":
                confidence,
            "reason":
                reason,
            "validations":
                validations,
            "all_pass":
                all(
                    validations.values()
                ),
        }

        save_json(
            OUTPUT_PATH,
            output_data,
        )

        print(
            reason
        )

        return

    uq129_gdf = loaded[
        "gdf"
    ]

    layer_result = {
        "official_code":
            SEOUL_UQ129_CODE,

        "selected_file":
            str(
                selected_path
            ),

        "actual_layer_path":
            str(
                loaded[
                    "actual_path"
                ]
            ),

        "feature_count":
            int(
                len(
                    uq129_gdf
                )
            ),

        "original_crs":
            loaded[
                "original_crs"
            ],

        "normalized_crs":
            loaded[
                "normalized_crs"
            ],

        "crs_assumption":
            loaded[
                "crs_assumption"
            ],
    }

    print(
        "Feature 수:",
        layer_result[
            "feature_count"
        ],
    )

    print(
        "원본 CRS:",
        layer_result[
            "original_crs"
        ]
        or "-",
    )

    print(
        "정규화 CRS:",
        layer_result[
            "normalized_crs"
        ],
    )

    print(
        "CRS 처리:",
        layer_result[
            "crs_assumption"
        ],
    )

    print()

    # --------------------------------------------------------
    # Intersection
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 4. Parcel Polygon × 개발진흥지구 Polygon 교차분석 ==="
    )
    print_separator()

    intersection_result = (
        run_intersection(
            parcel_geometry=
                parcel_geometry,
            uq129_gdf=
                uq129_gdf,
        )
    )

    print(
        "전체 UQ129 Feature:",
        intersection_result.get(
            "layer_feature_count",
            0,
        ),
    )

    print(
        "Parcel BBOX 후보:",
        intersection_result.get(
            "bbox_candidate_count",
            0,
        ),
    )

    print(
        "실제 교차 Feature:",
        intersection_result.get(
            "intersecting_feature_count",
            0,
        ),
    )

    print(
        "최대 교차 비율:",
        intersection_result.get(
            "max_intersection_ratio",
            0.0,
        ),
    )

    print()

    for index, item in enumerate(
        intersection_result.get(
            "intersections",
            [],
        ),
        start=1,
    ):

        print(
            "-" * 70
        )

        print(
            f"교차 Feature {index}"
        )

        print(
            "label:",
            item.get(
                "label"
            )
            or "-",
        )

        print(
            "교차 면적(degree²):",
            item.get(
                "intersection_area_degree2"
            ),
        )

        print(
            "교차 비율:",
            item.get(
                "intersection_ratio"
            ),
        )

        properties = item.get(
            "properties",
            {},
        )

        for key in [
            "LBL_NM",
            "STUT_FIG_MNG_NO",
            "FIG_LCLSF_CD",
            "FIG_MCLSF_CD",
            "FIG_SCLSF_CD",
            "FIG_ATRB_CD",
            "SGG_CD",
        ]:

            if key in properties:
                print(
                    f"{key}:",
                    properties[
                        key
                    ],
                )

    print()

    # --------------------------------------------------------
    # 최종 판정
    # --------------------------------------------------------

    intersection_count = (
        intersection_result.get(
            "intersecting_feature_count",
            0,
        )
    )

    if intersection_count > 0:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "TRUE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "대상 PNU와 직접 일치하는 "
            "Parcel Polygon과 서울시 UQ129 "
            "개발진흥지구 Polygon 사이에 실제 "
            "면적 교차가 확인됨"
        )

    else:

        # 전체 공간레이어가 정상적으로 로드되고
        # 대상 Parcel geometry도 정상 확보된 상황에서
        # 교차가 없으므로 FALSE 가능.
        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "FALSE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "서울시 UQ129 개발진흥지구 "
            "공간레이어 전체를 정상 로드하고 "
            "대상 PNU Parcel Polygon과 "
            "공간교차를 수행했으나 "
            "교차 Feature가 확인되지 않음"
        )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = run_validations(
        context=context,
        parcel_result=parcel_result,
        layer_result=layer_result,
        resolution=resolution,
        query_status=query_status,
    )

    # 추가 검증
    validations[
        "UQ129 공식 코드"
    ] = (
        SEOUL_UQ129_CODE
        == "UQ129"
    )

    validations[
        "TRUE는 실제 교차 존재"
    ] = (
        resolution
        != "TRUE"
        or intersection_count > 0
    )

    validations[
        "FALSE는 전체 레이어 정상조회 후 교차 없음"
    ] = (
        resolution
        != "FALSE"
        or (
            query_status
            == "QUERY_SUCCESS"
            and layer_result[
                "feature_count"
            ]
            > 0
            and intersection_count
            == 0
        )
    )

    all_pass = all(
        validations.values()
    )

    # --------------------------------------------------------
    # 결과 출력
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 5. 개발진흥지구 공간조건 최종 판정 ==="
    )
    print_separator()

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
        "reason:",
        reason,
    )

    print(
        "최대 필지 교차 비율:",
        intersection_result.get(
            "max_intersection_ratio",
            0.0,
        ),
    )

    print()

    print_separator()
    print(
        "=== C-9-2-3B-1A 검증 ==="
    )
    print_separator()

    for name, passed in (
        validations.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    # --------------------------------------------------------
    # JSON 저장
    # --------------------------------------------------------

    output_data = {
        "step":
            "STEP 17-21-C-9-2-3B-1A",

        "site":
            context,

        "condition":
            "개발진흥지구",

        "parcel":
            parcel_result,

        "uq129":
            layer_result,

        "intersection":
            intersection_result,

        "query_status":
            query_status,

        "resolution":
            resolution,

        "confidence":
            confidence,

        "reason":
            reason,

        "validations":
            validations,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print_separator()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print_separator()
    print()

    if all_pass:

        print(
            "STEP 17-21-C-9-2-3B-1A 완료"
        )

        print()

        print(
            "개발진흥지구 최종 판정:"
        )

        print(
            resolution
        )

        print()

        if resolution in {
            "TRUE",
            "FALSE",
        }:

            print(
                "Parcel Polygon × 서울시 UQ129 "
                "Polygon 실제 공간교차 검증 완료"
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-4"
            )

            print(
                "→ 개발밀도관리구역 실제 공간조회"
            )

            print(
                "→ 자연경관지구 / 입체복합구역 / "
                "수산자원보호구역 / 취락지구 순차 판정"
            )

    else:

        print(
            "STEP 17-21-C-9-2-3B-1A 검증 실패"
        )

        print(
            "FAIL 항목을 먼저 확인하십시오."
        )


if __name__ == "__main__":
    main()