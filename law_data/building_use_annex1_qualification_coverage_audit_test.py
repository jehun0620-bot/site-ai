# -*- coding: utf-8 -*-
"""Read-only coverage audit for Annex 1 canonical candidate qualifications.

This test derives its inventory from the production canonical catalog and
qualification registry. It does not infer missing legal qualifications and
does not change production data.
"""

from __future__ import annotations

from collections import defaultdict

from law_data.building_use_annex1_canonical_catalog import build_canonical_catalog
from law_data.building_use_annex1_qualification_registry import (
    VERIFIED_CANONICAL_QUALIFICATION_RULES,
    VERIFIED_QUALIFICATION_RULES,
    qualification_rules_for_candidate,
)


def main() -> None:
    catalog = build_canonical_catalog()
    assert catalog

    by_name = defaultdict(list)
    for entry in catalog:
        by_name[entry.canonical_name].append(entry)

    unique_names = tuple(sorted(by_name))
    single_names = tuple(name for name in unique_names if len(by_name[name]) == 1)
    multi_names = tuple(name for name in unique_names if len(by_name[name]) > 1)

    multi_rows = []
    fully_registered_multi = []
    partially_registered_multi = []
    unregistered_multi = []

    for name in multi_names:
        candidates = []
        registered_count = 0
        for entry in by_name[name]:
            rules = qualification_rules_for_candidate(
                entry.source_path,
                entry.canonical_name,
            )
            status = "VERIFIED" if rules else "UNREGISTERED"
            if rules:
                registered_count += 1
            candidates.append(
                (
                    entry.source_path.key,
                    entry.major_use,
                    status,
                    len(rules),
                )
            )

        if registered_count == len(candidates):
            coverage = "FULLY_REGISTERED"
            fully_registered_multi.append(name)
        elif registered_count == 0:
            coverage = "UNREGISTERED"
            unregistered_multi.append(name)
        else:
            coverage = "PARTIALLY_REGISTERED"
            partially_registered_multi.append(name)

        multi_rows.append((name, coverage, tuple(candidates)))

    assert len(catalog) == 225
    assert len(unique_names) == 190
    assert len(multi_names) == 31
    assert len(single_names) == 159
    assert len(VERIFIED_QUALIFICATION_RULES) == 31
    assert len(VERIFIED_CANONICAL_QUALIFICATION_RULES) == 1

    print("RESULT: PASS")
    print("Catalog entry count:", len(catalog))
    print("Unique canonical name count:", len(unique_names))
    print("Single-candidate canonical name count:", len(single_names))
    print("Multi-candidate canonical name count:", len(multi_names))
    print("SourcePath qualification rule count:", len(VERIFIED_QUALIFICATION_RULES))
    print(
        "Canonical-specific qualification rule count:",
        len(VERIFIED_CANONICAL_QUALIFICATION_RULES),
    )
    print("Fully registered multi-candidate count:", len(fully_registered_multi))
    print("Partially registered multi-candidate count:", len(partially_registered_multi))
    print("Unregistered multi-candidate count:", len(unregistered_multi))

    print("\nMULTI-CANDIDATE COVERAGE")
    for name, coverage, candidates in multi_rows:
        print(f"- {name}: {coverage}")
        for source_path, major_use, status, rule_count in candidates:
            print(
                f"  {source_path} | {major_use} | {status} | "
                f"qualification_rules={rule_count}"
            )

    print("\nPARTIALLY REGISTERED MULTI-CANDIDATE NAMES")
    print(tuple(partially_registered_multi))
    print("\nUNREGISTERED MULTI-CANDIDATE NAMES")
    print(tuple(unregistered_multi))
    print(
        "\nNot proven: candidate-set legal completeness, final classification, "
        "missing qualification meaning, frontend integration, PROJECT mapping, "
        "or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
