from __future__ import annotations

from unittest.mock import patch

from site_data.production_legal_scope_guard import (
    UnsupportedLegalJurisdictionError,
    require_supported_legal_jurisdiction,
)
from site_data.site_analysis_orchestrator import analyze_site_by_parcel

SEOUL_PNU = "1168010300100120002"
BUSAN_PNU = "2635010500105240002"


class ProviderReached(RuntimeError):
    pass


def main() -> None:
    assert require_supported_legal_jurisdiction(SEOUL_PNU) == SEOUL_PNU

    for pnu in (BUSAN_PNU, "4168010300100120002"):
        try:
            require_supported_legal_jurisdiction(pnu)
        except UnsupportedLegalJurisdictionError:
            pass
        else:
            raise AssertionError(f"Unsupported region must fail closed: {pnu}")

    for pnu in ("", "116801030010012000", "1168010300300120002", "abcdefghij100120002"):
        try:
            require_supported_legal_jurisdiction(pnu)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid PNU must be rejected: {pnu}")

    # Unsupported region must stop BEFORE any external BuildingHUB call.
    with patch("site_data.site_analysis_orchestrator.fetch_building_items") as fetch:
        try:
            analyze_site_by_parcel(
                sigungu_cd="26350", bjdong_cd="10500", plat_gb_cd="0",
                bun="0524", ji="0002",
            )
        except UnsupportedLegalJurisdictionError:
            pass
        else:
            raise AssertionError("Busan must not enter the Seoul-only engine")
        fetch.assert_not_called()

    # Positive control: valid Seoul input passes the jurisdiction gate and
    # reaches the NEXT boundary. No real provider call is performed.
    with patch(
        "site_data.site_analysis_orchestrator.fetch_building_items",
        side_effect=ProviderReached("SEOUl_SCOPE_ADMITTED"),
    ) as fetch:
        try:
            analyze_site_by_parcel(
                sigungu_cd="11680", bjdong_cd="10300", plat_gb_cd="0",
                bun="0012", ji="0002",
            )
        except ProviderReached:
            pass
        else:
            raise AssertionError("Seoul positive control did not reach provider boundary")
        fetch.assert_called_once()

    print("PRODUCTION_LEGAL_SCOPE_GUARD_CONTRACT_PASS")


if __name__ == "__main__":
    main()
