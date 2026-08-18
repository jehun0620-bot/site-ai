from dataclasses import dataclass
from typing import Optional


@dataclass
class Regulation:
    """
    법규 정보를 저장하는 데이터 모델.

    현재 단계에서는 실제 법정 수치를
    임의로 입력하지 않는다.
    """

    zoning: str

    building_coverage_ratio: Optional[float] = None
    floor_area_ratio: Optional[float] = None
    height_limit: Optional[float] = None

    use_restriction: Optional[str] = None

    source: Optional[str] = None
    legal_basis: Optional[str] = None

    priority: Optional[int] = None