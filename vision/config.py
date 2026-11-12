"""
UrbanFlow AI - Vision Module Configuration (Member 2)
Handles camera ROI, lane geometries, stop-line zones, and configurable
kinematic thresholds for collision and blockage heuristics.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def point_in_polygon(x: float, y: float, polygon: List[List[float]]) -> bool:
    """
    Ray-casting algorithm to test if a 2D point (x, y) is inside a polygon.
    Pure Python implementation: zero external dependencies, fast and robust.
    """
    if not polygon or len(polygon) < 3:
        return True  # If polygon is not specified, everything is considered inside
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


@dataclass
class LaneConfig:
    lane_id: str
    direction: str
    polygon: List[List[float]] = field(default_factory=list)

    def contains_point(self, x: float, y: float) -> bool:
        return point_in_polygon(x, y, self.polygon)


@dataclass
class CameraConfig:
    """
    Per-camera spatial configuration defining the field-of-view,
    lanes, and signal stop zones.
    """
    camera_id: str = "default_camera"
    road_id: str = "ROAD-01"
    is_calibrated_zones: bool = False
    description: str = "Default full-frame uncalibrated camera"
    reference_resolution: Tuple[int, int] = (1920, 1080)
    roi_polygon: List[List[float]] = field(default_factory=list)
    lanes: List[LaneConfig] = field(default_factory=list)
    stop_line_zone: List[List[float]] = field(default_factory=list)
    normal_queue_polygon: List[List[float]] = field(default_factory=list)

    def is_in_roi(self, x: float, y: float) -> bool:
        if not self.roi_polygon:
            return True
        return point_in_polygon(x, y, self.roi_polygon)

    def is_in_stop_line_zone(self, x: float, y: float) -> bool:
        """
        Returns True if (x, y) falls inside the signal stop-line zone
        where vehicles routinely stop for red lights.
        """
        if not self.stop_line_zone:
            return False
        return point_in_polygon(x, y, self.stop_line_zone)

    def is_in_normal_queue(self, x: float, y: float) -> bool:
        """
        Returns True if (x, y) is within normal queueing regions.
        """
        if not self.normal_queue_polygon:
            return self.is_in_stop_line_zone(x, y)
        return point_in_polygon(x, y, self.normal_queue_polygon)

    @classmethod
    def from_file(cls, path: str) -> "CameraConfig":
        """Load camera configuration from JSON or YAML file."""
        if not os.path.exists(path):
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            if path.endswith(".json"):
                data = json.load(f)
            else:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    data = json.load(f)

        lanes = [
            LaneConfig(
                lane_id=l.get("lane_id", f"LANE-{i}"),
                direction=l.get("direction", "unknown"),
                polygon=l.get("polygon", [])
            )
            for i, l in enumerate(data.get("lanes", []))
        ]

        return cls(
            camera_id=data.get("camera_id", "default_camera"),
            road_id=data.get("road_id", "ROAD-01"),
            is_calibrated_zones=data.get("is_calibrated_zones", bool(data.get("roi_polygon"))),
            description=data.get("description", ""),
            reference_resolution=tuple(data.get("reference_resolution", (1920, 1080))),
            roi_polygon=data.get("roi_polygon", []),
            lanes=lanes,
            stop_line_zone=data.get("stop_line_zone", []),
            normal_queue_polygon=data.get("normal_queue_polygon", [])
        )


@dataclass
class IncidentThresholdConfig:
    """
    Configurable kinematic thresholds for collision and blockage heuristics.
    Ensures that every threshold is explicitly tunable rather than hardcoded.
    """
    # Kinematic Collision Criteria (ALL required):
    min_pre_stop_relative_speed: float = 0.50
    """Min speed in bbox-widths-per-second before sudden deceleration."""

    max_abrupt_stop_duration_seconds: float = 1.20
    """Max elapsed time in seconds over which speed must drop to stationary (<0.10)."""

    min_speed_drop_ratio: float = 0.75
    """Min fraction of initial speed that must be lost during abrupt stop (0.0 to 1.0)."""

    min_heading_change_degrees: float = 20.0
    """Min change in heading angle (degrees) indicating sudden deflection/swerve."""

    max_proximity_bbox_widths: float = 1.30
    """Max distance between vehicle centers in average bbox widths to indicate impact."""

    min_collision_persistence_seconds: float = 3.0
    """Seconds candidate vehicles must remain stationary together outside stop line."""

    min_surrounding_moving_vehicles: int = 1
    """Min number of other moving vehicles on the road to confirm traffic is flowing."""

    # Blockage Criteria:
    blockage_min_duration_seconds: float = 12.0
    """Seconds a vehicle must remain stationary in active lane outside stop zone to flag blockage."""

    stationary_speed_threshold_bbox_widths_per_sec: float = 0.08
    """Upper bound speed to classify a vehicle as stationary."""

    # Confidence Calibration & Penalties:
    max_heuristic_score: float = 0.85
    """Upper clamp on heuristic score (conforming to safety boundary)."""

    uncalibrated_camera_penalty_factor: float = 0.70
    """Penalty factor applied to heuristic score when no calibrated camera zones exist."""
