# -*- coding: utf-8 -*-
"""Validated public fact input boundary for SITE analysis."""

from __future__ import annotations

from typing import Any, Mapping

from law_data.building_use_annex1_final_classifier import classify_building_use
from law_data.building_use_fact import building_use_fact_from_final


def build_public_fact_context(
    *,
    building_use_name: str | None = None,
    numeric_facts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build fail-closed Rule Engine facts from public API inputs."""

    context: dict[str, Any] = {}

    for raw_name, raw_fact in (numeric_facts or {}).items():
        name = str(raw_name or "").strip()
        if not name or not isinstance(raw_fact, Mapping):
            continue

        value = raw_fact.get("value")
        unit = str(raw_fact.get("unit") or "").strip()

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not unit:
            continue

        context[name] = {
            "value": value,
            "unit": unit,
        }

    canonical_name = str(building_use_name or "").strip()
    if canonical_name:
        final = classify_building_use(
            canonical_name,
            context,
        )
        fact = building_use_fact_from_final(final)
        if fact is not None:
            context["building_use"] = {
                "canonical_name": fact.canonical_name,
                "major_use": fact.major_use,
                "source_path": fact.source_path,
                "classification_status": fact.classification_status,
            }

    return context
