from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CongestionLevel(str, Enum):
    FREE_FLOW = "free_flow"
    MODERATE = "moderate"
    HEAVY = "heavy"
    SEVERE = "severe"


class TrafficObservation(BaseModel):
    road_id: str = Field(..., min_length=1, description="Unique road segment identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    vehicle_count: int = Field(..., ge=0, description="Observed vehicles on segment")
    average_speed_kmph: float = Field(..., ge=0.0, description="Average estimated vehicle speed")
    occupancy_ratio: Optional[float] = Field(None, ge=0.0, le=1.0, description="Lane occupancy percentage")
    source: str = Field(default="cctv_simulation")
    is_simulated: bool = Field(default=True)

    model_config = ConfigDict(from_attributes=True)


class TrafficForecast(BaseModel):
    road_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    current_congestion_level: CongestionLevel
    forecast_15m_level: CongestionLevel
    forecast_30m_level: CongestionLevel
    predicted_speed_15m_kmph: float = Field(..., ge=0.0)
    predicted_speed_30m_kmph: float = Field(..., ge=0.0)
    congestion_weight_multiplier: float = Field(..., ge=1.0, description="Multiplier applied to base road edge weight")
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_simulated: bool = Field(default=True)
    limitations_note: Optional[str] = Field(
        default="Simulated forecast baseline generated from historical diurnal traffic cycles."
    )

    model_config = ConfigDict(from_attributes=True)
