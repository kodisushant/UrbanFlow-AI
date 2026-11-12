# UrbanFlow AI — Computer Vision & CCTV Module (Member 2)

**Module Owner:** Member 2 — Computer Vision & Deep Learning Engineer  
**Role:** Real-time video ingestion, vehicle detection, multi-object tracking, traffic density observations, and conservative candidate incident/blockage detection.

---

## 1. Overview & Architecture

The Vision module processes CCTV traffic footage to extract continuous traffic intelligence and candidate incidents. It is specifically designed to operate with high efficiency on CPU hardware (e.g. Intel Core i5/i7) without requiring a dedicated GPU or heavy model fine-tuning.

```
UrbanFlow/
├── vision/
│   ├── __init__.py             # Public module exports
│   ├── schemas.py              # Single return contract (Pydantic models)
│   ├── config.py               # Camera spatial config & configurable thresholds
│   ├── detector.py             # Pretrained YOLO vehicle detector (COCO classes 2, 3, 5, 7)
│   ├── tracker.py              # Multi-object tracker & track state management
│   ├── kinematics.py           # Real-elapsed-time speed & heading change tracker
│   ├── traffic_analyzer.py     # Density, count breakdown, and flow rate aggregation
│   ├── incident_detector.py    # Strict 4-factor candidate collision & blockage heuristics
│   ├── evidence_extractor.py   # Full-frame & vehicle-crop snapshot persistence
│   ├── benchmark.py            # Real FPS & RAM benchmark (PyTorch vs ONNX vs OpenVINO)
│   ├── pipeline.py             # Central pipeline orchestrator (CLI & Python API)
│   ├── demo.py                 # Interactive visual player (--no-display for headless)
│   └── README.md
├── assets/
│   ├── camera_configs/         # Per-camera ROI, lane, and stop-line JSON configs
│   │   ├── cctv_camera_01.json
│   │   └── default_camera_config.json
│   ├── sample_videos/          # Pre-recorded CCTV test videos
│   └── evidence/               # Extracted JPEG evidence snapshots
└── requirements-vision.txt
```

---

## 2. Setup & Installation

Dependencies are isolated in `requirements-vision.txt`:

```bash
# 1. Install dependencies
pip install -r requirements-vision.txt

# Or for CPU-only PyTorch:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install opencv-python ultralytics pydantic pyyaml psutil
```

---

## 3. Running the Runtime Benchmark

Before processing, measure real FPS and memory on your hardware:

```bash
python -m vision.benchmark --model yolov8n.pt --iterations 40 --out assets/benchmark_results.json
```

- Measures real inference latency (ms/frame) and true FPS without hardcoded estimates.
- Records process peak RSS RAM consumption via `psutil`.
- Attempts export and execution across PyTorch CPU, ONNX Runtime, and OpenVINO.
- Selects the fastest available engine by default for subsequent runs.

---

## 4. Running the Vision Pipeline (CLI)

The pipeline can run as an independent background process that outputs structured JSON files for Member 1's backend:

```bash
python -m vision.pipeline \
  --video assets/sample_videos/demo.mp4 \
  --config assets/camera_configs/cctv_camera_01.json \
  --frame-stride 2 \
  --out assets/vision_results.json \
  --evidence-dir assets/evidence
```

### Options:
- `--video`: Path to MP4/AVI traffic video.
- `--config`: Camera configuration JSON specifying ROI and stop-line zones.
- `--frame-stride`: Process every $N$-th frame (default: 2, cuts CPU load by ~50%).
- `--out`: Destination file path for full Pydantic analysis JSON.
- `--evidence-dir`: Destination directory for evidence snapshots.

---

## 5. Running the Interactive Demo

To visualize detections, bounding boxes, relative speeds, and candidate alerts in real time:

```bash
# Graphical window with live bounding boxes and overlays
python -m vision.demo --video assets/sample_videos/demo.mp4 --config assets/camera_configs/cctv_camera_01.json

# Headless mode (no GUI window, safe for background servers or automated tests)
python -m vision.demo --video assets/sample_videos/demo.mp4 --no-display
```

---

## 6. Python API (Direct Integration for Member 1)

Member 1 can import the pipeline directly in Python:

```python
from vision.pipeline import TrafficVisionPipeline

pipeline = TrafficVisionPipeline(
    model_path="yolov8n.pt",
    config_path="assets/camera_configs/cctv_camera_01.json",
    frame_stride=2,
    device="cpu"
)

# Process video and receive validated Pydantic model
result = pipeline.process_video("assets/sample_videos/demo.mp4")

# Access periodic observations and flagged incidents
for obs in result.traffic_observations:
    print(f"Time: {obs.video_timestamp_seconds}s | Count: {obs.vehicle_count} | Congestion: {obs.congestion_level}")

for inc in result.candidate_incidents:
    print(f"Candidate: {inc.incident_id} | Score: {inc.heuristic_score} | Reason: {inc.candidate_details.detection_reason}")
```

---

## 7. Strict Conservative Heuristics

### A. Candidate Collision Heuristic
A potential collision is **never** declared merely because two vehicles stop near each other. All 4 independent criteria must be satisfied simultaneously:
1. **Abrupt Stop of Both Vehicles:** Both candidate vehicles must have been moving above relative speed threshold ($v_{\text{rel}} \ge 0.50$ bbox-widths/sec) and dropped $\ge 75\%$ speed within $\le 1.2$ seconds.
2. **Heading / Trajectory Change:** At least one vehicle exhibits an angular deflection $\ge 20^\circ$ right before stopping.
3. **Surrounding Traffic Still Moving:** At least 1 other vehicle on the road continues moving, eliminating false positives caused by red traffic lights or uniform traffic waves.
4. **Persistence Outside Normal Queue:** Neither vehicle is inside the designated `stop_line_zone` or `normal_queue_polygon`, and both remain stationary for $\ge 3.0$ seconds.

### B. Road Blockage Heuristic
Flags an active lane obstruction when a single vehicle remains stationary outside the stop-line zone for $\ge 12.0$ seconds while surrounding traffic flows or queues behind it.

### C. Hand-Weighted Heuristic Score
- Renamed from "confidence" to `heuristic_score`.
- Capped strictly at `0.85` (maximum value 0.85).
- If an uncalibrated camera config is used (no ROI/stop line defined), a penalty factor of `0.70` is applied to reflect higher uncertainty.

---

## 8. Evidence File Naming Standards

Evidence snapshots follow the strict naming conventions:
- **Full Annotated Frame:** `assets/evidence/{incident_id}_frame_{frame_index}.jpg`  
  *(e.g., `INC-CCTV-001_frame_426.jpg`)*
- **Cropped Involved Vehicles:** `assets/evidence/{incident_id}_crop_{track_id1}_{track_id2}.jpg`  
  *(e.g., `INC-CCTV-001_crop_14_19.jpg`)*

---

## 9. KNOWN_LIMITATIONS

1. **COCO Class Coverage (No Auto-Rickshaw / Three-Wheeler):**
   - The pretrained COCO dataset includes `car`, `motorcycle`, `bus`, and `truck`. It does **not** contain an explicit `auto-rickshaw` or `three-wheeler` class (common in Indian and Southeast Asian urban traffic).
   - Auto-rickshaws are typically detected as `car` or `motorcycle` with lower confidence.
2. **No Automated Incident Verification:**
   - **No incident flagged by this module is verified.** All candidate events carry `"status": "detected_unverified"` and `"verification_required": true`.
   - Severity is permanently set to `"unknown"`. Final verification and severity classification belong exclusively to a human traffic operator or Member 1's backend orchestration agents.
3. **Absence of Metric Calibration:**
   - Because real-world CCTV cameras lack intrinsic/extrinsic metric calibration grids, all speeds and accelerations are **strictly relative** (measured in `pixels_per_second` and `bbox_widths_per_second`). They must not be interpreted as absolute km/h or miles/hour.
4. **Occlusion & Low Lighting:**
   - Dense traffic occlusion, glare, or severe night-time shadows may cause track ID fragmentation. The tracker utilizes an IoU/Kalman association window to mitigate track drops.
