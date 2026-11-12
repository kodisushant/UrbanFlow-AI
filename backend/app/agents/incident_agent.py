from typing import Dict, Any, Tuple
from app.schemas.incident import IncidentRecord, IncidentSeverity
from app.schemas.resource import ResourceType


class IncidentAgent:
    """
    Incident Analysis Agent.
    Evaluates candidate events against strict criteria and generates factual,
    evidence-backed incident summaries without hallucinating details.
    """

    def analyze_candidate(self, incident: IncidentRecord) -> Tuple[str, ResourceType, str]:
        """
        Analyze incident facts and determine recommended service type and structured report.
        Returns: (severity_assessment, recommended_service, structured_report)
        """
        # Determine recommended emergency service strictly from incident type & observations
        itype = incident.incident_type.lower()
        if "collision" in itype or "accident" in itype or "crash" in itype:
            rec_service = ResourceType.AMBULANCE
            action_desc = "Dispatching emergency medical services and paramedic triage."
        elif "fire" in itype or "spill" in itype or "hazard" in itype:
            rec_service = ResourceType.FIRE_TRUCK
            action_desc = "Dispatching heavy extrication and fire hazard suppression."
        else:
            rec_service = ResourceType.POLICE_CRUISER
            action_desc = "Dispatching traffic enforcement and roadblock perimeter unit."

        # Structured report strictly adhering to verified facts
        report = (
            f"INCIDENT REPORT [{incident.incident_id}]\n"
            f"Location: Intersection {incident.location_node} (Lat: {incident.latitude}, Lon: {incident.longitude})\n"
            f"Detected Event: {incident.title}\n"
            f"Sensor Source: {incident.source} | Confidence Score: {incident.confidence:.1%}\n"
            f"Current Verification Status: {incident.status.value.upper()}\n"
            f"Recommended Primary Service: {rec_service.value.upper()}\n"
            f"Protocol: {action_desc}\n"
            f"Notice: Prototype simulation record. Awaiting human confirmation before physical dispatch."
        )

        severity_summary = f"{incident.severity.value.upper()} priority incident verified at {incident.location_node}."
        return severity_summary, rec_service, report


incident_agent = IncidentAgent()

