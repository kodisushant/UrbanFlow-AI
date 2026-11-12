"""
UrbanFlow AI - Vehicle Tracker (Member 2)
Multi-object tracker wrapper integrating ByteTrack association and
maintaining per-track kinematic history with real elapsed time.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from vision.detector import VEHICLE_CLASSES, Detection
from vision.kinematics import KinematicPoint, VehicleKinematics


@dataclass
class TrackedVehicle:
    track_id: int
    bbox: Tuple[float, float, float, float]
    class_id: int
    class_name: str
    confidence: float
    kinematics: VehicleKinematics
    latest_point: KinematicPoint


class VehicleTracker:
    """
    Manages vehicle tracking across frames and couples tracks with kinematics.
    Supports Ultralytics ByteTrack integration and a robust centroid/IoU fallback.
    """
    def __init__(self, max_history_seconds: float = 6.0):
        self.max_history_seconds = max_history_seconds
        self.active_tracks: Dict[int, VehicleKinematics] = {}
        self._next_fallback_id = 1

    def update_with_detections(
        self,
        tracked_boxes: List[Tuple[int, Tuple[float, float, float, float], int, float]],
        video_timestamp_seconds: float,
        frame_index: int
    ) -> List[TrackedVehicle]:
        """
        Updates tracks from external tracker output (e.g. YOLO track).
        tracked_boxes: list of (track_id, (x1, y1, x2, y2), class_id, confidence)
        """
        results: List[TrackedVehicle] = []
        current_ids = set()

        for track_id, bbox, cls_id, conf in tracked_boxes:
            current_ids.add(track_id)
            cls_name = VEHICLE_CLASSES.get(cls_id, "vehicle")

            if track_id not in self.active_tracks:
                self.active_tracks[track_id] = VehicleKinematics(
                    track_id=track_id,
                    class_name=cls_name,
                    max_history_seconds=self.max_history_seconds
                )

            kin = self.active_tracks[track_id]
            point = kin.add_point(
                video_timestamp_seconds=video_timestamp_seconds,
                frame_index=frame_index,
                bbox=bbox
            )

            results.append(TrackedVehicle(
                track_id=track_id,
                bbox=bbox,
                class_id=cls_id,
                class_name=cls_name,
                confidence=conf,
                kinematics=kin,
                latest_point=point
            ))

        # Clean up tracks not seen for over 5 seconds
        to_remove = []
        for tid, kin in self.active_tracks.items():
            if kin.latest and (video_timestamp_seconds - kin.latest.video_timestamp_seconds) > 5.0:
                to_remove.append(tid)
        for tid in to_remove:
            del self.active_tracks[tid]

        return results

    def update_fallback_iou(
        self,
        detections: List[Detection],
        video_timestamp_seconds: float,
        frame_index: int,
        iou_threshold: float = 0.30
    ) -> List[TrackedVehicle]:
        """
        Fallback IoU-based tracker when native ByteTrack is not directly hooked.
        Computes bounding box IoU with previous active tracks.
        """
        matched_tracks: List[Tuple[int, Tuple[float, float, float, float], int, float]] = []
        unmatched_dets = list(detections)

        # Match existing active tracks by IoU
        for tid, kin in list(self.active_tracks.items()):
            if not kin.latest or (video_timestamp_seconds - kin.latest.video_timestamp_seconds) > 1.5:
                continue

            prev_box = kin.latest.bbox
            best_iou = 0.0
            best_det_idx = -1

            for idx, det in enumerate(unmatched_dets):
                iou = self._calculate_iou(prev_box, det.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = idx

            if best_iou >= iou_threshold and best_det_idx >= 0:
                det = unmatched_dets.pop(best_det_idx)
                matched_tracks.append((tid, det.bbox, det.class_id, det.confidence))

        # Assign new track IDs to unmatched detections
        for det in unmatched_dets:
            new_id = self._next_fallback_id
            self._next_fallback_id += 1
            matched_tracks.append((new_id, det.bbox, det.class_id, det.confidence))

        return self.update_with_detections(matched_tracks, video_timestamp_seconds, frame_index)

    @staticmethod
    def _calculate_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
        boxAArea = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
        boxBArea = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou
