"""
UrbanFlow AI - Traffic Analyzer (Member 2)
Computes periodic traffic aggregation metrics: counts by class, active tracks,
relative speeds, lane occupancy ratio, and heuristic congestion levels.
"""

from typing import Dict, List, Optional
from vision.config import CameraConfig
from vision.schemas import TrafficObservation
from vision.tracker import TrackedVehicle


class TrafficAnalyzer:
    """
    Aggregates vehicle detections and kinematics into periodic TrafficObservation records.
    Filters by camera ROI and computes relative traffic density.
    """
    def __init__(self, camera_config: CameraConfig, sample_duration_seconds: float = 3.0):
        self.camera_config = camera_config
        self.sample_duration_seconds = sample_duration_seconds
        self.last_observation_timestamp = 0.0

    def should_emit_observation(self, current_timestamp_seconds: float) -> bool:
        return (current_timestamp_seconds - self.last_observation_timestamp) >= self.sample_duration_seconds

    def generate_observation(
        self,
        tracked_vehicles: List[TrackedVehicle],
        current_timestamp_seconds: float,
        frame_index: int,
        derived_wall_clock: Optional[str] = None
    ) -> TrafficObservation:
        self.last_observation_timestamp = current_timestamp_seconds

        # Filter vehicles inside camera ROI
        roi_vehicles = [
            v for v in tracked_vehicles
            if self.camera_config.is_in_roi(v.latest_point.centroid[0], v.latest_point.centroid[1])
        ]

        breakdown: Dict[str, int] = {
            "cars": 0,
            "motorcycles": 0,
            "buses": 0,
            "trucks": 0
        }

        total_pixel_speed = 0.0
        total_bbox_width_speed = 0.0
        stopped_count = 0
        total_bbox_area = 0.0

        for v in roi_vehicles:
            cname = v.class_name
            if cname == "car":
                breakdown["cars"] += 1
            elif cname == "motorcycle":
                breakdown["motorcycles"] += 1
            elif cname == "bus":
                breakdown["buses"] += 1
            elif cname == "truck":
                breakdown["trucks"] += 1

            pt = v.latest_point
            total_pixel_speed += pt.pixel_speed
            total_bbox_width_speed += pt.speed_bbox_widths_per_sec

            if pt.speed_bbox_widths_per_sec < 0.10:
                stopped_count += 1

            total_bbox_area += pt.bbox_width * pt.bbox_height

        count = len(roi_vehicles)
        avg_pixel_speed = (total_pixel_speed / count) if count > 0 else 0.0
        avg_bbox_speed = (total_bbox_width_speed / count) if count > 0 else 0.0

        # Estimate ROI area from reference resolution
        ref_w, ref_h = self.camera_config.reference_resolution
        roi_area = max(1000.0, float(ref_w * ref_h * 0.70))
        occupancy_ratio = min(1.0, max(0.0, total_bbox_area / roi_area))

        # Congestion heuristic
        if occupancy_ratio > 0.40 or (count >= 12 and avg_bbox_speed < 0.25):
            congestion = "heavy"
        elif occupancy_ratio > 0.18 or (count >= 6 and avg_bbox_speed < 0.55):
            congestion = "moderate"
        else:
            congestion = "low"

        return TrafficObservation(
            road_id=self.camera_config.road_id,
            source=self.camera_config.camera_id,
            video_timestamp_seconds=round(current_timestamp_seconds, 3),
            frame_index=frame_index,
            derived_wall_clock_time=derived_wall_clock,
            sample_duration_seconds=self.sample_duration_seconds,
            vehicle_count=count,
            breakdown=breakdown,
            active_track_count=count,
            stopped_vehicle_count=stopped_count,
            average_relative_pixel_speed=round(avg_pixel_speed, 2),
            average_relative_speed_bbox_widths_per_sec=round(avg_bbox_speed, 3),
            congestion_level=congestion,
            lane_occupancy_ratio=round(occupancy_ratio, 4)
        )
