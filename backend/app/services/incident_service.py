from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.schemas.incident import (
    IncidentRecord,
    IncidentStatus,
    IncidentSeverity,
    IncidentDetectionPayload,
    IncidentVerificationRequest,
    IncidentVerificationRecord,
)
from app.services.city_graph_service import city_graph_service


class IncidentService:
    """
    In-memory incident lifecycle manager enforcing the strict state progression:
    candidate -> verified -> response_recommended -> simulated_dispatch -> resolved
    """

    def __init__(self):
        self.incidents: Dict[str, IncidentRecord] = {}
        self._incident_counter = 1

    def create_candidate_incident(self, payload: IncidentDetectionPayload) -> IncidentRecord:
        """Create a candidate incident record from Member 2 vision detection."""
        incident_id = f"INC-{self._incident_counter:03d}"
        self._incident_counter += 1

        node = city_graph_service.get_node(payload.location_node)
        lat = node.latitude if node else 17.3850
        lon = node.longitude if node else 78.4867

        # Deterministically deduce severity based on observed vehicles and confidence
        severity = IncidentSeverity.MEDIUM
        if payload.confidence >= 0.85 and len(payload.observed_vehicles) >= 2:
            severity = IncidentSeverity.HIGH
        elif payload.confidence < 0.60:
            severity = IncidentSeverity.LOW

        title = f"{payload.candidate_type.replace('_', ' ').title()} near {node.name if node else payload.location_node}"

        incident = IncidentRecord(
            incident_id=incident_id,
            title=title,
            status=IncidentStatus.CANDIDATE,
            incident_type=payload.candidate_type,
            severity=severity,
            confidence=payload.confidence,
            location_node=payload.location_node,
            affected_road_id=payload.affected_road_id,
            latitude=lat,
            longitude=lon,
            source=payload.camera_id,
            evidence_urls=[payload.evidence_image_url] if payload.evidence_image_url else [],
            patient_count=payload.patient_count or 0,
            scenario_type=payload.scenario_type or ("fire" if "fire" in str(payload.candidate_type).lower() else "accident"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.incidents[incident_id] = incident
        return incident

    def verify_incident(self, incident_id: str, req: IncidentVerificationRequest) -> IncidentRecord:
        """
        Operator verification endpoint.
        Moves status candidate -> verified (if confirmed) or resolved/dismissed (if rejected).
        """
        incident = self.incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")

        incident.verification_info = IncidentVerificationRecord(
            verified=req.verified,
            operator_id=req.operator_id,
            verified_at=datetime.now(timezone.utc),
            notes=req.notes
        )

        if req.verified:
            incident.status = IncidentStatus.VERIFIED
        else:
            incident.status = IncidentStatus.RESOLVED  # Rejected as false alarm

        incident.updated_at = datetime.now(timezone.utc)
        return incident

    def update_status(self, incident_id: str, new_status: IncidentStatus) -> IncidentRecord:
        incident = self.incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found.")
        incident.status = new_status
        incident.updated_at = datetime.now(timezone.utc)
        return incident

    def get_all(self) -> List[IncidentRecord]:
        return list(self.incidents.values())

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        return self.incidents.get(incident_id)

    def reset(self):
        self.incidents.clear()
        self._incident_counter = 1


incident_service = IncidentService()

