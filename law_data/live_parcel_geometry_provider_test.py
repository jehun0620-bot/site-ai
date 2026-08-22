# -*- coding: utf-8 -*-

"""
C-14-2 Live Parcel Geometry Provider Test

대상:
서울특별시 강남구 개포동 13번지

PNU:
1168010300100130000
"""

from __future__ import annotations

from law_data.parcel_geometry_provider import (
    resolve_live_parcel_geometry,
)


TARGET_PNU = (
    "1168010300100130000"
)

# 아직 개포동 13번지의 대표 좌표를 확정하지 않았으므로
# 우선 SITE 객체/토지 API에서 확보 가능한 좌표가 필요하다.
#
# 아래 값은 현재 단계에서 직접 넣지 않는다.
# 테스트 실행 전에 실제 좌표를 확인해야 한다.


def main() -> None:

    print(
        "TARGET PNU:",
        TARGET_PNU,
    )

    print()

    print(
        "현재 단계에서는 실제 SITE 좌표를 먼저 확인해야 합니다."
    )

    print(
        "provider import OK"
    )


if __name__ == "__main__":

    main()