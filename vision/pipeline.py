"""
UrbanFlow AI - Vision Pipeline Orchestrator (Member 2)
Processes pre-recorded CCTV video, tracks vehicles, aggregates traffic flow metrics,
evaluates candidate incidents, and extracts evidence snapshots.

Operates in two modes:
1. Standalone CLI process writing JSON results for Member 1's backend.
2. In-memory Python module importable directly:
   `from vision.pipeline import TrafficVisionPipeline`
"""

import argparse
import datetime
import json
import os
import sys
from typing import List, Optional, Tuple

from vision.benchmark import get_default_model_format
from vision.config import CameraConfig, IncidentThresholdConfig
from vision.detector import VEHICLE_CLASSES, VehicleDetector
from vision.evidence_extractor import EvidenceExtractor
from vision.incident_detector import IncidentDetector
from vision.schemas import CandidateIncident, TrafficObservation, VideoAnalysisResult
from vision.tracker import VehicleTracker


class TrafficVisionPipeline:
    """
    End-to-end traffic computer vision pipeline.
    Processes video frames with configurable stride, computes kinematics using
    real elapsed time, and outputs strictly validated Pydantic data schemas.
    """
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        config_path: Optional[str] = None,
        frame_stride: int = 2,
        evidence_dir: str = "assets/evidence",
        device: str = "cpu",
        format_choice: str = "auto",
        confidence_threshold: float = 0.25,
        thresholds: Optional[IncidentThresholdConfig] = None
    ):
        self.frame_stride = max(1, frame_stride)
        self.evidence_dir = evidence_dir
        self.device = device
        self.confidence_threshold = confidence_threshold

        # Load camera configuration
        if config_path and os.path.exists(config_path):
            self.camera_config = CameraConfig.from_file(config_path)
        else:
            self.camera_config = CameraConfig(is_calibrated_zones=False)

        # Select model backend format
        if format_choice == "auto":
            format_choice = get_default_model_format()
        self.format_choice = format_choice

        # Initialize sub-modules
        self.detector = VehicleDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            device=device
        )
        self.tracker = VehicleTracker(max_history_seconds=6.0)
        from vision.traffic_analyzer import TrafficAnalyzer
        self.traffic_analyzer = TrafficAnalyzer(
            camera_config=self.camera_config,
            sample_duration_seconds=3.0
        )
        self.incident_detector = IncidentDetector(
            camera_config=self.camera_config,
            thresholds=thresholds or IncidentThresholdConfig()
        )
        self.evidence_extractor = EvidenceExtractor(output_dir=self.evidence_dir)

    def process_video(
        self,
        video_path: str,
        max_frames: Optional[int] = None,
        start_wall_clock_iso: Optional[str] = None
    ) -> VideoAnalysisResult:
        """
        Processes video file and returns unified VideoAnalysisResult.
        Primary time tracking relies strictly on real video_timestamp_seconds and frame_index.
        """
        try:
            import cv2
        except ImportError:
            raise RuntimeError("opencv-python is required to process video. Run 'pip install -r requirements-vision.txt'")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {video_path}")

        native_fps = cap.get(cv2.CAP_PROP_FPS)
        if native_fps <= 0 or native_fps > 120:
            native_fps = 30.0

        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_video_frames / native_fps if total_video_frames > 0 else 0.0

        # Derived wall-clock reference (Optional, marked derived, no unverified 'Z')
        base_datetime = None
        if start_wall_clock_iso:
            try:
                base_datetime = datetime.datetime.fromisoformat(start_wall_clock_iso.replace("Z", ""))
            except Exception:
                base_datetime = None

        observations: List[TrafficObservation] = []
        incidents: List[CandidateIncident] = []

        frame_idx = 0
        processed_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if max_frames and frame_idx >= max_frames:
                break

            # Frame stride: process every Nth frame
            if frame_idx % self.frame_stride != 0:
                frame_idx += 1
                continue

            processed_count += 1
            # Real elapsed video timestamp (not assumed fixed rate):
            t_seconds = frame_idx / native_fps

            # Derived wall-clock time string if base time was supplied
            derived_time = None
            if base_datetime:
                curr_dt = base_datetime + datetime.timedelta(seconds=t_seconds)
                derived_time = curr_dt.isoformat(timespec="milliseconds")

            # 1. Detect vehicles
            detections = self.detector.detect(frame)

            # 2. Track vehicles
            tracked = self.tracker.update_fallback_iou(
                detections=detections,
                video_timestamp_seconds=t_seconds,
                frame_index=frame_idx
            )

            # 3. Traffic aggregation observation (periodic)
            if self.traffic_analyzer.should_emit_observation(t_seconds):
                obs = self.traffic_analyzer.generate_observation(
                    tracked_vehicles=tracked,
                    current_timestamp_seconds=t_seconds,
                    frame_index=frame_idx,
                    derived_wall_clock=derived_time
                )
                observations.append(obs)

            # 4. Incident evaluation (candidate collisions & blockages)
            new_incidents = self.incident_detector.evaluate_frame(
                tracked_vehicles=tracked,
                current_timestamp_seconds=t_seconds,
                frame_index=frame_idx,
                derived_wall_clock=derived_time
            )

            # 5. Extract evidence for new candidate incidents
            for inc in new_incidents:
                self.evidence_extractor.extract_evidence(
                    incident=inc,
                    raw_frame=frame,
                    tracked_vehicles=tracked
                )
                incidents.append(inc)

            frame_idx += 1

        cap.release()

        # Emit final observation window if needed
        if not observations and processed_count > 0:
            obs = self.traffic_analyzer.generate_observation(
                tracked_vehicles=[],
                current_timestamp_seconds=t_seconds,
                frame_index=frame_idx - 1,
                derived_wall_clock=None
            )
            observations.append(obs)

        return VideoAnalysisResult(
            video_file=video_path,
            camera_id=self.camera_config.camera_id,
            road_id=self.camera_config.road_id,
            total_frames=total_video_frames,
            processed_frames=processed_count,
            fps=round(native_fps, 2),
            duration_seconds=round(duration_seconds, 2),
            frame_stride=self.frame_stride,
            camera_config_calibrated=self.camera_config.is_calibrated_zones,
            traffic_observations=observations,
            candidate_incidents=incidents
        )


def main():
    parser = argparse.ArgumentParser(description="UrbanFlow AI - CCTV Vision Processing CLI")
    parser.add_argument("--video", type=str, required=True, help="Path to traffic video file")
    parser.add_argument("--config", type=str, default="assets/camera_configs/cctv_camera_01.json", help="Path to camera config JSON")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO model path")
    parser.add_argument("--frame-stride", type=int, default=2, help="Process every Nth frame (default: 2)")
    parser.add_argument("--evidence-dir", type=str, default="assets/evidence", help="Directory for evidence snapshots")
    parser.add_argument("--out", type=str, default="assets/vision_results.json", help="Output path for JSON results")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames to process")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu)")
    args = parser.parse_args()

    pipeline = TrafficVisionPipeline(
        model_path=args.model,
        config_path=args.config,
        frame_stride=args.frame_stride,
        evidence_dir=args.evidence_dir,
        device=args.device
    )

    print(f"[Vision Pipeline] Starting processing of '{args.video}' with stride={args.frame_stride}...")
    result = pipeline.process_video(video_path=args.video, max_frames=args.max_frames)

    # Persist JSON output
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    print(f"[Vision Pipeline] Processing complete.")
    print(f"  Processed {result.processed_frames}/{result.total_frames} frames ({result.duration_seconds}s).")
    print(f"  Observations generated: {len(result.traffic_observations)}")
    print(f"  Candidate incidents flagged: {len(result.candidate_incidents)}")
    print(f"  Results saved to: {args.out}")


if __name__ == "__main__":
    main()
