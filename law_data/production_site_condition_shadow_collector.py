from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable, Mapping

from law_data.production_site_condition import ProductionSiteCondition


COLLECTOR_NAME = "PRODUCTION_SITE_CONDITION_SHADOW_COLLECTOR"


def _normalize_contract_entry(entry: Any) -> dict[str, Any] | None:
    """Return a contract dict without inferring or manufacturing legal state."""

    if isinstance(entry, ProductionSiteCondition):
        return entry.to_dict()

    if isinstance(entry, Mapping):
        data = dict(entry)
        name = str(data.get("name") or "").strip()
        condition_type = str(data.get("condition_type") or "").strip().upper()
        resolution_type = str(data.get("resolution_type") or "").strip().upper()
        state = str(data.get("state") or "").strip().upper()

        if not name:
            return None
        if condition_type not in {"SITE", "SITE_HISTORY"}:
            return None
        if resolution_type not in {
            "SNAPSHOT",
            "SPATIAL",
            "HYBRID_SPATIAL_NOTICE",
            "HISTORICAL_SITE_EVENT",
        }:
            return None
        if state not in {"TRUE", "FALSE", "UNKNOWN"}:
            return None

        if condition_type == "SITE_HISTORY" and resolution_type == "SPATIAL":
            return None

        return data

    return None


def collect_production_site_condition_shadows(
    *sources: Any,
) -> dict[str, dict[str, Any]]:
    """Merge already-normalized production condition shadows.

    This collector performs no resolver execution, legal inference, runtime
    registration, SITE overlay, or Rule Engine mutation.

    Duplicate condition names are rejected rather than overwritten so conflicting
    evidence cannot be silently promoted by source order.
    """

    collected: dict[str, dict[str, Any]] = {}

    for source in sources:
        if source is None:
            continue

        if isinstance(source, Mapping):
            entries: Iterable[Any] = source.values()
        elif isinstance(source, (list, tuple)):
            entries = source
        else:
            continue

        for entry in entries:
            normalized = _normalize_contract_entry(entry)
            if normalized is None:
                continue

            name = str(normalized["name"]).strip()
            if name in collected:
                raise ValueError(
                    f"duplicate production condition shadow: {name}"
                )

            collected[name] = dict(normalized)

    return collected
