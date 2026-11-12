"""
UrbanFlow AI - Computer Vision & CCTV Analysis Module (Member 2)
Provides vehicle detection, multi-object tracking, relative traffic density estimation,
and conservative candidate incident detection.
"""

from vision.config import CameraConfig, IncidentThresholdConfig
from vision.detector import VEHICLE_CLASSES, Detection, VehicleDetector
from vision.incident_detector import IncidentDetector
from vision.kinematics import KinematicPoint, VehicleKinematics
from vision.pipeline import TrafficVisionPipeline
from vision.schemas import (
    CandidateDetails,
    CandidateIncident,
    EvidenceItem,
    TrafficObservation,
    VideoAnalysisResult,
)
from vision.traffic_analyzer import TrafficAnalyzer
from vision.tracker import TrackedVehicle, VehicleTracker

__all__ = [
    "TrafficVisionPipeline",
    "CameraConfig",
    "IncidentThresholdConfig",
    "VehicleDetector",
    "VehicleTracker",
    "TrafficAnalyzer",
    "IncidentDetector",
    "KinematicPoint",
    "VehicleKinematics",
    "TrackedVehicle",
    "Detection",
    "VEHICLE_CLASSES",
    "CandidateIncident",
    "CandidateDetails",
    "EvidenceItem",
    "TrafficObservation",
    "VideoAnalysisResult",
]
