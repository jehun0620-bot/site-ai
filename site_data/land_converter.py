from datetime import datetime
from typing import Any, Dict, List, Optional

from .site_data_model import Land

def select_latest_land_record(
    records: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    동일 PNU에 대해 여러 토지특성정보가 반환될 경우
    lastUpdtDt가 가장 최신인 데이터를 선택한다.
    """

    if not records:
        return None

    def get_update_date(record: Dict[str, Any]) -> datetime:
        date_text = record.get("lastUpdtDt", "")

        try:
            return datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            return datetime.min

    return max(records, key=get_update_date)


def convert_land_record(record: Dict[str, Any]) -> Land:
    """
    VWorld 토지특성정보 1건을
    우리 시스템의 Land 객체로 변환한다.
    """

    return Land(
        land_area=float(record.get("lndpclAr", 0) or 0),

        land_category=record.get(
            "lndcgrCodeNm",
            ""
        ),

        zoning=record.get(
            "prposArea1Nm",
            ""
        ),

        district="",

        land_use_regulation=""
    )