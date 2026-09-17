# -*- coding: utf-8 -*-
"""Contract for the public API parcel-register identity boundary."""
from unittest.mock import patch
from pydantic import ValidationError
from api_app import SiteAnalysisRequest, site_analysis


def main():
    ordinary=SiteAnalysisRequest(sigungu_cd="11680",bjdong_cd="10300",bun="0012",ji="0000")
    assert ordinary.plat_gb_cd=="0"

    mountain=SiteAnalysisRequest(sigungu_cd="11590",bjdong_cd="10600",plat_gb_cd="1",bun="0029",ji="0003")
    assert mountain.plat_gb_cd=="1"

    for invalid in ("", "2", "x"):
        try:
            SiteAnalysisRequest(sigungu_cd="11590",bjdong_cd="10600",plat_gb_cd=invalid,bun="0029",ji="0003")
        except ValidationError:
            pass
        else:
            raise AssertionError(f"invalid plat_gb_cd admitted: {invalid!r}")

    captured={}
    def fake_analyze_site_by_parcel(**kwargs):
        captured.update(kwargs)
        return {"ok":True}

    with patch("api_app.analyze_site_by_parcel",side_effect=fake_analyze_site_by_parcel):
        result=site_analysis(mountain)
    assert result=={"ok":True}
    assert captured["sigungu_cd"]=="11590"
    assert captured["bjdong_cd"]=="10600"
    assert captured["plat_gb_cd"]=="1"
    assert captured["bun"]=="0029"
    assert captured["ji"]=="0003"

    print("PUBLIC_API_PARCEL_REGISTER_IDENTITY_CONTRACT_PASS")

if __name__=="__main__": main()
