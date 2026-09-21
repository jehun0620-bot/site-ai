# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
VWORLD_DATA_URL = "https://api.vworld.kr/req/data"
REQUEST_TIMEOUT = 30


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def load_vworld_api_key() -> str:
    load_dotenv(BASE_DIR / ".env")
    return (os.getenv("VWORLD_API_KEY") or os.getenv("VWORLD_KEY") or "").strip()


def collect_features(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    candidates: List[Any] = []
    response = _safe_dict(payload.get("response"))
    result = _safe_dict(response.get("result"))
    feature_collection = result.get("featureCollection")

    if isinstance(feature_collection, dict):
        candidates.extend(_safe_list(feature_collection.get("features")))
    elif isinstance(feature_collection, list):
        for item in feature_collection:
            if isinstance(item, dict):
                candidates.extend(_safe_list(item.get("features")))

    candidates.extend(_safe_list(payload.get("features")))
    return [feature for feature in candidates if isinstance(feature, dict)]


def get_vworld_status(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    return _safe_dict(payload.get("response")).get("status")


def get_vworld_error(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return _safe_dict(_safe_dict(payload.get("response")).get("error"))


def query_spatial_dataset(
    *,
    dataset: str,
    api_key: str,
    x: float,
    y: float,
) -> Dict[str, Any]:
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": dataset,
        "key": api_key,
        "format": "json",
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
        "geomFilter": f"POINT({x} {y})",
        "size": 100,
        "page": 1,
    }
    request_info = {"dataset": dataset, "x": x, "y": y, "crs": "EPSG:4326"}

    try:
        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return {
            "http_status": None,
            "vworld_status": None,
            "classification": "TRANSPORT_ERROR",
            "transport_error": repr(exc),
            "feature_count": 0,
            "features": [],
            "request": request_info,
        }

    try:
        payload = response.json()
    except Exception as exc:
        return {
            "http_status": response.status_code,
            "vworld_status": None,
            "classification": "JSON_PARSE_ERROR",
            "transport_error": None,
            "json_error": repr(exc),
            "feature_count": 0,
            "features": [],
            "request": request_info,
        }

    status = get_vworld_status(payload)
    features = collect_features(payload)

    if response.status_code != 200:
        classification = "HTTP_ERROR"
    elif status == "OK":
        classification = "QUERY_SUCCESS"
    elif status == "NOT_FOUND" and not features:
        classification = "QUERY_EMPTY"
    else:
        classification = "QUERY_FAILED"

    return {
        "http_status": response.status_code,
        "vworld_status": status,
        "classification": classification,
        "transport_error": None,
        "error": get_vworld_error(payload),
        "feature_count": len(features),
        "features": features,
        "request": request_info,
    }
