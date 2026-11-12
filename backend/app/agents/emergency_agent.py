from typing import Optional, Dict, Any, Tuple
from app.schemas.incident import IncidentRecord
from app.schemas.resource import EmergencyUnit, ResourceType, ResourceStatus
from app.services.resource_service import resource_service


class EmergencyCoordinationAgent:
    """
    Emergency Coordination Agent.
    Recommends response units based on incident requirements, location, availability, and capabilities.
    """

    def coordinate_response(
        self,
        incident: IncidentRecord,
        recommended_type: ResourceType,
        avoid_road_ids: Optional[set] = None
    ) -> Tuple[Optional[EmergencyUnit], str]:
        """
        Select best unit deterministically via resource_service and generate explanation.
        """
        unit = resource_service.find_best_unit(
            target_node=incident.location_node,
            required_type=recommended_type,
            avoid_road_ids=avoid_road_ids
        )

        if not unit:
            return None, "No available units matching criteria in the active registry."

        reasoning = (
            f"Assigned unit {unit.name} ({unit.unit_id}) from station {unit.station_node}. "
            f"Unit selected for capability match ({', '.join(unit.capabilities[:2])}) and optimal arrival proximity."
        )
        return unit, reasoning


emergency_agent = EmergencyCoordinationAgent()

