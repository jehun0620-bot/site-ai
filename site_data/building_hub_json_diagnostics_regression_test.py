# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-A
Building HUB Non-JSON Diagnostics Regression

목표
======================================================================
site_analysis_orchestrator.fetch_building_items()가
Building HUB로부터 HTTP 200이지만 JSON이 아닌 응답을 받을 경우,

1. BuildingAPIError 발생
2. HTTP status 포함
3. Content-Type 포함
4. response length 포함
5. body preview 포함
6. API key가 오류 메시지에 노출되지 않음

을 검증한다.

중요
======================================================================
실제 Building HUB API를 호출하지 않는다.

requests.get을 임시 FakeResponse로 교체하여
upstream non-JSON 응답을 결정론적으로 재현한다.
"""

from __future__ import annotations

from typing import Any, Dict

from site_data import site_analysis_orchestrator
from site_data.site_analysis_orchestrator import (
    BuildingAPIError,
    fetch_building_items,
)


# ============================================================
# TEST CONSTANTS
# ============================================================

TEST_SERVICE_KEY = (
    "TEST_SECRET_BUILDING_API_KEY"
)

TEST_BODY = (
    "<html>"
    "<head><title>Temporary Error</title></head>"
    "<body>"
    "Building HUB upstream temporary non-json response"
    "</body>"
    "</html>"
)

TEST_CONTENT_TYPE = (
    "text/html; charset=UTF-8"
)


# ============================================================
# FAKE RESPONSE
# ============================================================

class FakeResponse:

    def __init__(
        self,
    ) -> None:

        self.status_code = (
            200
        )

        self.headers: Dict[
            str,
            str
        ] = {
            "Content-Type":
                TEST_CONTENT_TYPE,
        }

        self.text = (
            TEST_BODY
        )

    def json(
        self,
    ) -> Any:

        raise ValueError(
            "fake non-json response"
        )


# ============================================================
# FAKE REQUEST
# ============================================================

captured_request: Dict[
    str,
    Any
] = {}


def fake_requests_get(
    url: str,
    *,
    params: Dict[str, Any],
    timeout: int,
) -> FakeResponse:

    captured_request[
        "url"
    ] = (
        url
    )

    captured_request[
        "params"
    ] = (
        dict(
            params
        )
    )

    captured_request[
        "timeout"
    ] = (
        timeout
    )

    return FakeResponse()


# ============================================================
# RUN
# ============================================================

original_requests_get = (
    site_analysis_orchestrator
    .requests
    .get
)


error_message = None

error_type = None


try:

    site_analysis_orchestrator.requests.get = (
        fake_requests_get
    )

    fetch_building_items(
        sigungu_cd=(
            "11680"
        ),
        bjdong_cd=(
            "10300"
        ),
        bun=(
            "0012"
        ),
        ji=(
            "0000"
        ),
        service_key=(
            TEST_SERVICE_KEY
        ),
        timeout=(
            30
        ),
    )

except BuildingAPIError as exc:

    error_type = (
        type(
            exc
        ).__name__
    )

    error_message = (
        str(
            exc
        )
    )

finally:

    site_analysis_orchestrator.requests.get = (
        original_requests_get
    )


# ============================================================
# CONSOLE
# ============================================================

print(
    "============================================================"
)

print(
    "BUILDING HUB NON-JSON DIAGNOSTICS"
)

print(
    "============================================================"
)

print(
    "Error type:",
    error_type,
)

print(
    "Error message:",
    error_message,
)

print()

print(
    "Captured URL:",
    captured_request.get(
        "url"
    ),
)

print(
    "Captured timeout:",
    captured_request.get(
        "timeout"
    ),
)

print(
    "Captured request keys:",
    sorted(
        captured_request.get(
            "params",
            {},
        ).keys()
    ),
)


# ============================================================
# VALIDATION
# ============================================================

message = (
    error_message
    or ""
)

captured_params = (
    captured_request.get(
        "params",
        {},
    )
)


validations = {

    # --------------------------------------------------------
    # exception
    # --------------------------------------------------------

    "BuildingAPIError raised": (
        error_type
        == "BuildingAPIError"
    ),

    "JSON parsing failure message": (
        "건축HUB 응답 JSON 파싱 실패"
        in message
    ),

    # --------------------------------------------------------
    # diagnostics
    # --------------------------------------------------------

    "HTTP diagnostic": (
        "HTTP=200"
        in message
    ),

    "Content-Type diagnostic": (
        (
            "Content-Type="
            + TEST_CONTENT_TYPE
        )
        in message
    ),

    "Length diagnostic": (
        (
            "Length="
            + str(
                len(
                    TEST_BODY
                )
            )
        )
        in message
    ),

    "Preview diagnostic": (
        "Building HUB upstream temporary non-json response"
        in message
    ),

    # --------------------------------------------------------
    # secret safety
    # --------------------------------------------------------

    "API key not leaked": (
        TEST_SERVICE_KEY
        not in message
    ),

    # --------------------------------------------------------
    # request preservation
    # --------------------------------------------------------

    "Building HUB URL preserved": (
        captured_request.get(
            "url"
        )
        == (
            site_analysis_orchestrator
            .BUILDING_API_URL
        )
    ),

    "timeout preserved": (
        captured_request.get(
            "timeout"
        )
        == 30
    ),

    "service key sent to upstream": (
        captured_params.get(
            "serviceKey"
        )
        == TEST_SERVICE_KEY
    ),

    "JSON request preserved": (
        captured_params.get(
            "_type"
        )
        == "json"
    ),

    "parcel identifiers preserved": (
        (
            captured_params.get(
                "sigunguCd"
            ),
            captured_params.get(
                "bjdongCd"
            ),
            captured_params.get(
                "bun"
            ),
            captured_params.get(
                "ji"
            ),
        )
        == (
            "11680",
            "10300",
            "0012",
            "0000",
        )
    ),
}


# ============================================================
# OUTPUT
# ============================================================

print()

print(
    "============================================================"
)

print(
    "VALIDATION"
)

print(
    "============================================================"
)


for name, passed in (
    validations.items()
):

    print(
        f"{name}:",
        passed,
    )


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


raise SystemExit(
    0
    if all_pass
    else 1
)