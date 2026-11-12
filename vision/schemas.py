"""
UrbanFlow AI - Vision Module Data Schemas (Member 2)
Strict Pydantic models defining the return contract between Computer Vision
and Member 1's backend orchestration system.

Conforms to project constraints:
1. No camera calibration: relative pixel speed or bbox-widths-per-second only.
2. Severity is fixed to 'unknown' (assigned strictly by human or Member 1 agent).
3. Confidence renamed to 'heuristic_score' (capped at 0.85, hand-weighted).
4. Primary time fields are 'video_timestamp_seconds' and 'frame_index'.
5. Evidence filenames follow: INC-CCTV-001_frame_426.jpg & INC-CCTV-001_crop_14_19.jpg
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    """
    Evidence frame or cropped vehicle snapshot.
    Filename patterns enforced:
    - Annotated full frame: {incident_id}_frame_{frame_index}.jpg
    - Involved vehicle crop: {incident_id}_crop_{track_id1}_{track_id2}.jpg
    """
    evidence_type: Literal["annotated_frame", "vehicle_crop"] = Field(
        ...,
        description="Type of evidence artifact: annotated full frame or cropped vehicle region."
    )
    file_path: str = Field(
        ...,
        description="Relative or absolute path to evidence image on disk (e.g., assets/evidence/INC-CCTV-001_frame_426.jpg)."
    )
    video_timestamp_seconds: float = Field(
        ...,
        ge=0.0,
        description="Primary video elapsed timestamp in seconds when evidence was captured."
    )
    frame_index: int = Field(
        ...,
        ge=0,
        description="Exact video frame index when evidence was captured."
    )


class CandidateDetails(BaseModel):
    """
    Kinematic and spatial evidence details explaining the candidate incident.
    All speed metrics are strictly relative (pixels/sec or bbox-widths/sec).
    """
    detection_reason: str = Field(
        ...,
        description="Human-readable explanation of why the heuristic flagged this event."
    )
    vehicle_count_involved: int = Field(
        ...,
        ge=1,
        description="Number of vehicles directly involved in the candidate event."
    )
    involved_track_ids: List[int] = Field(
        default_factory=list,
        description="Track IDs of vehicles involved."
    )
    vehicle_types: List[str] = Field(
        default_factory=list,
        description="Vehicle classes detected by YOLO (e.g., ['car', 'truck'])."
    )
    relative_pre_stop_speed_bbox_widths_per_sec: float = Field(
        ...,
        ge=0.0,
        description="Relative speed before sudden stop in bounding-box widths per second."
    )
    relative_speed_drop_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relative deceleration ratio (0.0 to 1.0) indicating speed reduction magnitude."
    )
    trajectory_deviation_degrees: float = Field(
        ...,
        ge=0.0,
        description="Observed angular deviation in trajectory heading before stopping (degrees)."
    )
    relative_spacing_bbox_widths: float = Field(
        ...,
        ge=0.0,
        description="Proximity between candidate vehicles normalized by average bounding-box width."
    )
    surrounding_traffic_moving: bool = Field(
        ...,
        description="True if other non-involved vehicles on the road continued moving (rules out red-light/traffic wave)."
    )
    outside_stop_line_zone: bool = Field(
        ...,
        description="True if stopped vehicles are outside the designated stop-line / normal queue zone."
    )
    stoppage_duration_seconds: float = Field(
        ...,
        ge=0.0,
        description="Duration for which candidate vehicles have remained stationary outside queue area."
    )
    disclaimer: str = Field(
        default="Automated vision heuristic flag. No incident is verified automatically and no human casualties or injuries are inferred.",
        description="Mandatory system safety notice."
    )


class CandidateIncident(BaseModel):
    """
    Candidate incident report emitted by Computer Vision module.
    Always marked as 'detected_unverified' with verification_required=True.
    """
    incident_id: str = Field(
        ...,
        pattern=r"^INC-[A-Za-z0-9_\-]+$",
        description="Unique identifier for candidate incident, e.g. INC-CCTV-001."
    )
    type: Literal[
        "possible_collision",
        "road_blockage",
        "abnormal_stopped_vehicle"
    ] = Field(
        ...,
        description="Candidate incident category based on vision heuristics."
    )
    status: Literal["detected_unverified"] = Field(
        default="detected_unverified",
        description="Initial status. Vision never claims a verified accident."
    )
    verification_required: Literal[True] = Field(
        default=True,
        description="Mandatory verification flag. Human operator or Member 1 agent must verify."
    )
    source: str = Field(
        ...,
        description="Source CCTV camera identifier, e.g. 'cctv_camera_01'."
    )
    road_id: str = Field(
        ...,
        description="Road segment or intersection identifier, e.g. 'ROAD-01'."
    )
    video_timestamp_seconds: float = Field(
        ...,
        ge=0.0,
        description="Primary timestamp: elapsed video time in seconds."
    )
    frame_index: int = Field(
        ...,
        ge=0,
        description="Primary frame reference: video frame index."
    )
    derived_wall_clock_time: Optional[str] = Field(
        default=None,
        description="Optional wall-clock timestamp derived from video start time. Does not use 'Z' suffix unless verified UTC."
    )
    heuristic_score: float = Field(
        ...,
        ge=0.0,
        le=0.85,
        description="Hand-weighted heuristic score (not a calibrated probability), capped strictly at 0.85."
    )
    severity: Literal["unknown"] = Field(
        default="unknown",
        description="Assigned strictly by human operator or Member 1 orchestration agent. Computer vision does not assess severity."
    )
    candidate_details: CandidateDetails = Field(
        ...,
        description="Kinematic and heuristic evidence supporting the candidate event."
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="List of evidence snapshots (annotated frame and vehicle crops)."
    )
    affected_road_ids: List[str] = Field(
        default_factory=list,
        description="Road IDs impacted or potentially blocked by this event."
    )

    @field_validator("heuristic_score", mode="before")
    @classmethod
    def cap_heuristic_score(cls, v: float) -> float:
        val = float(v)
        if val > 0.85:
            return 0.85
        return round(val, 4)


class TrafficObservation(BaseModel):
    """
    Periodic traffic aggregation record emitted by Computer Vision module.
    Provides volume, relative flow speeds, and congestion level for Member 3's forecasting model.
    """
    road_id: str = Field(
        ...,
        description="Road identifier observed by the camera."
    )
    source: str = Field(
        ...,
        description="Camera ID or video source."
    )
    video_timestamp_seconds: float = Field(
        ...,
        ge=0.0,
        description="Primary video elapsed time in seconds at observation window end."
    )
    frame_index: int = Field(
        ...,
        ge=0,
        description="Primary video frame index at observation window end."
    )
    derived_wall_clock_time: Optional[str] = Field(
        default=None,
        description="Optional wall-clock timestamp derived from video start time without unverified UTC 'Z'."
    )
    sample_duration_seconds: float = Field(
        ...,
        gt=0.0,
        description="Duration of the observation time window in seconds."
    )
    vehicle_count: int = Field(
        ...,
        ge=0,
        description="Total distinct vehicles observed in ROI during window."
    )
    breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts broken down by vehicle class (e.g. {'cars': 12, 'trucks': 2, 'buses': 1, 'motorcycles': 3})."
    )
    active_track_count: int = Field(
        ...,
        ge=0,
        description="Number of currently active vehicle tracks in ROI."
    )
    stopped_vehicle_count: int = Field(
        ...,
        ge=0,
        description="Number of vehicles currently stationary in ROI."
    )
    average_relative_pixel_speed: float = Field(
        ...,
        ge=0.0,
        description="Average vehicle speed in pixels per second across active tracks."
    )
    average_relative_speed_bbox_widths_per_sec: float = Field(
        ...,
        ge=0.0,
        description="Average vehicle speed in bounding-box widths per second across active tracks."
    )
    congestion_level: Literal["low", "moderate", "heavy"] = Field(
        ...,
        description="Heuristic congestion classification derived from vehicle density and relative speed."
    )
    lane_occupancy_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of ROI area occupied by vehicle bounding boxes (0.0 to 1.0)."
    )


class VideoAnalysisResult(BaseModel):
    """
    Unified result object returned by the vision pipeline for a complete video run.
    Contains metadata, all periodic observations, and all flagged candidate incidents.
    """
    video_file: str = Field(..., description="Path or name of processed video.")
    camera_id: str = Field(..., description="Camera identifier.")
    road_id: str = Field(..., description="Road identifier.")
    total_frames: int = Field(..., ge=0, description="Total video frames.")
    processed_frames: int = Field(..., ge=0, description="Number of frames processed (accounting for frame stride).")
    fps: float = Field(..., gt=0.0, description="Video native frames per second.")
    duration_seconds: float = Field(..., ge=0.0, description="Total video duration in seconds.")
    frame_stride: int = Field(..., ge=1, description="Frame sampling stride applied.")
    camera_config_calibrated: bool = Field(..., description="True if calibrated ROI and stop-line zones were provided.")
    traffic_observations: List[TrafficObservation] = Field(default_factory=list)
    candidate_incidents: List[CandidateIncident] = Field(default_factory=list)
