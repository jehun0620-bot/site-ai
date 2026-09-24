import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
VWORLD_API_KEY = os.getenv("VWORLD_API_KEY")
API_URL = "https://api.vworld.kr/ned/data/getLandCharacteristics"


class VWorldLandProviderError(RuntimeError):
    """Raised when VWorld land-characteristics lookup fails at the provider boundary."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = bool(retryable)


class VWorldLandNoDataError(RuntimeError):
    """Raised after successful provider calls find no records in the requested year window."""


def create_pnu(
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    plat_gb_cd: str = "0",
) -> str:
    """Create a 19-digit PNU from canonical parcel identity.

    Building HUB platGbCd uses 0 for ordinary parcels and 1 for mountain
    parcels. PNU land-register digits are 1 and 2 respectively.
    """
    sigungu_cd = str(sigungu_cd or "").strip()
    bjdong_cd = str(bjdong_cd or "").strip()
    bun = str(bun or "").strip()
    ji = str(ji or "").strip()
    plat_gb_cd = str(plat_gb_cd or "").strip()

    if len(sigungu_cd) != 5 or not sigungu_cd.isdigit():
        raise ValueError(f"sigungu_cd는 5자리 숫자여야 합니다: {sigungu_cd}")
    if len(bjdong_cd) != 5 or not bjdong_cd.isdigit():
        raise ValueError(f"bjdong_cd는 5자리 숫자여야 합니다: {bjdong_cd}")
    if not bun.isdigit() or len(bun) > 4:
        raise ValueError(f"bun은 4자리 이하 숫자여야 합니다: {bun}")
    if not ji.isdigit() or len(ji) > 4:
        raise ValueError(f"ji는 4자리 이하 숫자여야 합니다: {ji}")

    land_gbn_by_plat_gb_cd = {"0": "1", "1": "2"}
    try:
        land_gbn = land_gbn_by_plat_gb_cd[plat_gb_cd]
    except KeyError as e:
        raise ValueError(
            f"plat_gb_cd는 '0'(일반) 또는 '1'(산)이어야 합니다: {plat_gb_cd}"
        ) from e

    return sigungu_cd + bjdong_cd + land_gbn + bun.zfill(4) + ji.zfill(4)


def get_land_characteristics(
    pnu: str,
    stdr_year: str,
    num_of_rows: int = 10,
    page_no: int = 1,
) -> List[Dict[str, Any]]:
    """PNU를 이용하여 VWorld 토지특성정보 API를 호출한다."""
    if not VWORLD_API_KEY:
        raise VWorldLandProviderError("VWORLD_API_KEY를 찾을 수 없습니다.", retryable=False)

    params = {
        "key": VWORLD_API_KEY,
        "pnu": pnu,
        "stdrYear": stdr_year,
        "format": "json",
        "numOfRows": str(num_of_rows),
        "pageNo": str(page_no),
    }
    try:
        response = requests.get(API_URL, params=params, timeout=30)
    except requests.RequestException as e:
        raise VWorldLandProviderError(f"VWorld API 요청 중 오류가 발생했습니다: {e}", retryable=True) from e
    if response.status_code != 200:
        raise VWorldLandProviderError(\n            f"VWorld API HTTP 오류: {response.status_code}",\n            retryable=response.status_code in {408, 429} or 500 <= response.status_code <= 599,\n        )
    try:
        data = response.json()
    except ValueError as e:
        raise VWorldLandProviderError("VWorld API 응답을 JSON으로 변환할 수 없습니다.", retryable=False) from e
    try:
        records = data["landCharacteristicss"]["field"]
    except (KeyError, TypeError) as e:
        raise RuntimeError(
            "VWorld API 응답에서 landCharacteristicss.field를 찾을 수 없습니다."
        ) from e
    if not isinstance(records, list):
        raise VWorldLandProviderError("VWorld API의 field 데이터가 목록 형식이 아닙니다.", retryable=False)
    return records



def get_latest_land_characteristics(
    pnu: str,
    *,
    start_year: int | None = None,
    lookback_years: int = 5,
    num_of_rows: int = 10,
    page_no: int = 1,
) -> tuple[str, List[Dict[str, Any]]]:
    """Return the newest available VWorld land-characteristics year.

    The search starts at the current calendar year unless start_year is
    explicitly supplied, then moves backward until records are found.
    """
    if lookback_years < 1:
        raise ValueError("lookback_years는 1 이상이어야 합니다.")

    first_year = start_year if start_year is not None else datetime.now().year
    for year in range(first_year, first_year - lookback_years, -1):
        records = get_land_characteristics(
            pnu,
            stdr_year=str(year),
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
        if records:
            return str(year), records

    raise RuntimeError(
        f"VWorld 토지특성정보를 최근 {lookback_years}개 기준연도에서 찾을 수 없습니다: {pnu}"
    )
