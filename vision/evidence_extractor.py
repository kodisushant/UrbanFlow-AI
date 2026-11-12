"""
UrbanFlow AI - Evidence Extractor (Member 2)
Extracts and persists evidence frames and cropped vehicle snapshots.
Enforces the strict filename patterns required by the project:
  - {incident_id}_frame_{frame_index}.jpg
  - {incident_id}_crop_{track_id1}_{track_id2}.jpg
"""

import os
from typing import List, Optional
from vision.schemas import CandidateIncident, EvidenceItem
from vision.tracker import TrackedVehicle


class EvidenceExtractor:
    """
    Saves annotated full frames and vehicle crops for candidate incidents.
    """
    def __init__(self, output_dir: str = "assets/evidence"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_evidence(
        self,
        incident: CandidateIncident,
        raw_frame,
        tracked_vehicles: List[TrackedVehicle]
    ) -> List[EvidenceItem]:
        """
        Saves the annotated frame and vehicle crop for the candidate incident.
        Attaches EvidenceItem objects to incident.evidence.
        """
        if raw_frame is None:
            return []

        try:
            import cv2
        except ImportError:
            cv2 = None

        evidence_items: List[EvidenceItem] = []
        incident_id = incident.incident_id
        frame_idx = incident.frame_index
        t_sec = incident.video_timestamp_seconds

        # 1. Annotated Full Frame: {incident_id}_frame_{frame_index}.jpg
        frame_filename = f"{incident_id}_frame_{frame_idx}.jpg"
        frame_path = os.path.join(self.output_dir, frame_filename).replace("\\", "/")

        # 2. Vehicle Crop: {incident_id}_crop_{id1}_{id2}.jpg or {incident_id}_crop_{id1}.jpg
        involved_ids = incident.candidate_details.involved_track_ids
        if len(involved_ids) >= 2:
            crop_filename = f"{incident_id}_crop_{involved_ids[0]}_{involved_ids[1]}.jpg"
        elif len(involved_ids) == 1:
            crop_filename = f"{incident_id}_crop_{involved_ids[0]}.jpg"
        else:
            crop_filename = f"{incident_id}_crop_vehicles.jpg"
        crop_path = os.path.join(self.output_dir, crop_filename).replace("\\", "/")

        if cv2 is not None:
            # Draw annotation on a copy
            annotated = raw_frame.copy()
            h, w = annotated.shape[:2]

            involved_vehicles = [v for v in tracked_vehicles if v.track_id in involved_ids]

            # Bounding box for crop calculation
            crop_x1, crop_y1 = w, h
            crop_x2, crop_y2 = 0, 0

            for v in involved_vehicles:
                bx1, by1, bx2, by2 = [int(coord) for coord in v.bbox]
                crop_x1 = max(0, min(crop_x1, bx1 - 30))
                crop_y1 = max(0, min(crop_y1, by1 - 30))
                crop_x2 = min(w, max(crop_x2, bx2 + 30))
                crop_y2 = min(h, max(crop_y2, by2 + 30))

                # Draw red/amber warning box
                cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (0, 69, 255), 2)
                label = f"#{v.track_id} {v.class_name} [CANDIDATE]"
                cv2.putText(annotated, label, (bx1, max(15, by1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 69, 255), 2)

            # Draw banner header
            banner = f"FLAGGED UNVERIFIED: {incident.type} | Score: {incident.heuristic_score} | T: {t_sec:.1f}s"
            cv2.rectangle(annotated, (10, 10), (w - 10, 50), (0, 0, 180), -1)
            cv2.putText(annotated, banner, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Save full frame
            cv2.imwrite(frame_path, annotated)
            evidence_items.append(EvidenceItem(
                evidence_type="annotated_frame",
                file_path=frame_path,
                video_timestamp_seconds=t_sec,
                frame_index=frame_idx
            ))

            # Save cropped region
            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                crop_img = annotated[crop_y1:crop_y2, crop_x1:crop_x2]
                cv2.imwrite(crop_path, crop_img)
                evidence_items.append(EvidenceItem(
                    evidence_type="vehicle_crop",
                    file_path=crop_path,
                    video_timestamp_seconds=t_sec,
                    frame_index=frame_idx
                ))
        else:
            # Fallback if cv2 not installed during isolated unit checks
            evidence_items.append(EvidenceItem(
                evidence_type="annotated_frame",
                file_path=frame_path,
                video_timestamp_seconds=t_sec,
                frame_index=frame_idx
            ))

        incident.evidence = evidence_items
        return evidence_items
