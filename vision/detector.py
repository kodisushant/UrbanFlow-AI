"""
UrbanFlow AI - Object Detector Wrapper (Member 2)
Encapsulates YOLO inference supporting PyTorch, ONNX, and OpenVINO backends.
Filters strictly for traffic vehicle classes (car, motorcycle, bus, truck).
"""

import os
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


# Target COCO class mapping for vehicles:
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


@dataclass
class Detection:
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    class_id: int
    class_name: str


class VehicleDetector:
    """
    Inference wrapper for YOLO vehicle detection.
    Supports PyTorch (.pt), ONNX (.onnx), and OpenVINO model formats.
    """
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.25,
        device: str = "cpu"
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
        except Exception as e:
            # Model will be loaded on demand or user will run benchmark/install
            self.model = None
            self._load_error = str(e)

    def detect(self, frame) -> List[Detection]:
        """
        Runs object detection on a single frame (numpy BGR image).
        Returns list of Detection objects filtered for vehicles.
        """
        if self.model is None:
            self._load_model()
            if self.model is None:
                return []

        # Target only vehicle class IDs: [2, 3, 5, 7]
        target_ids = list(VEHICLE_CLASSES.keys())

        results = self.model.predict(
            source=frame,
            classes=target_ids,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False
        )

        detections: List[Detection] = []
        if not results:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)

        for i in range(len(xyxy)):
            cls_id = int(classes[i])
            cls_name = VEHICLE_CLASSES.get(cls_id, "vehicle")
            det = Detection(
                bbox=(float(xyxy[i][0]), float(xyxy[i][1]), float(xyxy[i][2]), float(xyxy[i][3])),
                confidence=float(confs[i]),
                class_id=cls_id,
                class_name=cls_name
            )
            detections.append(det)

        return detections
