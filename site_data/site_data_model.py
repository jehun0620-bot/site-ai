from dataclasses import dataclass, field
from typing import List, Optional

from .regulation_model import Regulation

@dataclass
class Building:
    """
    우리 시스템에서 사용하는 하나의 건축물 데이터
    """

    building_id: Optional[str] = None
    management_id: Optional[int] = None

    dong_name: str = ""
    building_name: str = ""

    main_use: str = ""

    land_area: float = 0.0
    building_area: float = 0.0
    total_floor_area: float = 0.0

    building_coverage_ratio: float = 0.0
    floor_area_ratio: float = 0.0

    ground_floor_count: int = 0
    underground_floor_count: int = 0

    household_count: int = 0

    approval_date: str = ""


@dataclass
class Land:
    """
    우리 시스템에서 사용하는 하나의 토지 데이터
    """

    land_area: float = 0.0

    land_category: str = ""

    zoning: str = ""

    district: str = ""

    land_use_regulation: str = ""


@dataclass
class Site:
    """
    우리 시스템에서 사용하는 하나의 대지 데이터
    """

    site_id: str = ""

    address: str = ""
    road_address: str = ""

    sigungu_cd: str = ""
    bjdong_cd: str = ""
    bun: str = ""
    ji: str = ""

    land: Optional[Land] = None

    regulation: Optional[Regulation] = None

    buildings: List[Building] = field(default_factory=list)