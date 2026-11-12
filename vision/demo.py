"""
UrbanFlow AI - Interactive CCTV Vision Demo (Member 2)
Runs vehicle detection, tracking, and incident detection on video.
Renders real-time visual overlays including ROI polygons, vehicle tracks,
relative speeds, and flagged candidate incidents.

Includes --no-display flag for headless or automated testing environments.
"""

import argparse
import os
import sys
import time

from vision.config import CameraConfig, IncidentThresholdConfig
from vision.detector import VehicleDetector
from vision.evidence_extractor import EvidenceExtractor
from vision.incident_detector import IncidentDetector
from vision.schemas import VideoAnalysisResult
from vision.traffic_analyzer import TrafficAnalyzer
from vision.tracker import VehicleTracker


def run_demo(
    video_path: str,
    config_path: str,
    model_path: str = "yolov8n.pt",
    frame_stride: int = 2,
    no_display: bool = False,
    evidence_dir: str = "assets/evidence",
    out_json: str = "assets/demo_results.json",
    max_frames: int = None
):
    try:
        import cv2
    except ImportError:
        print("[Demo Error] opencv-python is not installed. Please run: pip install -r requirements-vision.txt")
        sys.exit(1)

    if not os.path.exists(video_path):
        print(f"[Demo Error] Video file not found: {video_path}")
        sys.exit(1)

    camera_config = CameraConfig.from_file(config_path) if os.path.exists(config_path) else CameraConfig(is_calibrated_zones=False)
    detector = VehicleDetector(model_path=model_path, device="cpu")
    tracker = VehicleTracker(max_history_seconds=6.0)
    analyzer = TrafficAnalyzer(camera_config=camera_config, sample_duration_seconds=3.0)
    incident_detector = IncidentDetector(camera_config=camera_config)
    evidence_extractor = EvidenceExtractor(output_dir=evidence_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[Demo Error] Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    observations = []
    incidents = []
    frame_idx = 0
    processed_count = 0

    print(f"\n=======================================================")
    print(f"UrbanFlow AI - CCTV Analysis Module (Member 2)")
    print(f"Video: {video_path} ({total_frames} frames @ {fps:.1f} FPS)")
    print(f"Camera ID: {camera_config.camera_id} | Calibrated: {camera_config.is_calibrated_zones}")
    print(f"Display Mode: {'Headless (--no-display)' if no_display else 'GUI Window Active'}")
    print(f"=======================================================\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if max_frames and frame_idx >= max_frames:
            break

        if frame_idx % frame_stride != 0:
            frame_idx += 1
            continue

        processed_count += 1
        t_sec = frame_idx / fps

        # 1. Detection
        detections = detector.detect(frame)

        # 2. Tracking
        tracked = tracker.update_fallback_iou(detections, t_sec, frame_idx)

        # 3. Traffic Observation
        if analyzer.should_emit_observation(t_sec):
            obs = analyzer.generate_observation(tracked, t_sec, frame_idx)
            observations.append(obs)

        # 4. Incident Evaluation
        new_incidents = incident_detector.evaluate_frame(tracked, t_sec, frame_idx)
        for inc in new_incidents:
            evidence_extractor.extract_evidence(inc, frame, tracked)
            incidents.append(inc)
            print(f"\n[ALERT] Candidate Incident Flagged at T={t_sec:.1f}s:")
            print(f"  ID: {inc.incident_id} | Type: {inc.type} | Heuristic Score: {inc.heuristic_score}")
            print(f"  Reason: {inc.candidate_details.detection_reason}")

        # Visual Rendering (if display enabled)
        if not no_display:
            display_frame = frame.copy()
            h, w = display_frame.shape[:2]

            # Draw ROI and Stop-Line Polygons if calibrated
            if camera_config.is_calibrated_zones:
                if camera_config.roi_polygon:
                    import numpy as np
                    pts = np.array(camera_config.roi_polygon, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(display_frame, [pts], isClosed=True, color=(255, 200, 0), thickness=2)
                if camera_config.stop_line_zone:
                    import numpy as np
                    pts = np.array(camera_config.stop_line_zone, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(display_frame, [pts], isClosed=True, color=(0, 255, 255), thickness=2)

            # Draw tracked vehicles
            for v in tracked:
                bx1, by1, bx2, by2 = [int(c) for c in v.bbox]
                pt = v.latest_point
                color = (0, 255, 0) if pt.speed_bbox_widths_per_sec > 0.10 else (0, 165, 255)
                cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), color, 2)
                label = f"#{v.track_id} {v.class_name} | {pt.speed_bbox_widths_per_sec:.2f} bw/s"
                cv2.putText(display_frame, label, (bx1, max(15, by1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            # Status Overlay
            status_text = f"T: {t_sec:.1f}s | Frame: {frame_idx} | Tracks: {len(tracked)} | Incidents: {len(incidents)}"
            cv2.rectangle(display_frame, (5, 5), (550, 40), (0, 0, 0), -1)
            cv2.putText(display_frame, status_text, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow("UrbanFlow AI - CCTV Analysis", display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[Demo] Stopped by user.")
                break

        frame_idx += 1

    cap.release()
    if not no_display:
        cv2.destroyAllWindows()

    result = VideoAnalysisResult(
        video_file=video_path,
        camera_id=camera_config.camera_id,
        road_id=camera_config.road_id,
        total_frames=total_frames,
        processed_frames=processed_count,
        fps=round(fps, 2),
        duration_seconds=round(total_frames / fps, 2) if fps > 0 else 0.0,
        frame_stride=frame_stride,
        camera_config_calibrated=camera_config.is_calibrated_zones,
        traffic_observations=observations,
        candidate_incidents=incidents
    )

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    print(f"\n[Demo Complete] Results saved to '{out_json}'. Flagged incidents: {len(incidents)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UrbanFlow AI - CCTV Demo Runner")
    parser.add_argument("--video", type=str, required=True, help="Video file path")
    parser.add_argument("--config", type=str, default="assets/camera_configs/cctv_camera_01.json", help="Camera config JSON")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO model path")
    parser.add_argument("--frame-stride", type=int, default=2, help="Frame stride")
    parser.add_argument("--no-display", action="store_true", help="Run without graphical display window")
    parser.add_argument("--evidence-dir", type=str, default="assets/evidence", help="Evidence output folder")
    parser.add_argument("--out", type=str, default="assets/demo_results.json", help="Output JSON path")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames")
    args = parser.parse_args()

    run_demo(
        video_path=args.video,
        config_path=args.config,
        model_path=args.model,
        frame_stride=args.frame_stride,
        no_display=args.no_display,
        evidence_dir=args.evidence_dir,
        out_json=args.out,
        max_frames=args.max_frames
    )
