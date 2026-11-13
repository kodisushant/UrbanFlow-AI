from typing import Dict, List, Optional
from app.schemas.resource import EmergencyUnit, ResourceType, ResourceStatus
from app.services.city_graph_service import city_graph_service


class ResourceService:
    """
    Emergency response resource registry and deterministic unit allocator
    synchronized with Member 4's Cyber City fleet.
    """

    def __init__(self):
        self.units: Dict[str, EmergencyUnit] = {}
        self.initialize_default_units()

    def initialize_default_units(self):
        self.units.clear()

        def get_pos(node_id: str):
            node = city_graph_service.get_node(node_id)
            if node:
                return node.latitude, node.longitude
            return 17.4420, 78.3800

        p_amb1 = get_pos("INT-04")
        p_amb2 = get_pos("INT-13")
        p_fire = get_pos("INT-07")
        p_pol1 = get_pos("INT-05")
        p_pol2 = get_pos("INT-11")

        default_fleet = [
            EmergencyUnit(
                unit_id="AMB-01",
                name="Medic One ALS",
                call_sign="Medic One ALS",
                unit_type="ambulance",
                status="available",
                station_node="INT-04",
                current_node="INT-04",
                latitude=p_amb1[0],
                longitude=p_amb1[1],
                capabilities=["advanced_life_support", "paramedic_crew", "ventilator", "defibrillator"],
                speed_kmph=55.0
            ),
            EmergencyUnit(
                unit_id="AMB-02",
                name="South Apex Medic",
                call_sign="South Apex Medic",
                unit_type="ambulance",
                status="available",
                station_node="INT-13",
                current_node="INT-13",
                latitude=p_amb2[0],
                longitude=p_amb2[1],
                capabilities=["basic_life_support", "emergency_transport"],
                speed_kmph=50.0
            ),
            EmergencyUnit(
                unit_id="FIRE-01",
                name="Tower Rescue 7",
                call_sign="Tower Rescue 7",
                unit_type="fire_engine",
                status="available",
                station_node="INT-07",
                current_node="INT-07",
                latitude=p_fire[0],
                longitude=p_fire[1],
                capabilities=["water_tender", "hydraulic_rescue_cutters", "ladder", "hazmat_containment"],
                speed_kmph=45.0
            ),
            EmergencyUnit(
                unit_id="POLICE-01",
                name="Highway Patrol Alpha",
                call_sign="Patrol Alpha",
                unit_type="police_patrol",
                status="available",
                station_node="INT-05",
                current_node="INT-05",
                latitude=p_pol1[0],
                longitude=p_pol1[1],
                capabilities=["traffic_control", "perimeter_security", "incident_investigation"],
                speed_kmph=60.0
            ),
            EmergencyUnit(
                unit_id="POLICE-02",
                name="East Patrol Delta",
                call_sign="East Patrol Delta",
                unit_type="police_patrol",
                status="available",
                station_node="INT-11",
                current_node="INT-11",
                latitude=p_pol2[0],
                longitude=p_pol2[1],
                capabilities=["rapid_response", "crowd_diversion", "motorcycle_escort"],
                speed_kmph=65.0
            )
        ]

        for u in default_fleet:
            self.units[u.unit_id] = u
        # Register alias POL-01 -> POLICE-01
        self.units["POL-01"] = self.units["POLICE-01"]

    def get_all_units(self) -> List[EmergencyUnit]:
        # Return unique units by unit_id
        seen = set()
        result = []
        for u in self.units.values():
            if u.unit_id not in seen:
                seen.add(u.unit_id)
                result.append(u)
        return result

    def get_unit(self, unit_id: str) -> Optional[EmergencyUnit]:
        if unit_id in self.units:
            return self.units[unit_id]
        if unit_id == "POL-01":
            return self.units.get("POLICE-01")
        return None

    def update_unit_status(
        self,
        unit_id: str,
        status: str,
        incident_id: Optional[str] = None
    ) -> Optional[EmergencyUnit]:
        unit = self.get_unit(unit_id)
        if unit:
            unit.status = status
            if incident_id is not None:
                unit.assigned_incident_id = incident_id
        return unit

    def find_best_unit(
        self,
        target_node: str,
        required_type: str,
        avoid_road_ids: Optional[set] = None
    ) -> Optional[EmergencyUnit]:
        """
        Deterministic unit matching: Finds closest available unit of required_type
        by calculating shortest travel time using city_graph_service.
        """
        req_norm = required_type.lower()
        if "fire" in req_norm:
            type_match = ["fire_engine", "fire_truck"]
        elif "police" in req_norm or "patrol" in req_norm:
            type_match = ["police_patrol", "police_cruiser", "police"]
        else:
            type_match = ["ambulance"]

        available_candidates = [
            u for u in self.get_all_units()
            if any(t in u.unit_type.lower() for t in type_match) and u.status in ["available", "stationed"]
        ]

        if not available_candidates:
            available_candidates = [u for u in self.get_all_units() if u.status in ["available", "stationed"]]

        if not available_candidates:
            return None

        best_unit = None
        best_travel_time = float("inf")

        for u in available_candidates:
            path = city_graph_service.find_shortest_path(
                u.current_node,
                target_node,
                avoid_road_ids=avoid_road_ids,
                algorithm="astar"
            )
            travel_time = path.estimated_travel_time_seconds if path else float("inf")
            if travel_time < best_travel_time:
                best_travel_time = travel_time
                best_unit = u

        return best_unit or available_candidates[0]


resource_service = ResourceService()
