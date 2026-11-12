from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.traffic import CongestionLevel


class SignalState(str, Enum):
    NORMAL = "normal"
    PRIORITY_GREEN = "priority_green"
    CAUTION_FLASHING = "caution_flashing"


class IntersectionNode(BaseModel):
    node_id: str = Field(..., description="Unique intersection node ID e.g., NODE-01")
    name: str = Field(..., description="Descriptive label e.g., Main & 4th Ave")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    is_signalized: bool = True
    signal_state: SignalState = SignalState.NORMAL

    model_config = ConfigDict(from_attributes=True)


class RoadSegment(BaseModel):
    road_id: str = Field(..., description="Unique road segment identifier e.g., ROAD-01")
    name: str = Field(..., description="Road name e.g., Broadway St")
    source_node: str = Field(..., description="Origin intersection node ID")
    target_node: str = Field(..., description="Destination intersection node ID")
    length_meters: float = Field(..., gt=0.0)
    speed_limit_kmph: float = Field(default=50.0, gt=0.0)
    base_travel_time_seconds: int = Field(..., gt=0)
    current_congestion_level: CongestionLevel = CongestionLevel.FREE_FLOW
    congestion_weight_multiplier: float = Field(default=1.0, ge=1.0)
    is_blocked: bool = False
    is_diverted: bool = False

    model_config = ConfigDict(from_attributes=True)


class CityGraph(BaseModel):
    city_name: str = "Metropolis SmartGrid"
    nodes: List[IntersectionNode]
    edges: List[RoadSegment]

    model_config = ConfigDict(from_attributes=True)
