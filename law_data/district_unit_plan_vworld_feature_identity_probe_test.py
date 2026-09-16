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
        "name": (
            "uname",
            "name",
            "zonename",
            "e_name",
            "dname",
            "title",
            "nm",
            "zone_name",
            "dan_name",
            "cat_nam",
            "dgm_nm",
            "upj_name",
        ),
        "designation_year": ("dyear",),
        "designation_number": ("dnum",),
        "code": ("ucode", "e_code", "code", "zone_cd", "cd"),
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


def main() -> None:
    """Probe raw VWorld district-unit-plan feature attributes without promoting truth.

    This diagnostic probe only exposes the returned LT_C_UPISUQ161 feature properties
    and highlights possible designation identity fields. It does not assert that
    dyear/dnum correspond to Seoul upisAnnouncement fields and does not grant SITE
    truth, promotion, or production/runtime registration authority.
    """

    load_dotenv(BASE_DIR / ".env")
    service_key = os.getenv("VWORLD_API_KEY") or os.getenv("VWORLD_KEY")
    if not service_key:
        print("ERROR: VWorld API key not found (VWORLD_API_KEY or VWORLD_KEY).")
        sys.exit(2)

    pnu = _text(os.getenv("DISTRICT_UNIT_PLAN_PROBE_PNU")) or DEFAULT_PNU

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": DATASET,
        "key": service_key,
        "domain": "localhost",
        "format": "json",
        "size": "20",
        "attrFilter": f"pnu:=:{pnu}",
        "geometry": "false",
        "attribute": "true",
        "crs": "EPSG:4326",
    }

    print("=" * 72)
    print("DISTRICT UNIT PLAN VWORLD FEATURE IDENTITY PROBE")
    print("=" * 72)
    print(f"Dataset: {DATASET}")
    print(f"PNU: {pnu}")
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
        print("NO_FEATURES: no matching feature returned.")
        print("This is diagnostic absence only; it is not SITE FALSE evidence.")
        return

    for index, feature in enumerate(features, start=1):
        properties = feature.get("properties") if isinstance(feature, Mapping) else None
        properties = dict(properties) if isinstance(properties, Mapping) else {}

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

    print("=" * 72)
    print("PROBE_COMPLETE")
    print("Do not infer dnum == ANCMNT_NO until separately verified against official notice data.")


if __name__ == "__main__":
    main()
