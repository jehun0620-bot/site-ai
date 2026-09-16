from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET = "LT_C_UPISUQ161"
DEFAULT_PNU = "1168010300100120000"
VWORLD_DATA_URL = "https://api.vworld.kr/req/data"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _find_key(mapping: Mapping[str, Any], candidates: tuple[str, ...]) -> tuple[str | None, Any]:
    lowered = {str(key).lower(): key for key in mapping}
    for candidate in candidates:
        original = lowered.get(candidate.lower())
        if original is not None:
            return str(original), mapping.get(original)
    return None, None


def _candidate_identity_fields(properties: Mapping[str, Any]) -> dict[str, Any]:
    groups = {
        "notice_serial": ("ntfc_sn",),
        "drawing_name": ("dgm_nm",),
        "presentation_serial": ("present_sn",),
        "large_class": ("lclas_cl", "lcl_nam"),
        "middle_class": ("mlsfc_cl", "mls_nam"),
        "small_class": ("sclas_cl", "scl_nam"),
        "attribute_type": ("atrb_se", "atr_nam"),
        "district_name": ("sig_nam",),
        "legacy_designation_year": ("dyear",),
        "legacy_designation_number": ("dnum",),
    }
    result: dict[str, Any] = {}
    for label, candidates in groups.items():
        key, value = _find_key(properties, candidates)
        result[label] = {
            "source_key": key,
            "value": value,
            "present": bool(_text(value)),
        }
    return result


def _coordinate(name: str) -> float:
    raw = _text(os.getenv(name))
    if not raw:
        print(f"ERROR: {name} is required for point-geometry probing.")
        print("Set it only in the current PowerShell session; .env modification is not required.")
        sys.exit(2)
    try:
        return float(raw)
    except ValueError:
        print(f"ERROR: {name} must be a decimal coordinate, got {raw!r}.")
        sys.exit(2)


def main() -> None:
    """Probe raw VWorld district-unit-plan attributes at an explicit point.

    PNU is retained only as diagnostic target identity. LT_C_UPISUQ161 does not
    accept PNU as an attrFilter field, so this probe requires an explicit WGS84
    longitude/latitude point. Returned attributes are diagnostic candidates only:
    no field is asserted to equal a Seoul upisAnnouncement identity field, and no
    SITE truth, promotion, or production/runtime authority is granted.
    """

    load_dotenv(BASE_DIR / ".env")
    service_key = os.getenv("VWORLD_API_KEY") or os.getenv("VWORLD_KEY")
    if not service_key:
        print("ERROR: VWorld API key not found (VWORLD_API_KEY or VWORLD_KEY).")
        sys.exit(2)

    pnu = _text(os.getenv("DISTRICT_UNIT_PLAN_PROBE_PNU")) or DEFAULT_PNU
    longitude = _coordinate("DISTRICT_UNIT_PLAN_PROBE_LON")
    latitude = _coordinate("DISTRICT_UNIT_PLAN_PROBE_LAT")

    if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
        print("ERROR: probe coordinates are outside WGS84 longitude/latitude ranges.")
        sys.exit(2)

    point_wkt = f"POINT({longitude} {latitude})"
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": DATASET,
        "key": service_key,
        "domain": "localhost",
        "format": "json",
        "size": "20",
        "geomFilter": point_wkt,
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
    }

    print("=" * 72)
    print("DISTRICT UNIT PLAN VWORLD FEATURE IDENTITY PROBE")
    print("=" * 72)
    print(f"Dataset: {DATASET}")
    print(f"Diagnostic PNU: {pnu}")
    print(f"Point (EPSG:4326): {point_wkt}")
    print("PNU is not sent as attrFilter.")
    print("Purpose: inspect raw feature properties; no truth/promotion decision")

    try:
        response = requests.get(VWORLD_DATA_URL, params=params, timeout=30)
    except requests.RequestException as exc:
        print(f"REQUEST_ERROR: {exc}")
        sys.exit(3)

    print(f"HTTP status: {response.status_code}")
    if response.status_code != 200:
        print("HTTP_ERROR: VWorld request did not return 200.")
        sys.exit(4)

    try:
        payload = response.json()
    except ValueError:
        print("JSON_ERROR: response was not valid JSON.")
        sys.exit(5)

    response_block = payload.get("response") if isinstance(payload, Mapping) else None
    if not isinstance(response_block, Mapping):
        print("SCHEMA_ERROR: missing response object.")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])
        sys.exit(6)

    status = response_block.get("status")
    print(f"VWorld status: {status}")
    if status != "OK":
        error = response_block.get("error")
        print("VWORLD_NON_OK:")
        print(json.dumps(error, ensure_ascii=False, indent=2))
        print("No FALSE/current-validity inference is allowed from this result.")
        sys.exit(7)

    result = response_block.get("result")
    feature_collection = result.get("featureCollection") if isinstance(result, Mapping) else None
    features = feature_collection.get("features") if isinstance(feature_collection, Mapping) else None
    if not isinstance(features, list):
        features = []

    print(f"Feature count: {len(features)}")
    if not features:
        print("NO_FEATURES: no feature intersecting the probe point was returned.")
        print("This is diagnostic absence only; it is not SITE FALSE evidence.")
        return

    for index, feature in enumerate(features, start=1):
        properties = feature.get("properties") if isinstance(feature, Mapping) else None
        properties = dict(properties) if isinstance(properties, Mapping) else {}
        geometry = feature.get("geometry") if isinstance(feature, Mapping) else None

        print("-" * 72)
        print(f"FEATURE {index}")
        print("Candidate identity fields:")
        print(
            json.dumps(
                _candidate_identity_fields(properties),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        print("Raw property keys:")
        print(json.dumps(sorted(str(key) for key in properties), ensure_ascii=False, indent=2))
        print("Raw properties:")
        print(json.dumps(properties, ensure_ascii=False, indent=2, default=str))
        print("Returned geometry type:")
        geometry_type = geometry.get("type") if isinstance(geometry, Mapping) else None
        print(json.dumps(geometry_type, ensure_ascii=False))

    print("=" * 72)
    print("PROBE_COMPLETE")
    print("Do not infer ntfc_sn or any other VWorld field equals ANCMNT_NO without separate verification.")


if __name__ == "__main__":
    main()
