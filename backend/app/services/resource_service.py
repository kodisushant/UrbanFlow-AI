from typing import Dict, List, Optional
from app.schemas.resource import EmergencyUnit, ResourceType, ResourceStatus
from app.services.city_graph_service import city_graph_service


class ResourceService:
    """
    Emergency response resource registry and deterministic unit allocator.
    """

    def __init__(self):
        self.units: Dict[str, EmergencyUnit] = {}
        self.initialize_default_units()

    def initialize_default_units(self):
        self.units.clear()
        
        # Helper to get lat/lon for node
        def get_pos(node_id: str):
            node = city_graph_service.get_node(node_id)
            if node:
                return node.latitude, node.longitude
            return 17.3850, 78.4867

        p1 = get_pos("NODE-02")  # Hospital Junction
        p2 = get_pos("NODE-10")  # East Terminal
        p3 = get_pos("NODE-08")  # Civic Center
        p4 = get_pos("NODE-01")  # North Gate
        p5 = get_pos("NODE-14")  # Industrial Belt

        default_fleet = [
            EmergencyUnit(
                unit_id="AMB-01",
                name="RescueMedic 1",
                unit_type=ResourceType.AMBULANCE,
                status=ResourceStatus.AVAILABLE,
                station_node="NODE-02",
                current_node="NODE-02",
                latitude=p1[0],
                longitude=p1[1],
                capabilities=["advanced_cardiac_life_support", "paramedic_triage"],
                speed_kmph=55.0
            ),
            EmergencyUnit(
                unit_id="AMB-02",
                name="RapidResponse 2",
                unit_type=ResourceType.AMBULANCE,
                status=ResourceStatus.AVAILABLE,
                station_node="NODE-10",
                current_node="NODE-10",
                latitude=p2[0],
                longitude=p2[1],
                capabilities=["basic_life_support", "trauma_stabilization"],
                speed_kmph=50.0
            ),
            EmergencyUnit(
                unit_id="FIRE-01",
                name="Engine 7",
                unit_type=ResourceType.FIRE_TRUCK,
                status=ResourceStatus.AVAILABLE,
                station_node="NODE-08",
                current_node="NODE-08",
                latitude=p3[0],
                longitude=p3[1],
                capabilities=["vehicle_extrication", "chemical_hazard_control", "foam_suppression"],
                speed_kmph=45.0
            ),
            EmergencyUnit(
                unit_id="POLICE-01",
                name="Patrol Alpha",
                unit_type=ResourceType.POLICE_CRUISER,
                status=ResourceStatus.AVAILABLE,
                station_node="NODE-01",
                current_node="NODE-01",
                latitude=p4[0],
                longitude=p4[1],
                capabilities=["traffic_containment", "perimeter_lockdown"],
                speed_kmph=60.0
            ),
            EmergencyUnit(
                unit_id="POLICE-02",
                name="Highway Interceptor 4",
                unit_type=ResourceType.POLICE_CRUISER,
                status=ResourceStatus.AVAILABLE,
                station_node="NODE-14",
                current_node="NODE-14",
                latitude=p5[0],
                longitude=p5[1],
                capabilities=["express_escort", "accident_investigation"],
                speed_kmph=65.0
            )
        ]

        for u in default_fleet:
            self.units[u.unit_id] = u

    def get_all_units(self) -> List[EmergencyUnit]:
        return list(self.units.values())

    def get_unit(self, unit_id: str) -> Optional[EmergencyUnit]:
        return self.units.get(unit_id)

    def update_unit_status(
        self,
        unit_id: str,
        status: ResourceStatus,
        incident_id: Optional[str] = None
    ) -> Optional[EmergencyUnit]:
        unit = self.units.get(unit_id)
        if unit:
            unit.status = status
            if incident_id is not None:
                unit.assigned_incident_id = incident_id
        return unit

    def find_best_unit(
        self,
        target_node: str,
        required_type: ResourceType,
        avoid_road_ids: Optional[set] = None
    ) -> Optional[EmergencyUnit]:
        """
        Deterministic unit matching: Finds the closest available unit of required_type
        by calculating shortest travel time using city_graph_service.
        """
        available_candidates = [
            u for u in self.units.values()
            if u.unit_type == required_type and u.status == ResourceStatus.AVAILABLE
        ]

        if not available_candidates:
            # Fallback to any available unit if none of strict type
            available_candidates = [u for u in self.units.values() if u.status == ResourceStatus.AVAILABLE]

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

