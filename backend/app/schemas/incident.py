from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class IncidentStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    RESPONSE_RECOMMENDED = "response_recommended"
    SIMULATED_DISPATCH = "simulated_dispatch"
    RESOLVED = "resolved"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ObservedVehicle(BaseModel):
    vehicle_class: str = Field(..., description="Vehicle type e.g., car, truck, bus, motorcycle")
    bbox: List[int] = Field(..., min_length=4, max_length=4, description="Bounding box [x1, y1, x2, y2]")
    speed_kmph: float = Field(default=0.0, ge=0.0)
    is_stopped: bool = Field(default=True)


class IncidentDetectionPayload(BaseModel):
    camera_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    candidate_type: str = Field(..., description="e.g. possible_collision, stalled_vehicle, road_debris")
    confidence: float = Field(..., ge=0.0, le=1.0)
    location_node: str = Field(..., description="Associated road graph intersection node ID")
    affected_road_id: Optional[str] = Field(None, description="Affected road edge ID")
    evidence_image_url: Optional[str] = Field(None, description="URL or path to frame evidence snapshot")
    observed_vehicles: List[ObservedVehicle] = Field(default_factory=list)
    is_simulated: bool = Field(default=True)


class IncidentVerificationRequest(BaseModel):
    verified: bool = Field(..., description="True if operator confirms, False if rejected as false positive")
    operator_id: str = Field(..., min_length=1, description="Operator or dispatcher identifier")
    notes: Optional[str] = Field(None, description="Operator observations or dispatch instructions")


class IncidentVerificationRecord(BaseModel):
    verified: bool
    operator_id: str
    verified_at: datetime
    notes: Optional[str] = None


class IncidentRecord(BaseModel):
    incident_id: str
    title: str
    status: IncidentStatus = IncidentStatus.CANDIDATE
    incident_type: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    confidence: float = Field(..., ge=0.0, le=1.0)
    location_node: str
    affected_road_id: Optional[str] = None
    latitude: float
    longitude: float
    source: str
    evidence_urls: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    verification_info: Optional[IncidentVerificationRecord] = None
    structured_report: Optional[str] = None
    recommended_service: Optional[str] = None
    assigned_unit_ids: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
