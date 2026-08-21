# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-5
FastAPI HTTP Integration Test
"""

from __future__ import annotations

from fastapi.testclient import (
    TestClient,
)

from api_app import (
    app,
)


client = TestClient(
    app
)


def main() -> int:

    # ========================================================
    # health
    # ========================================================

    health_response = (
        client.get(
            "/health"
        )
    )

    health_json = (
        health_response.json()
    )

    print(
        "Health status:",
        health_response.status_code,
    )

    print(
        "Health:",
        health_json,
    )

    print()

    # ========================================================
    # site analysis
    # ========================================================

    payload = {

        "sigungu_cd": (
            "11680"
        ),

        "bjdong_cd": (
            "10300"
        ),

        "bun": (
            "0012"
        ),

        "ji": (
            "0000"
        ),

        "project_profile": {
            "공동주택": (
                "TRUE"
            ),
        },

        "procedure_profile": {
            "도시계획위원회심의": (
                "TRUE"
            ),
        },

        "include_debug": (
            False
        ),
    }

    response = (
        client.post(
            "/v1/site-analysis",
            json=payload,
        )
    )

    print(
        "Analysis HTTP:",
        response.status_code,
    )

    result = (
        response.json()
    )

    if (
        response.status_code
        != 200
    ):

        print(
            result
        )

        return 1

    # ========================================================
    # console
    # ========================================================

    print(
        "Schema:",
        result.get(
            "schema_version"
        ),
    )

    print(
        "Status:",
        result.get(
            "status"
        ),
    )

    print()

    print(
        "SITE ID:",
        result[
            "site"
        ][
            "site_id"
        ],
    )

    print(
        "Road address:",
        result[
            "site"
        ][
            "road_address"
        ],
    )

    print(
        "PNU:",
        result[
            "site"
        ][
            "pnu"
        ],
    )

    print()

    print(
        "Official area:",
        result[
            "land_area"
        ][
            "official"
        ][
            "value"
        ],
    )

    print()

    print(
        "BCR:",
        result[
            "regulation"
        ][
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "FAR:",
        result[
            "regulation"
        ][
            "floor_area_ratio"
        ][
            "value"
        ],
    )

    print()

    print(
        "Rules:",
        result[
            "rule_evaluation"
        ],
    )

    print()

    print(
        "Building count:",
        result[
            "service"
        ][
            "building_count"
        ],
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "health 200": (
            health_response.status_code
            == 200
        ),

        "health ok": (
            health_json.get(
                "status"
            )
            == "ok"
        ),

        "analysis HTTP 200": (
            response.status_code
            == 200
        ),

        "schema": (
            result.get(
                "schema_version"
            )
            == "SITE_ANALYSIS_API_V1"
        ),

        "ready": (
            result.get(
                "status"
            )
            == "READY"
        ),

        "site": (
            result[
                "site"
            ][
                "site_id"
            ]
            == "11680-10300-0012-0000"
        ),

        "road address": (
            bool(
                result[
                    "site"
                ][
                    "road_address"
                ]
            )
        ),

        "pnu": (
            result[
                "site"
            ][
                "pnu"
            ]
            == "1168010300100120000"
        ),

        "official area": (
            result[
                "land_area"
            ][
                "official"
            ][
                "value"
            ]
            == 121040.4
        ),

        "BCR": (
            result[
                "regulation"
            ][
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR": (
            result[
                "regulation"
            ][
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
        ),

        "rules": (
            result[
                "rule_evaluation"
            ][
                "total"
            ]
            == 314
        ),

        "building count": (
            result[
                "service"
            ][
                "building_count"
            ]
            == 34
        ),

        "debug excluded": (
            "debug"
            not in result
        ),
    }

    all_pass = all(
        validations.values()
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    if not all_pass:

        print()
        print(
            "FAILED:"
        )

        for name, passed in (
            validations.items()
        ):

            if not passed:

                print(
                    "-",
                    name,
                )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )