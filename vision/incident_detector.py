"""
UrbanFlow AI - Candidate Incident Detector (Member 2)
Implements conservative, explainable heuristics for candidate collision and blockage detection.
Requires ALL 4 collision criteria to eliminate false positives from red lights or stop-and-go jams.
"""

import math
from typing import Dict, List, Optional, Set, Tuple
from vision.config import CameraConfig, IncidentThresholdConfig
from vision.schemas import CandidateDetails, CandidateIncident
from vision.tracker import TrackedVehicle


class IncidentDetector:
    """
    Evaluates tracked vehicles against strict geometric, kinematic, and spatial rules.
    Flags candidates as 'detected_unverified' with heuristic_score <= 0.85.
    """
    def __init__(
        self,
        camera_config: CameraConfig,
        thresholds: Optional[IncidentThresholdConfig] = None
    ):
        self.camera_config = camera_config
        self.thresholds = thresholds or IncidentThresholdConfig()
        self.incident_counter = 1
        self.active_incident_keys: Set[Tuple[int, ...]] = set()

    def evaluate_frame(
        self,
        tracked_vehicles: List[TrackedVehicle],
        current_timestamp_seconds: float,
        frame_index: int,
        derived_wall_clock: Optional[str] = None
    ) -> List[CandidateIncident]:
        """
        Scans current tracked vehicles for candidate collisions and road blockages.
        Returns newly triggered CandidateIncident records.
        """
        new_incidents: List[CandidateIncident] = []

        # 1. Evaluate Candidate Collisions (Multi-vehicle interaction)
        collision_candidates = self._detect_candidate_collisions(
            tracked_vehicles=tracked_vehicles,
            current_timestamp_seconds=current_timestamp_seconds,
            frame_index=frame_index,
            derived_wall_clock=derived_wall_clock
        )
        new_incidents.extend(collision_candidates)

        # 2. Evaluate Candidate Road Blockages (Single stationary vehicle in active lane)
        blockage_candidates = self._detect_candidate_blockages(
            tracked_vehicles=tracked_vehicles,
            current_timestamp_seconds=current_timestamp_seconds,
            frame_index=frame_index,
            derived_wall_clock=derived_wall_clock
        )
        new_incidents.extend(blockage_candidates)

        return new_incidents

    def _detect_candidate_collisions(
        self,
        tracked_vehicles: List[TrackedVehicle],
        current_timestamp_seconds: float,
        frame_index: int,
        derived_wall_clock: Optional[str]
    ) -> List[CandidateIncident]:
        candidates: List[CandidateIncident] = []
        n = len(tracked_vehicles)
        if n < 2:
            return candidates

        # Check surrounding traffic motion: count how many OTHER vehicles are moving
        moving_vehicles_count = sum(
            1 for v in tracked_vehicles
            if v.latest_point.speed_bbox_widths_per_sec > (self.thresholds.stationary_speed_threshold_bbox_widths_per_sec * 2.0)
        )

        for i in range(n):
            v1 = tracked_vehicles[i]
            p1 = v1.latest_point

            # Check if v1 is outside stop line and normal queue
            if self.camera_config.is_in_normal_queue(p1.centroid[0], p1.centroid[1]):
                continue

            for j in range(i + 1, n):
                v2 = tracked_vehicles[j]
                p2 = v2.latest_point

                if self.camera_config.is_in_normal_queue(p2.centroid[0], p2.centroid[1]):
                    continue

                pair_key = (min(v1.track_id, v2.track_id), max(v1.track_id, v2.track_id))
                if pair_key in self.active_incident_keys:
                    continue  # Already flagged this pair

                # Criterion 1: Mutual Proximity (normalized by average bbox width)
                avg_w = (p1.bbox_width + p2.bbox_width) / 2.0
                dist_px = math.hypot(p1.centroid[0] - p2.centroid[0], p1.centroid[1] - p2.centroid[1])
                spacing_ratio = dist_px / max(1.0, avg_w)

                if spacing_ratio > self.thresholds.max_proximity_bbox_widths:
                    continue

                # Criterion 2: Abrupt Stop of BOTH vehicles
                abrupt1, peak1, drop1, dur1 = v1.kinematics.detect_abrupt_stop(
                    lookback_seconds=2.5,
                    min_pre_stop_speed=self.thresholds.min_pre_stop_relative_speed,
                    max_duration_seconds=self.thresholds.max_abrupt_stop_duration_seconds,
                    stationary_threshold=self.thresholds.stationary_speed_threshold_bbox_widths_per_sec
                )
                abrupt2, peak2, drop2, dur2 = v2.kinematics.detect_abrupt_stop(
                    lookback_seconds=2.5,
                    min_pre_stop_speed=self.thresholds.min_pre_stop_relative_speed,
                    max_duration_seconds=self.thresholds.max_abrupt_stop_duration_seconds,
                    stationary_threshold=self.thresholds.stationary_speed_threshold_bbox_widths_per_sec
                )

                if not (abrupt1 and abrupt2):
                    continue  # BOTH must have stopped abruptly

                # Criterion 3: Heading or Trajectory Deviation
                head_change1 = v1.kinematics.get_heading_change_degrees(lookback_seconds=3.0)
                head_change2 = v2.kinematics.get_heading_change_degrees(lookback_seconds=3.0)
                max_heading_change = max(head_change1, head_change2)

                if max_heading_change < self.thresholds.min_heading_change_degrees:
                    continue  # Must exhibit sudden swerve / angle deviation

                # Criterion 4: Surrounding Traffic Still Moving (Rules out red-light cycle)
                # Count moving vehicles excluding v1 and v2
                v1_moving = 1 if p1.speed_bbox_widths_per_sec > (self.thresholds.stationary_speed_threshold_bbox_widths_per_sec * 2.0) else 0
                v2_moving = 1 if p2.speed_bbox_widths_per_sec > (self.thresholds.stationary_speed_threshold_bbox_widths_per_sec * 2.0) else 0
                surrounding_moving = max(0, moving_vehicles_count - (v1_moving + v2_moving))

                if surrounding_moving < self.thresholds.min_surrounding_moving_vehicles:
                    continue  # If entire street stopped simultaneously, likely a red light or queue

                # Criterion 5: Persistence Outside Normal Queue Position
                stop_dur1 = v1.kinematics.get_stoppage_duration_seconds(self.thresholds.stationary_speed_threshold_bbox_widths_per_sec)
                stop_dur2 = v2.kinematics.get_stoppage_duration_seconds(self.thresholds.stationary_speed_threshold_bbox_widths_per_sec)
                min_stop_dur = min(stop_dur1, stop_dur2)

                if min_stop_dur < self.thresholds.min_collision_persistence_seconds:
                    continue  # Must persist outside queue for required duration

                # ALL criteria passed! Calculate hand-weighted heuristic score:
                raw_score = (
                    0.25 * min(1.0, (drop1 + drop2) / 2.0) +
                    0.25 * min(1.0, max_heading_change / 60.0) +
                    0.25 * min(1.0, min_stop_dur / 6.0) +
                    0.25 * ((v1.confidence + v2.confidence) / 2.0)
                )

                # Apply penalty if camera zones are uncalibrated
                if not self.camera_config.is_calibrated_zones:
                    raw_score *= self.thresholds.uncalibrated_camera_penalty_factor

                heuristic_score = min(self.thresholds.max_heuristic_score, max(0.30, raw_score))

                incident_id = f"INC-CCTV-{self.incident_counter:03d}"
                self.incident_counter += 1
                self.active_incident_keys.add(pair_key)

                incident = CandidateIncident(
                    incident_id=incident_id,
                    type="possible_collision",
                    status="detected_unverified",
                    verification_required=True,
                    source=self.camera_config.camera_id,
                    road_id=self.camera_config.road_id,
                    video_timestamp_seconds=round(current_timestamp_seconds, 3),
                    frame_index=frame_index,
                    derived_wall_clock_time=derived_wall_clock,
                    heuristic_score=round(heuristic_score, 4),
                    severity="unknown",
                    candidate_details=CandidateDetails(
                        detection_reason=(
                            f"Abrupt deceleration of both vehicles ({v1.class_name} #{v1.track_id} and {v2.class_name} #{v2.track_id}) "
                            f"with heading deviation {round(max_heading_change, 1)}°, proximity {round(spacing_ratio, 2)} bbox-widths, "
                            f"and {surrounding_moving} surrounding vehicles actively moving."
                        ),
                        vehicle_count_involved=2,
                        involved_track_ids=[v1.track_id, v2.track_id],
                        vehicle_types=[v1.class_name, v2.class_name],
                        relative_pre_stop_speed_bbox_widths_per_sec=round(max(peak1, peak2), 3),
                        relative_speed_drop_ratio=round((drop1 + drop2) / 2.0, 3),
                        trajectory_deviation_degrees=round(max_heading_change, 1),
                        relative_spacing_bbox_widths=round(spacing_ratio, 2),
                        surrounding_traffic_moving=True,
                        outside_stop_line_zone=True,
                        stoppage_duration_seconds=round(min_stop_dur, 2)
                    ),
                    evidence=[],  # Populated by evidence extractor
                    affected_road_ids=[self.camera_config.road_id]
                )
                candidates.append(incident)

        return candidates

    def _detect_candidate_blockages(
        self,
        tracked_vehicles: List[TrackedVehicle],
        current_timestamp_seconds: float,
        frame_index: int,
        derived_wall_clock: Optional[str]
    ) -> List[CandidateIncident]:
        candidates: List[CandidateIncident] = []

        for v in tracked_vehicles:
            pt = v.latest_point

            # Must be inside camera ROI
            if not self.camera_config.is_in_roi(pt.centroid[0], pt.centroid[1]):
                continue

            # Must be OUTSIDE normal queue / stop line zone
            if self.camera_config.is_in_normal_queue(pt.centroid[0], pt.centroid[1]):
                continue

            single_key = (v.track_id,)
            if single_key in self.active_incident_keys:
                continue

            stoppage_sec = v.kinematics.get_stoppage_duration_seconds(
                self.thresholds.stationary_speed_threshold_bbox_widths_per_sec
            )

            if stoppage_sec >= self.thresholds.blockage_min_duration_seconds:
                raw_score = 0.45 + min(0.35, (stoppage_sec - self.thresholds.blockage_min_duration_seconds) * 0.03)
                if not self.camera_config.is_calibrated_zones:
                    raw_score *= self.thresholds.uncalibrated_camera_penalty_factor

                heuristic_score = min(self.thresholds.max_heuristic_score, raw_score)

                incident_id = f"INC-CCTV-{self.incident_counter:03d}"
                self.incident_counter += 1
                self.active_incident_keys.add(single_key)

                incident = CandidateIncident(
                    incident_id=incident_id,
                    type="road_blockage",
                    status="detected_unverified",
                    verification_required=True,
                    source=self.camera_config.camera_id,
                    road_id=self.camera_config.road_id,
                    video_timestamp_seconds=round(current_timestamp_seconds, 3),
                    frame_index=frame_index,
                    derived_wall_clock_time=derived_wall_clock,
                    heuristic_score=round(heuristic_score, 4),
                    severity="unknown",
                    candidate_details=CandidateDetails(
                        detection_reason=(
                            f"Vehicle {v.class_name} #{v.track_id} stationary in travel lane for {round(stoppage_sec, 1)}s "
                            f"outside normal signal stop line."
                        ),
                        vehicle_count_involved=1,
                        involved_track_ids=[v.track_id],
                        vehicle_types=[v.class_name],
                        relative_pre_stop_speed_bbox_widths_per_sec=0.0,
                        relative_speed_drop_ratio=0.0,
                        trajectory_deviation_degrees=0.0,
                        relative_spacing_bbox_widths=0.0,
                        surrounding_traffic_moving=True,
                        outside_stop_line_zone=True,
                        stoppage_duration_seconds=round(stoppage_sec, 2)
                    ),
                    evidence=[],
                    affected_road_ids=[self.camera_config.road_id]
                )
                candidates.append(incident)

        return candidates
