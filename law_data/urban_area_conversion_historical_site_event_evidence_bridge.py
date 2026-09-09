from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from law_data.urban_area_conversion_historical_site_event_shadow_adapter import (
    adapt_urban_area_conversion_history_shadow,
    extract_checks,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_EVIDENCE_PATH = (
    BASE_DIR / "law_data" / "output" / "urban_area_conversion_history_resolution.json"
)

BRIDGE_MODE = "READ_ONLY_EVIDENCE_BRIDGE"
INPUT_OK = "OK"
INPUT_FILE_MISSING = "FILE_MISSING"
INPUT_INVALID_JSON = "INVALID_JSON"
INPUT_INVALID_ROOT = "INVALID_ROOT"
INPUT_CHECKS_MISSING = "CHECKS_MISSING"


def _fail_closed_payload() -> dict[str, Any]:
    return {}


def bridge_payload(
    payload: Mapping[str, Any] | None,
    *,
    input_status: str = INPUT_OK,
    source_path: str = "",
) -> dict[str, Any]:
    """Pass an already loaded history payload through the shadow adapter.

    The bridge never upgrades legacy negative evidence into global history
    completeness. Missing or malformed input is represented by an empty payload,
    which the shadow adapter resolves fail-closed to UNKNOWN.
    """

    normalized_payload: Mapping[str, Any]
    if isinstance(payload, Mapping):
        normalized_payload = payload
    else:
        normalized_payload = _fail_closed_payload()
        if input_status == INPUT_OK:
            input_status = INPUT_INVALID_ROOT

    checks = extract_checks(normalized_payload)
    if input_status == INPUT_OK and not checks:
        input_status = INPUT_CHECKS_MISSING

    shadow = adapt_urban_area_conversion_history_shadow(normalized_payload)

    return {
        "bridge_mode": BRIDGE_MODE,
        "input_status": input_status,
        "source_path": source_path,
        "checks_present": bool(checks),
        "shadow": shadow,
        "generalized_resolution": shadow["generalized_resolution"]["resolution"],
        "global_history_completeness_promoted": False,
        "legacy_false_eligibility_promoted": False,
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }


def load_evidence_bridge(
    path: Path | str = DEFAULT_EVIDENCE_PATH,
) -> dict[str, Any]:
    """Read the integrated history evidence JSON without modifying any output.

    File absence, malformed JSON, non-object roots, and missing checks all fail
    closed through the generalized shadow adapter. No exception from those input
    states is converted into FALSE or legal absence.
    """

    evidence_path = Path(path)
    source_path = str(evidence_path)

    if not evidence_path.exists():
        return bridge_payload(
            _fail_closed_payload(),
            input_status=INPUT_FILE_MISSING,
            source_path=source_path,
        )

    try:
        with evidence_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return bridge_payload(
            _fail_closed_payload(),
            input_status=INPUT_INVALID_JSON,
            source_path=source_path,
        )

    if not isinstance(payload, dict):
        return bridge_payload(
            _fail_closed_payload(),
            input_status=INPUT_INVALID_ROOT,
            source_path=source_path,
        )

    return bridge_payload(
        payload,
        input_status=INPUT_OK,
        source_path=source_path,
    )
