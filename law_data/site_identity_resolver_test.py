# -*- coding: utf-8 -*-

from site_identity_resolver import (
    resolve_site_identity,
)


def main() -> int:

    result = resolve_site_identity(
        base_site={
            "site_id": (
                "11680-10300-0012-0000"
            ),

            "address": (
                "서울특별시 강남구 개포동 12번지"
            ),

            "zone": (
                "제3종일반주거지역"
            ),
        }
    )

    print(
        "SITE ID:",
        result[
            "site_id"
        ],
    )

    print(
        "Address:",
        result[
            "address"
        ],
    )

    print(
        "Road address:",
        result[
            "road_address"
        ],
    )

    print()

    print(
        "PNU:",
        result[
            "pnu"
        ],
    )

    print(
        "Sigungu:",
        result[
            "sigungu_code"
        ],
    )

    print(
        "Bjdong:",
        result[
            "bjdong_code"
        ],
    )

    print(
        "Main/Sub:",
        (
            result[
                "main_no"
            ],
            result[
                "sub_no"
            ],
        ),
    )

    print()

    print(
        "Coordinate:",
        result[
            "coordinate"
        ],
    )

    print()

    print(
        "Zone:",
        result[
            "zone"
        ],
    )

    print(
        "Identity status:",
        result[
            "identity_status"
        ],
    )

    print(
        "Coordinate status:",
        result[
            "coordinate_status"
        ],
    )

    print()

    print(
        "Parcel reference:",
        result[
            "parcel_reference"
        ],
    )

    validations = {

        "site id": (
            result[
                "site_id"
            ]
            == (
                "11680-10300-0012-0000"
            )
        ),

        "address": (
            result[
                "address"
            ]
            == (
                "서울특별시 강남구 개포동 12번지"
            )
        ),

        "pnu": (
            result[
                "pnu"
            ]
            == (
                "1168010300100120000"
            )
        ),

        "sigungu": (
            result[
                "sigungu_code"
            ]
            == "11680"
        ),

        "bjdong": (
            result[
                "bjdong_code"
            ]
            == "10300"
        ),

        "main": (
            result[
                "main_no"
            ]
            == "0012"
        ),

        "sub": (
            result[
                "sub_no"
            ]
            == "0000"
        ),

        "zone": (
            result[
                "zone"
            ]
            == "제3종일반주거지역"
        ),

        "x": (
            result[
                "coordinate"
            ][
                "x"
            ]
            == (
                127.07539280356858
            )
        ),

        "y": (
            result[
                "coordinate"
            ][
                "y"
            ]
            == (
                37.494197498186885
            )
        ),

        "crs": (
            result[
                "coordinate"
            ][
                "crs"
            ]
            == "EPSG:4326"
        ),

        "identity complete": (
            result[
                "identity_status"
            ]
            == "COMPLETE"
        ),

        "coordinate confirmed": (
            result[
                "coordinate_status"
            ]
            == "CONFIRMED"
        ),

        "parcel dataset": (
            result[
                "parcel_reference"
            ][
                "dataset"
            ]
            == "LP_PA_CBND_BUBUN"
        ),

        "parcel verified": (
            result[
                "parcel_reference"
            ][
                "strict_pnu_verified"
            ]
            is True
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