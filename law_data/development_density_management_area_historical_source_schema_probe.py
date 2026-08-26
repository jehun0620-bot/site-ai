# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_historical_official_source_expansion.json"
)


def summarize(
    value: Any,
    path: str = "root",
    depth: int = 0,
    max_depth: int = 5,
) -> None:

    if depth > max_depth:
        return

    indent = "  " * depth

    if isinstance(value, dict):

        print(
            f"{indent}{path}: dict ({len(value)} keys)"
        )

        for key, child in value.items():

            child_path = f"{path}.{key}"

            if isinstance(child, dict):

                print(
                    f"{indent}  {key}: dict ({len(child)} keys)"
                )

                summarize(
                    child,
                    child_path,
                    depth + 1,
                    max_depth,
                )

            elif isinstance(child, list):

                print(
                    f"{indent}  {key}: list ({len(child)} items)"
                )

                if child:

                    first = child[0]

                    if isinstance(first, dict):

                        print(
                            f"{indent}    first item keys:"
                        )

                        for first_key in first.keys():

                            print(
                                f"{indent}      - {first_key}"
                            )

                    else:

                        print(
                            f"{indent}    first item:"
                            f" {repr(first)[:300]}"
                        )

                    summarize(
                        child[:2],
                        child_path,
                        depth + 1,
                        max_depth,
                    )

            else:

                preview = repr(child)

                if len(preview) > 300:
                    preview = preview[:300] + "..."

                print(
                    f"{indent}  {key}: {preview}"
                )

    elif isinstance(value, list):

        print(
            f"{indent}{path}: list ({len(value)} items)"
        )

        for index, child in enumerate(value[:2]):

            child_path = f"{path}[{index}]"

            summarize(
                child,
                child_path,
                depth + 1,
                max_depth,
            )


def find_interesting_nodes(
    value: Any,
    path: str = "root",
) -> None:

    if isinstance(value, dict):

        keys = {
            str(key).lower()
            for key in value.keys()
        }

        interesting = any(
            term in key
            for key in keys
            for term in [
                "source",
                "target",
                "pool",
                "family",
                "url",
                "endpoint",
            ]
        )

        if interesting:

            print()
            print("-" * 70)
            print("PATH:", path)
            print("KEYS:", list(value.keys()))

            for key, child in value.items():

                key_lower = str(key).lower()

                if any(
                    term in key_lower
                    for term in [
                        "source",
                        "target",
                        "pool",
                        "family",
                        "url",
                        "endpoint",
                        "name",
                        "class",
                        "strategy",
                        "priority",
                    ]
                ):

                    preview = repr(child)

                    if len(preview) > 1000:
                        preview = preview[:1000] + "..."

                    print(
                        f"{key}: {preview}"
                    )

        for key, child in value.items():

            find_interesting_nodes(
                child,
                f"{path}.{key}",
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):

            find_interesting_nodes(
                child,
                f"{path}[{index}]",
            )


def main() -> None:

    print("=" * 70)
    print("HISTORICAL SOURCE SCHEMA PROBE")
    print("=" * 70)

    print()
    print("Input:", INPUT_PATH)

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            INPUT_PATH
        )

    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    print()
    print("=" * 70)
    print("TOP-LEVEL STRUCTURE")
    print("=" * 70)
    print()

    summarize(
        data,
        max_depth=3,
    )

    print()
    print("=" * 70)
    print("SOURCE/TARGET/POOL/URL NODES")
    print("=" * 70)

    find_interesting_nodes(
        data
    )

    print()
    print("=" * 70)
    print("PROBE COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()