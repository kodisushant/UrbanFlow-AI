"""
UrbanFlow AI - Traffic Intelligence Data Models
Defines Pydantic schemas for CCTV observations, traffic metrics,
15-30 minute forecasts, and routing metadata for Members 1 and 4.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class CongestionLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HEAVY = "heavy"
    SEVERE = "severe"


class CCTVObservation(BaseModel):
    """Input observation from Member 2 (Computer Vision / CCTV) or simulator."""
    source_id: str = Field(..., description="Camera ID or simulator source ID, e.g. 'cctv_cam_01'")
    road_id: str = Field(..., description="Road segment identifier matching road network, e.g. 'ROAD-01'")
    intersection_id: Optional[str] = Field(None, description="Nearby intersection ID, if applicable, e.g. 'INT-01'")
    timestamp: datetime = Field(..., description="Timestamp of observation (aware or naive)")
    vehicle_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown by vehicle class, e.g. {'car': 12, 'motorcycle': 4, 'bus': 1, 'truck': 1}"
    )
    total_vehicles: int = Field(..., ge=0, description="Total count of detected vehicles")
    passenger_car_units: Optional[float] = Field(
        None, ge=0.0, description="Weighted volume (PCU). If not provided, computed from vehicle_counts"
    )
    estimated_speed_kmph: Optional[float] = Field(
        None, ge=0.0, description="Estimated average speed in km/h from optical tracking (can be 0.0 for dead stop)"
    )
    stopped_vehicles_count: int = Field(
        0, ge=0, description="Number of stationary / stopped vehicles detected in the frame"
    )
    lane_occupancy_ratio: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Estimated visual occupancy ratio of the road lanes [0.0 - 1.0]"
    )
    is_simulated: bool = Field(False, description="Whether this observation originates from a simulator")


class CurrentTrafficState(BaseModel):
    """Calculated real-time traffic status for a road segment or intersection."""
    road_id: str
    intersection_id: Optional[str] = Field(None, description="Intersection ID if applicable")
    timestamp: datetime
    vehicle_count: int
    passenger_car_units: float
    estimated_speed_kmph: float
    free_flow_speed_kmph: float
    density_pcu_per_km: float
    volume_capacity_ratio: float
    congestion_score: float = Field(..., ge=0.0, le=1.0, description="Normalized score 0.0 (empty) to 1.0 (gridlock)")
    congestion_level: CongestionLevel
    is_abnormal: bool = Field(False, description="Flagged if sudden spike or anomaly detected")
    abnormal_reason: Optional[str] = None


class ForecastHorizon(BaseModel):
    """Forecast for a specific future horizon (15m or 30m)."""
    horizon_minutes: int = Field(..., description="15 or 30")
    predicted_timestamp: datetime
    predicted_congestion_score: float = Field(..., ge=0.0, le=1.0)
    predicted_congestion_level: CongestionLevel
    predicted_speed_kmph: float = Field(..., ge=0.0)
    heuristic_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Heuristic confidence score [0.0 - 1.0] derived from recent volatility (or fixed cold-start value), NOT an empirical probability."
    )


class TrafficForecastResult(BaseModel):
    """15-30 minute forecast container."""
    horizon_15m: ForecastHorizon
    horizon_30m: ForecastHorizon


class RoutingMetadata(BaseModel):
    """Traffic penalty and multiplier data directly consumed by Member 4 (Route Optimization)."""
    travel_time_multiplier: float = Field(
        ..., ge=1.0, description="Multiplier over free-flow travel time, e.g. 1.0 (empty) to 4.0+ (gridlock)"
    )
    penalty_weight: float = Field(..., ge=0.0, description="Additive penalty cost for Dijkstra/A* routing")
    recommended_avoid: bool = Field(False, description="Recommendation to route around this segment if severe")


class TrafficIntelligenceOutput(BaseModel):
    """Complete structured output payload returned to Member 1 (Backend)."""
    road_id: str
    intersection_id: Optional[str] = Field(None, description="Intersection identifier if observation is intersection-level")
    timestamp: datetime
    current_state: CurrentTrafficState
    forecast: TrafficForecastResult
    routing_metadata: RoutingMetadata
    forecast_reliability: Optional[str] = Field(
        None,
        description="Forecast reliability indicator: 'normal', 'low_during_incident', or 'low_cold_start'"
    )
    data_provenance: Dict[str, str] = Field(
        default_factory=lambda: {
            "module": "traffic_intelligence",
            "model_version": "v1.0-baseline-ridge",
            "training_data": "synthetic",
            "forecast_type": "model_prediction",
            "forecast_reliability": "normal",
            "is_synthetic": "false"
        }
    )
