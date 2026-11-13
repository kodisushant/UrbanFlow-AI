from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator


class IncidentStatus(str, Enum):
    CANDIDATE = "candidate"
    DETECTED_UNVERIFIED = "candidate"
    VERIFIED = "verified"
    RESPONSE_RECOMMENDED = "response_recommended"
    SIMULATED_DISPATCH = "simulated_dispatch"
    ON_SCENE = "on_scene"
    RESOLVED = "resolved"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "medium"


class ObservedVehicle(BaseModel):
    vehicle_class: str = Field(..., description="Vehicle type e.g., car, truck, bus, motorcycle")
    bbox: List[int] = Field(..., min_length=4, max_length=4, description="Bounding box [x1, y1, x2, y2]")
    speed_kmph: float = Field(default=0.0, ge=0.0)
    is_stopped: bool = Field(default=True)
    relative_speed_bbox_widths_per_sec: Optional[float] = None


class IncidentDetectionPayload(BaseModel):
    camera_id: Optional[str] = Field(default="cctv_camera_01", min_length=1)
    source: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    candidate_type: Optional[str] = Field(default="possible_collision")
    type: Optional[str] = Field(default=None)
    confidence: Optional[float] = Field(default=0.85, ge=0.0, le=1.0)
    heuristic_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    location_node: Optional[str] = Field(default="INT-03", description="Associated intersection node ID")
    road_id: Optional[str] = Field(default=None)
    affected_road_id: Optional[str] = Field(default=None)
    evidence_image_url: Optional[str] = Field(default=None)
    evidence_urls: List[str] = Field(default_factory=list)
    observed_vehicles: List[ObservedVehicle] = Field(default_factory=list)
    patient_count: Optional[int] = Field(default=0)
    scenario_type: Optional[str] = Field(default="accident")
    is_simulated: bool = Field(default=True)

    @model_validator(mode="after")
    def sync_payload_fields(self):
        if not self.camera_id and self.source:
            self.camera_id = self.source
        if not self.source and self.camera_id:
            self.source = self.camera_id
        if not self.candidate_type and self.type:
            self.candidate_type = self.type
        if not self.affected_road_id and self.road_id:
            self.affected_road_id = self.road_id
        if self.heuristic_score is not None and self.confidence is None:
            self.confidence = self.heuristic_score
        elif self.confidence is not None and self.heuristic_score is None:
            self.heuristic_score = self.confidence
        return self


class IncidentVerificationRequest(BaseModel):
    verified: bool = Field(..., description="True if operator confirms, False if rejected as false positive")
    operator_id: str = Field(default="OP_COMMAND_01", min_length=1)
    notes: Optional[str] = Field(None, description="Operator observations or dispatch instructions")


class IncidentVerificationRecord(BaseModel):
    verified: bool
    operator_id: str
    verified_at: datetime
    notes: Optional[str] = None


class IncidentRecord(BaseModel):
    incident_id: str
    title: str
    status: str = "candidate"
    incident_type: str
    severity: str = "medium"
    confidence: float = 0.85
    heuristic_score: float = 0.85
    location_node: str
    affected_road_id: Optional[str] = None
    latitude: float
    longitude: float
    source: str
    evidence_urls: List[str] = Field(default_factory=list)
    created_at: Any = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Any = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_info: Optional[IncidentVerificationRecord] = None
    structured_report: Optional[str] = None
    recommended_service: Optional[str] = None
    assigned_unit_ids: List[str] = Field(default_factory=list)
    patient_count: int = Field(default=0, description="Reported or triage patient count")
    scenario_type: Optional[str] = Field(default="accident", description="accident | fire")

    @model_validator(mode="after")
    def sync_record_fields(self):
        if self.heuristic_score is None:
            self.heuristic_score = self.confidence
        elif self.confidence is None:
            self.confidence = self.heuristic_score
        return self

    model_config = ConfigDict(from_attributes=True)
