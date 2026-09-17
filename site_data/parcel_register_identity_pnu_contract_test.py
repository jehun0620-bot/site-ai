from site_data.site_data_model import Site
from site_data.site_analysis_service import site_to_analysis_input
from site_data.vworld_api import create_pnu


def main():
    ordinary = create_pnu("11680", "10300", "0012", "0000", "0")
    assert ordinary == "1168010300100120000", ordinary

    mountain = create_pnu("11590", "10600", "0029", "0003", "1")
    assert mountain == "1159010600200290003", mountain

    site = Site(
        sigungu_cd="11590",
        bjdong_cd="10600",
        plat_gb_cd="1",
        bun="0029",
        ji="0003",
    )
    analysis_input = site_to_analysis_input(site)
    assert analysis_input["pnu"] == mountain
    assert analysis_input["plat_gb_cd"] == "1"

    for invalid in ("", "2", "x"):
        try:
            create_pnu("11590", "10600", "0029", "0003", invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid plat_gb_cd accepted: {invalid!r}")

    invalid_site = Site(
        sigungu_cd="11590",
        bjdong_cd="10600",
        plat_gb_cd="2",
        bun="0029",
        ji="0003",
    )
    assert site_to_analysis_input(invalid_site)["pnu"] == ""

    print("PARCEL_REGISTER_IDENTITY_PNU_CONTRACT_PASS")


if __name__ == "__main__":
    main()
