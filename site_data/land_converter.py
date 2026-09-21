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

def hydrate_land_from_records(
    records: List[Dict[str, Any]],
    *,
    reference_year: str,
) -> tuple[Optional[Land], Optional[Dict[str, Any]]]:
    """Convert the newest VWorld record into Land and preserve provenance."""
    record = select_latest_land_record(records)
    if record is None:
        return None, None

    land = convert_land_record(record)
    land.source_reference_year = str(reference_year).strip() or None
    land.source_last_updated_at = str(record.get("lastUpdtDt") or "").strip() or None
    return land, record
