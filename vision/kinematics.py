"""
UrbanFlow AI - Kinematics & Relative Motion Tracker (Member 2)
Tracks per-vehicle trajectories, relative speeds (bbox-widths/sec and pixels/sec),
real-time acceleration/deceleration, and heading angles using real elapsed time.
"""

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple


@dataclass
class KinematicPoint:
    video_timestamp_seconds: float
    frame_index: int
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    centroid: Tuple[float, float]           # cx, cy
    bbox_width: float
    bbox_height: float
    pixel_speed: float                       # pixels / second (real elapsed time)
    speed_bbox_widths_per_sec: float         # bbox-widths / second
    heading_degrees: Optional[float]         # -180.0 to 180.0 degrees


class VehicleKinematics:
    """
    Tracks trajectory and relative motion history for a single persistent vehicle track.
    All calculations derive from real elapsed time (video_timestamp_seconds),
    not an assumed fixed frame rate.
    """
    def __init__(self, track_id: int, class_name: str, max_history_seconds: float = 6.0):
        self.track_id = track_id
        self.class_name = class_name
        self.max_history_seconds = max_history_seconds
        self.history: Deque[KinematicPoint] = deque()

    def add_point(
        self,
        video_timestamp_seconds: float,
        frame_index: int,
        bbox: Tuple[float, float, float, float]
    ) -> KinematicPoint:
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        w = max(1.0, float(x2 - x1))
        h = max(1.0, float(y2 - y1))

        pixel_speed = 0.0
        speed_bbox_widths = 0.0
        heading: Optional[float] = None

        if self.history:
            prev = self.history[-1]
            dt = video_timestamp_seconds - prev.video_timestamp_seconds

            if dt > 1e-4:
                dx = cx - prev.centroid[0]
                dy = cy - prev.centroid[1]
                dist_px = math.hypot(dx, dy)
                pixel_speed = dist_px / dt
                speed_bbox_widths = pixel_speed / w

                if dist_px > 2.0:  # Compute heading only when displacement is significant
                    heading = math.degrees(math.atan2(dy, dx))
                else:
                    heading = prev.heading_degrees
            else:
                pixel_speed = prev.pixel_speed
                speed_bbox_widths = prev.speed_bbox_widths_per_sec
                heading = prev.heading_degrees

        point = KinematicPoint(
            video_timestamp_seconds=video_timestamp_seconds,
            frame_index=frame_index,
            bbox=bbox,
            centroid=(cx, cy),
            bbox_width=w,
            bbox_height=h,
            pixel_speed=pixel_speed,
            speed_bbox_widths_per_sec=speed_bbox_widths,
            heading_degrees=heading
        )
        self.history.append(point)

        # Prune old points beyond max_history_seconds
        while len(self.history) > 2 and (video_timestamp_seconds - self.history[0].video_timestamp_seconds) > self.max_history_seconds:
            self.history.popleft()

        return point

    @property
    def latest(self) -> Optional[KinematicPoint]:
        return self.history[-1] if self.history else None

    def get_stoppage_duration_seconds(self, stationary_threshold: float = 0.10) -> float:
        """
        Calculates how many continuous seconds the vehicle has been stationary (< threshold).
        """
        if not self.history:
            return 0.0
        
        current_time = self.history[-1].video_timestamp_seconds
        stationary_start_time = current_time

        for pt in reversed(self.history):
            if pt.speed_bbox_widths_per_sec <= stationary_threshold:
                stationary_start_time = pt.video_timestamp_seconds
            else:
                break

        return max(0.0, current_time - stationary_start_time)

    def detect_abrupt_stop(
        self,
        lookback_seconds: float = 2.0,
        min_pre_stop_speed: float = 0.40,
        max_duration_seconds: float = 1.20,
        stationary_threshold: float = 0.10
    ) -> Tuple[bool, float, float, float]:
        """
        Determines if this vehicle experienced an abrupt stop:
        Returns:
            (is_abrupt_stop, peak_pre_stop_speed, speed_drop_ratio, duration_seconds)
        """
        if len(self.history) < 3:
            return False, 0.0, 0.0, 0.0

        current_time = self.history[-1].video_timestamp_seconds
        recent = [p for p in self.history if (current_time - p.video_timestamp_seconds) <= lookback_seconds]
        if len(recent) < 3:
            return False, 0.0, 0.0, 0.0

        current_speed = recent[-1].speed_bbox_widths_per_sec
        if current_speed > stationary_threshold:
            # Currently not stopped
            return False, 0.0, 0.0, 0.0

        # Find peak speed in recent window
        peak_point = max(recent, key=lambda p: p.speed_bbox_widths_per_sec)
        peak_speed = peak_point.speed_bbox_widths_per_sec

        if peak_speed < min_pre_stop_speed:
            return False, peak_speed, 0.0, 0.0

        duration = current_time - peak_point.video_timestamp_seconds
        if duration <= 0 or duration > max_duration_seconds:
            return False, peak_speed, 0.0, duration

        drop_ratio = (peak_speed - current_speed) / max(1e-5, peak_speed)
        is_abrupt = drop_ratio >= 0.70

        return is_abrupt, peak_speed, drop_ratio, duration

    def get_heading_change_degrees(self, lookback_seconds: float = 2.5) -> float:
        """
        Computes maximum trajectory/heading angle deflection during recent movement.
        """
        if len(self.history) < 3:
            return 0.0

        current_time = self.history[-1].video_timestamp_seconds
        headings = [
            p.heading_degrees
            for p in self.history
            if (current_time - p.video_timestamp_seconds) <= lookback_seconds and p.heading_degrees is not None
        ]
        if len(headings) < 2:
            return 0.0

        # Calculate max angle difference in degrees
        max_diff = 0.0
        for i in range(len(headings)):
            for j in range(i + 1, len(headings)):
                diff = abs(headings[i] - headings[j])
                diff = min(diff, 360.0 - diff)  # Account for circular wrap-around
                if diff > max_diff:
                    max_diff = diff

        return max_diff
