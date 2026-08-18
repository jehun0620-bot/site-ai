import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# 1. 프로젝트 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# 2. .env 파일 불러오기
# ============================================================

load_dotenv(BASE_DIR / ".env")


# ============================================================
# 3. VWorld API 인증키
# ============================================================

VWORLD_API_KEY = os.getenv("VWORLD_API_KEY")


# ============================================================
# 4. VWorld 토지특성정보 API
# ============================================================

API_URL = (
    "https://api.vworld.kr/ned/data/"
    "getLandCharacteristics"
)


def create_pnu(
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
) -> str:
    """
    시군구코드, 법정동코드, 본번, 부번을 이용하여
    19자리 PNU를 생성한다.

    일반 토지 기준:
    법정동코드(10자리)
    + 대장구분(1자리)
    + 본번(4자리)
    + 부번(4자리)
    """

    sigungu_cd = str(sigungu_cd or "").strip()
    bjdong_cd = str(bjdong_cd or "").strip()
    bun = str(bun or "").strip()
    ji = str(ji or "").strip()

    bun = bun.zfill(4)
    ji = ji.zfill(4)

    if len(sigungu_cd) != 5:
        raise ValueError(
            f"sigungu_cd는 5자리여야 합니다: {sigungu_cd}"
        )

    if len(bjdong_cd) != 5:
        raise ValueError(
            f"bjdong_cd는 5자리여야 합니다: {bjdong_cd}"
        )

    pnu = (
        sigungu_cd
        + bjdong_cd
        + "1"
        + bun
        + ji
    )

    return pnu


def get_land_characteristics(
    pnu: str,
    stdr_year: str = "2024",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> List[Dict[str, Any]]:
    """
    PNU를 이용하여 VWorld 토지특성정보 API를 호출한다.

    반환값:
        토지특성정보 field 목록
    """

    if not VWORLD_API_KEY:
        raise RuntimeError(
            "VWORLD_API_KEY를 찾을 수 없습니다."
        )

    params = {
        "key": VWORLD_API_KEY,
        "pnu": pnu,
        "stdrYear": stdr_year,
        "format": "json",
        "numOfRows": str(num_of_rows),
        "pageNo": str(page_no),
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=30,
        )

    except requests.RequestException as e:
        raise RuntimeError(
            f"VWorld API 요청 중 오류가 발생했습니다: {e}"
        ) from e

    if response.status_code != 200:
        raise RuntimeError(
            f"VWorld API HTTP 오류: "
            f"{response.status_code}"
        )

    try:
        data = response.json()

    except ValueError as e:
        raise RuntimeError(
            "VWorld API 응답을 JSON으로 변환할 수 없습니다."
        ) from e

    try:
        records = data[
            "landCharacteristicss"
        ]["field"]

    except (KeyError, TypeError) as e:
        raise RuntimeError(
            "VWorld API 응답에서 "
            "landCharacteristicss.field를 찾을 수 없습니다."
        ) from e

    if not isinstance(records, list):
        raise RuntimeError(
            "VWorld API의 field 데이터가 "
            "목록 형식이 아닙니다."
        )

    return records