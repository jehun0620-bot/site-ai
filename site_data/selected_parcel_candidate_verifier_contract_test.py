from __future__ import annotations

from unittest.mock import patch

from site_data.selected_parcel_candidate_verifier import verify_selected_parcel_candidate


PNU = "1168010300100120002"
OTHER_PNU = "1168010300100120003"
X = 127.07662495509604
Y = 37.49629354642009


def _feature(pnu: str):
    return {
        "type": "Feature",
        "properties": {"pnu": pnu},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[127.0, 37.0], [127.1, 37.0], [127.1, 37.1], [127.0, 37.0]]],
        },
    }


def main() -> None:
    with patch(
        "site_data.selected_parcel_candidate_verifier.query_dataset_by_point",
        return_value={"features": [_feature(PNU)]},
    ) as query:
        result = verify_selected_parcel_candidate(PNU, X, Y, api_key="test-key")
        assert result.verified
        assert result.pnu == PNU
        assert result.sigungu_cd == "11680"
        assert result.bjdong_cd == "10300"
        assert result.plat_gb_cd == "0"
        assert result.bun == "0012"
        assert result.ji == "0002"
        assert result.crs == "EPSG:4326"
        query.assert_called_once()

    with patch(
        "site_data.selected_parcel_candidate_verifier.query_dataset_by_point",
        return_value={"features": [_feature(OTHER_PNU)]},
    ):
        result = verify_selected_parcel_candidate(PNU, X, Y, api_key="test-key")
        assert not result.verified
        assert result.resolution == "SELECTED_PNU_POLYGON_MISMATCH"

    with patch("site_data.selected_parcel_candidate_verifier.query_dataset_by_point") as query:
        result = verify_selected_parcel_candidate("123", X, Y, api_key="test-key")
        assert not result.verified
        assert result.resolution == "CANDIDATE_PNU_INVALID"
        query.assert_not_called()

    with patch("site_data.selected_parcel_candidate_verifier.query_dataset_by_point") as query:
        result = verify_selected_parcel_candidate(PNU, 999, Y, api_key="test-key")
        assert not result.verified
        assert result.resolution == "CANDIDATE_POINT_INVALID"
        query.assert_not_called()

    with patch(
        "site_data.selected_parcel_candidate_verifier.query_dataset_by_point",
        return_value={"features": []},
    ):
        result = verify_selected_parcel_candidate(PNU, X, Y, api_key="test-key")
        assert not result.verified
        assert result.resolution == "PARCEL_POLYGON_UNRESOLVED"

    with patch("site_data.selected_parcel_candidate_verifier.load_vworld_key", return_value=""), patch(
        "site_data.selected_parcel_candidate_verifier.query_dataset_by_point"
    ) as query:
        result = verify_selected_parcel_candidate(PNU, X, Y)
        assert not result.verified
        assert result.resolution == "VWORLD_KEY_MISSING"
        query.assert_not_called()

    print("SELECTED_PARCEL_CANDIDATE_VERIFIER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
