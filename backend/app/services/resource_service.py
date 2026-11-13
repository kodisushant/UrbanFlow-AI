import time
import math
from typing import Dict, List, Optional, Set
from app.schemas.resource import EmergencyUnit, ResourceType, ResourceStatus
from app.services.city_graph_service import city_graph_service

DISPATCH_RULES = {
    "accident": {
        "ambulance": 1,
        "police_patrol": 1
    },
    "fire": {
        "fire_truck": 1,
        "ambulance": 1,
        "police_patrol": 1
    }
}


class ResourceService:
    """
    Emergency response resource registry and deterministic unit allocator
    synchronized with Member 4's Cyber City fleet.
    Enforces the complete tick-based Unit State Machine.
    """

    def __init__(self):
        self.units: Dict[str, EmergencyUnit] = {}
        self.initialize_default_units()

    @staticmethod
    def normalize_unit_type(raw_type: str) -> str:
        t = str(raw_type).lower()
        if "fire" in t:
            return "fire_engine"
        if "police" in t or "patrol" in t or "cruiser" in t:
            return "police_patrol"
        return "ambulance"

    def initialize_default_units(self):
        self.units.clear()

        def get_pos(node_id: str):
            node = city_graph_service.get_node(node_id)
            if node:
                return node.latitude, node.longitude
            return 17.4420, 78.3800

        p_amb1 = get_pos("INT-20")
        p_amb2 = get_pos("INT-18")
        p_amb3 = get_pos("INT-11")
        p_fire1 = get_pos("INT-07")
        p_fire2 = get_pos("INT-02")
        p_fire3 = get_pos("INT-07")
        p_pol1 = get_pos("INT-05")
        p_pol2 = get_pos("INT-11")

        default_fleet = [
            EmergencyUnit(
                unit_id="AMB-01",
                name="Medic One ALS",
                call_sign="Medic One ALS",
                unit_type="ambulance",
                status="available",
                station_node="INT-20",
                current_node="INT-20",
                home_hospital_node="INT-04",
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
                station_node="INT-18",
                current_node="INT-18",
                home_hospital_node="INT-13",
                latitude=p_amb2[0],
                longitude=p_amb2[1],
                capabilities=["basic_life_support", "emergency_transport"],
                speed_kmph=50.0
            ),
            EmergencyUnit(
                unit_id="AMB-03",
                name="East Trauma Medic 3",
                call_sign="East Trauma Medic 3",
                unit_type="ambulance",
                status="available",
                station_node="INT-11",
                current_node="INT-11",
                home_hospital_node="INT-10",
                latitude=p_amb3[0],
                longitude=p_amb3[1],
                capabilities=["trauma_care", "emergency_transport"],
                speed_kmph=55.0
            ),
            EmergencyUnit(
                unit_id="FIRE-01",
                name="Tower Rescue 7",
                call_sign="Tower Rescue 7",
                unit_type="fire_engine",
                status="available",
                station_node="INT-07",
                current_node="INT-07",
                latitude=p_fire1[0],
                longitude=p_fire1[1],
                capabilities=["water_tender", "hydraulic_rescue_cutters", "ladder", "hazmat_containment"],
                speed_kmph=48.0
            ),
            EmergencyUnit(
                unit_id="FIRE-02",
                name="Metro Pumper 12",
                call_sign="Metro Pumper 12",
                unit_type="fire_engine",
                status="available",
                station_node="INT-02",
                current_node="INT-02",
                latitude=p_fire2[0],
                longitude=p_fire2[1],
                capabilities=["water_cannon", "pumper", "foam_suppression"],
                speed_kmph=50.0
            ),
            EmergencyUnit(
                unit_id="FIRE-03",
                name="Hazard Ladder 03",
                call_sign="Hazard Ladder 03",
                unit_type="fire_engine",
                status="available",
                station_node="INT-07",
                current_node="INT-07",
                latitude=p_fire3[0],
                longitude=p_fire3[1],
                capabilities=["aerial_ladder", "smoke_ejection", "high_angle_rescue"],
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
        self.units["POL-01"] = self.units["POLICE-01"]

    def is_mission_in_progress(self) -> bool:
        """Returns True if any unit is busy with an active incident mission."""
        return any(u.status not in ["available", "stationed"] for u in self.get_all_units())

    def get_all_units(self) -> List[EmergencyUnit]:
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

    def find_nearest_available_units(
        self,
        target_node: str,
        required_type: str,
        count: int = 1,
        avoid_road_ids: Optional[Set[str]] = None
    ) -> List[EmergencyUnit]:
        """
        Picks the nearest AVAILABLE units by shortest-path travel time (A*).
        Never reassigns a busy unit.
        """
        norm_req = self.normalize_unit_type(required_type)
        available_candidates = [
            u for u in self.get_all_units()
            if self.normalize_unit_type(u.unit_type) == norm_req and u.status in ["available", "stationed"]
        ]

        scored_candidates = []
        for u in available_candidates:
            path = city_graph_service.find_shortest_path(
                origin_node=u.current_node,
                destination_node=target_node,
                avoid_road_ids=avoid_road_ids,
                algorithm="astar",
                allow_destination_access=True
            )
            travel_time = path.estimated_travel_time_seconds if path else float("inf")
            scored_candidates.append((travel_time, u))

        # Sort by travel time ascending
        scored_candidates.sort(key=lambda x: x[0])
        return [unit for time_cost, unit in scored_candidates if time_cost < float("inf")][:count]

    def find_best_unit(
        self,
        target_node: str,
        required_type: str,
        avoid_road_ids: Optional[set] = None
    ) -> Optional[EmergencyUnit]:
        units = self.find_nearest_available_units(target_node, required_type, count=1, avoid_road_ids=avoid_road_ids)
        return units[0] if units else None

    @staticmethod
    def _haversine(p1: List[float], p2: List[float]) -> float:
        r = 6371000.0
        phi1, phi2 = math.radians(p1[0]), math.radians(p2[0])
        dphi = math.radians(p2[0] - p1[0])
        dlam = math.radians(p2[1] - p1[1])
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def dispatch_unit_with_route(
        self,
        unit_id: str,
        incident_id: str,
        target_node: str,
        route_geometry: List[List[float]],
        eta_seconds: int,
        total_distance_meters: float
    ) -> Optional[EmergencyUnit]:
        unit = self.get_unit(unit_id)
        if not unit:
            return None
        unit.status = ResourceStatus.EN_ROUTE.value
        unit.assigned_incident_id = incident_id
        unit.target_node = target_node
        unit.route_geometry = route_geometry
        unit.dispatch_timestamp = time.time()
        unit.eta_seconds = eta_seconds
        unit.total_route_distance_meters = total_distance_meters
        unit.total_route_duration_seconds = float(eta_seconds)
        unit.phase_start_time = None
        unit.phase_duration_seconds = None
        if route_geometry:
            unit.latitude = route_geometry[0][0]
            unit.longitude = route_geometry[0][1]
        return unit

    def tick(self, speed_multiplier: float = 6.0, current_time: Optional[float] = None) -> List[EmergencyUnit]:
        """
        Universal Unit State Machine:
        Ambulance: available -> en_route -> on_scene -> loading (timed ~5s) -> transporting -> at_hospital (brief ~4s) -> returning -> available
        Fire/Police: available -> en_route -> on_scene (timed ~8s) -> returning -> available
        """
        now = current_time if current_time is not None else time.time()
        phase_speed = 1.0 if current_time is not None else speed_multiplier

        from app.agents.coordinator import workflow_coordinator
        from app.services.incident_service import incident_service
        from app.schemas.route import RouteResult

        active_inc = workflow_coordinator.state.active_incident

        for unit in self.get_all_units():
            if unit.status in ["available", "stationed"]:
                continue

            # -------------------------------------------------------------
            # 1. EN_ROUTE (Traveling towards incident location)
            # -------------------------------------------------------------
            if unit.status == ResourceStatus.EN_ROUTE.value:
                if not unit.route_geometry or len(unit.route_geometry) < 2:
                    unit.status = ResourceStatus.ON_SCENE.value
                    unit.current_node = unit.target_node or unit.current_node
                    unit.eta_seconds = 0
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 1.0 if unit.unit_type == "ambulance" else 8.0
                    continue

                if unit.dispatch_timestamp is None:
                    unit.dispatch_timestamp = now

                elapsed = max(0.0, now - unit.dispatch_timestamp)
                speed_mps = (unit.speed_kmph * 1000.0 / 3600.0) * speed_multiplier
                dist_traveled = elapsed * speed_mps

                seg_lens = [self._haversine(unit.route_geometry[i - 1], unit.route_geometry[i]) for i in range(1, len(unit.route_geometry))]
                total_dist = sum(seg_lens)

                if total_dist <= 0 or dist_traveled >= total_dist:
                    unit.latitude = unit.route_geometry[-1][0]
                    unit.longitude = unit.route_geometry[-1][1]
                    unit.current_node = unit.target_node or unit.current_node
                    unit.status = ResourceStatus.ON_SCENE.value
                    unit.eta_seconds = 0
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 1.0 if unit.unit_type == "ambulance" else 8.0

                    workflow_coordinator.log_agent_action(
                        agent_name="EmergencyAgent",
                        role="On-Scene Triage",
                        action=f"{unit.call_sign} Arrived On Scene",
                        summary=f"{unit.call_sign} arrived at incident {unit.current_node}. Establishing scene response.",
                        details={"unit_id": unit.unit_id, "status": "on_scene"}
                    )
                    if active_inc and active_inc.status != "on_scene":
                        incident_service.update_status(active_inc.incident_id, "on_scene")
                        workflow_coordinator.state.status = "on_scene"
                        workflow_coordinator.state.stage = "on_scene_triage"
                else:
                    rem_dist = max(0.0, total_dist - dist_traveled)
                    unit.eta_seconds = max(1, int(rem_dist / speed_mps))
                    accum = 0.0
                    for i, slen in enumerate(seg_lens):
                        if accum + slen >= dist_traveled:
                            t = (dist_traveled - accum) / slen if slen > 0 else 0.0
                            unit.latitude = unit.route_geometry[i][0] + t * (unit.route_geometry[i + 1][0] - unit.route_geometry[i][0])
                            unit.longitude = unit.route_geometry[i][1] + t * (unit.route_geometry[i + 1][1] - unit.route_geometry[i][1])
                            break
                        accum += slen

            # -------------------------------------------------------------
            # 2. ON_SCENE (At incident location)
            # -------------------------------------------------------------
            elif unit.status == ResourceStatus.ON_SCENE.value:
                if unit.phase_start_time is None:
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 1.0 if unit.unit_type == "ambulance" else 8.0

                elapsed_phase = (now - unit.phase_start_time) * phase_speed
                if elapsed_phase >= (unit.phase_duration_seconds or 1.0):
                    if unit.unit_type == "ambulance":
                        # Transition to LOADING
                        unit.status = ResourceStatus.LOADING.value
                        unit.phase_start_time = now
                        unit.phase_duration_seconds = 5.0
                        pts = active_inc.patient_count if active_inc else 1
                        workflow_coordinator.log_agent_action(
                            agent_name="EmergencyAgent",
                            role="Paramedic Triage",
                            action=f"{unit.call_sign} Loading Patients",
                            summary=f"{unit.call_sign} loading {pts} patient(s) into emergency ambulance.",
                            details={"unit_id": unit.unit_id, "patient_count": pts}
                        )
                    else:
                        # Fire / Police on-scene mitigation complete -> Transition to RETURNING
                        ret_path = city_graph_service.find_shortest_path(
                            origin_node=unit.current_node,
                            destination_node=unit.station_node,
                            algorithm="astar",
                            allow_destination_access=True
                        )
                        coords = [[c["latitude"], c["longitude"]] for c in ret_path.coordinates] if ret_path and ret_path.coordinates else []
                        unit.status = ResourceStatus.RETURNING.value
                        unit.target_node = unit.station_node
                        unit.route_geometry = coords
                        unit.dispatch_timestamp = now
                        unit.total_route_distance_meters = ret_path.distance_meters if ret_path else 0.0
                        unit.total_route_duration_seconds = ret_path.estimated_travel_time_seconds if ret_path else 0.0
                        unit.eta_seconds = ret_path.estimated_travel_time_seconds if ret_path else 0
                        unit.phase_start_time = None

                        workflow_coordinator.log_agent_action(
                            agent_name="EmergencyAgent",
                            role="Return Dispatch",
                            action=f"{unit.call_sign} Returning to Station",
                            summary=f"{unit.call_sign} secured scene and returning to station {unit.station_node}.",
                            details={"unit_id": unit.unit_id, "station": unit.station_node}
                        )

            # -------------------------------------------------------------
            # 3. LOADING (Ambulance loading patients, ~5 simulated seconds)
            # -------------------------------------------------------------
            elif unit.status == ResourceStatus.LOADING.value:
                if unit.phase_start_time is None:
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 5.0

                elapsed_phase = (now - unit.phase_start_time) * phase_speed
                if elapsed_phase >= (unit.phase_duration_seconds or 5.0):
                    pts = active_inc.patient_count if active_inc else 1
                    unit.patient_count = pts
                    hosp = unit.home_hospital_node or "INT-04"
                    hosp_path = city_graph_service.find_shortest_path(
                        origin_node=unit.current_node,
                        destination_node=hosp,
                        algorithm="astar",
                        allow_destination_access=True
                    )
                    coords = [[c["latitude"], c["longitude"]] for c in hosp_path.coordinates] if hosp_path and hosp_path.coordinates else []
                    unit.status = ResourceStatus.TRANSPORTING.value
                    unit.target_node = hosp
                    unit.route_geometry = coords
                    unit.dispatch_timestamp = now
                    unit.total_route_distance_meters = hosp_path.distance_meters if hosp_path else 0.0
                    unit.total_route_duration_seconds = hosp_path.estimated_travel_time_seconds if hosp_path else 0.0
                    unit.eta_seconds = hosp_path.estimated_travel_time_seconds if hosp_path else 0
                    unit.phase_start_time = None

                    # Add transport route to active routes
                    if hosp_path:
                        workflow_coordinator.state.active_routes = [
                            r for r in workflow_coordinator.state.active_routes if r.unit_id != unit.unit_id
                        ] + [
                            RouteResult(
                                route_id=f"ROUTE-HOSP-{unit.unit_id}",
                                origin_node=unit.current_node,
                                destination_node=hosp,
                                unit_id=unit.unit_id,
                                unit_type=unit.unit_type,
                                route_kind="transport_hospital",
                                coordinates=hosp_path.coordinates,
                                total_distance_meters=hosp_path.distance_meters,
                                estimated_travel_time_seconds=hosp_path.estimated_travel_time_seconds,
                                explanation=f"Emergency patient transport from incident to hospital {hosp}."
                            )
                        ]

                    workflow_coordinator.log_agent_action(
                        agent_name="EmergencyAgent",
                        role="Hospital Transport",
                        action=f"{unit.call_sign} Transporting to Hospital",
                        summary=f"{unit.call_sign} loaded {pts} patient(s) and transporting to {hosp}. ETA: {round((hosp_path.estimated_travel_time_seconds if hosp_path else 60)/60.0, 1)} min.",
                        details={"unit_id": unit.unit_id, "hospital": hosp, "patient_count": pts}
                    )

            # -------------------------------------------------------------
            # 4. TRANSPORTING (Ambulance transporting to hospital)
            # -------------------------------------------------------------
            elif unit.status == ResourceStatus.TRANSPORTING.value:
                if not unit.route_geometry or len(unit.route_geometry) < 2:
                    unit.status = ResourceStatus.AT_HOSPITAL.value
                    unit.current_node = unit.target_node or unit.current_node
                    unit.eta_seconds = 0
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 4.0
                    continue

                if unit.dispatch_timestamp is None:
                    unit.dispatch_timestamp = now

                elapsed = max(0.0, now - unit.dispatch_timestamp)
                speed_mps = (unit.speed_kmph * 1000.0 / 3600.0) * speed_multiplier
                dist_traveled = elapsed * speed_mps

                seg_lens = [self._haversine(unit.route_geometry[i - 1], unit.route_geometry[i]) for i in range(1, len(unit.route_geometry))]
                total_dist = sum(seg_lens)

                if total_dist <= 0 or dist_traveled >= total_dist:
                    unit.latitude = unit.route_geometry[-1][0]
                    unit.longitude = unit.route_geometry[-1][1]
                    unit.current_node = unit.target_node or unit.current_node
                    unit.status = ResourceStatus.AT_HOSPITAL.value
                    unit.eta_seconds = 0
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 4.0

                    workflow_coordinator.log_agent_action(
                        agent_name="EmergencyAgent",
                        role="Emergency Admission",
                        action=f"{unit.call_sign} Arrived at Hospital",
                        summary=f"{unit.call_sign} reached hospital {unit.current_node}. Transferring {unit.patient_count} patient(s) to emergency room staff.",
                        details={"unit_id": unit.unit_id, "hospital": unit.current_node, "patient_count": unit.patient_count}
                    )
                else:
                    rem_dist = max(0.0, total_dist - dist_traveled)
                    unit.eta_seconds = max(1, int(rem_dist / speed_mps))
                    accum = 0.0
                    for i, slen in enumerate(seg_lens):
                        if accum + slen >= dist_traveled:
                            t = (dist_traveled - accum) / slen if slen > 0 else 0.0
                            unit.latitude = unit.route_geometry[i][0] + t * (unit.route_geometry[i + 1][0] - unit.route_geometry[i][0])
                            unit.longitude = unit.route_geometry[i][1] + t * (unit.route_geometry[i + 1][1] - unit.route_geometry[i][1])
                            break
                        accum += slen

            # -------------------------------------------------------------
            # 5. AT_HOSPITAL (Ambulance at ER, brief ~4 simulated seconds)
            # -------------------------------------------------------------
            elif unit.status == ResourceStatus.AT_HOSPITAL.value:
                if unit.phase_start_time is None:
                    unit.phase_start_time = now
                    unit.phase_duration_seconds = 4.0

                elapsed_phase = (now - unit.phase_start_time) * phase_speed
                if elapsed_phase >= (unit.phase_duration_seconds or 4.0):
                    unit.patient_count = 0
                    if unit.current_node == unit.station_node:
                        # Already at home station!
                        unit.status = ResourceStatus.AVAILABLE.value
                        unit.assigned_incident_id = None
                        unit.eta_seconds = 0
                        unit.route_geometry = []
                        workflow_coordinator.log_agent_action(
                            agent_name="EmergencyAgent",
                            role="Mission Standby",
                            action=f"{unit.call_sign} Mission Complete",
                            summary=f"{unit.call_sign} completed hospital transfer at {unit.station_node} and available.",
                            details={"unit_id": unit.unit_id}
                        )
                    else:
                        # Compute return route from hospital to station
                        ret_path = city_graph_service.find_shortest_path(
                            origin_node=unit.current_node,
                            destination_node=unit.station_node,
                            algorithm="astar",
                            allow_destination_access=True
                        )
                        coords = [[c["latitude"], c["longitude"]] for c in ret_path.coordinates] if ret_path and ret_path.coordinates else []
                        unit.status = ResourceStatus.RETURNING.value
                        unit.target_node = unit.station_node
                        unit.route_geometry = coords
                        unit.dispatch_timestamp = now
                        unit.total_route_distance_meters = ret_path.distance_meters if ret_path else 0.0
                        unit.total_route_duration_seconds = ret_path.estimated_travel_time_seconds if ret_path else 0.0
                        unit.eta_seconds = ret_path.estimated_travel_time_seconds if ret_path else 0
                        unit.phase_start_time = None

                        if ret_path:
                            workflow_coordinator.state.active_routes = [
                                r for r in workflow_coordinator.state.active_routes if r.unit_id != unit.unit_id
                            ] + [
                                RouteResult(
                                    route_id=f"ROUTE-RET-{unit.unit_id}",
                                    origin_node=unit.current_node,
                                    destination_node=unit.station_node,
                                    unit_id=unit.unit_id,
                                    unit_type=unit.unit_type,
                                    route_kind="return_station",
                                    coordinates=ret_path.coordinates,
                                    total_distance_meters=ret_path.distance_meters,
                                    estimated_travel_time_seconds=ret_path.estimated_travel_time_seconds,
                                    explanation=f"Returning from hospital to base station {unit.station_node}."
                                )
                            ]

                        workflow_coordinator.log_agent_action(
                            agent_name="EmergencyAgent",
                            role="Return Transit",
                            action=f"{unit.call_sign} Returning to Base",
                            summary=f"{unit.call_sign} finished hospital discharge. Returning to station {unit.station_node}.",
                            details={"unit_id": unit.unit_id, "station": unit.station_node}
                        )

            # -------------------------------------------------------------
            # 6. RETURNING (Traveling back to home station)
            # -------------------------------------------------------------
            elif unit.status == ResourceStatus.RETURNING.value:
                if not unit.route_geometry or len(unit.route_geometry) < 2:
                    unit.status = ResourceStatus.AVAILABLE.value
                    unit.current_node = unit.station_node
                    unit.assigned_incident_id = None
                    unit.eta_seconds = 0
                    unit.route_geometry = []
                    continue

                if unit.dispatch_timestamp is None:
                    unit.dispatch_timestamp = now

                elapsed = max(0.0, now - unit.dispatch_timestamp)
                speed_mps = (unit.speed_kmph * 1000.0 / 3600.0) * speed_multiplier
                dist_traveled = elapsed * speed_mps

                seg_lens = [self._haversine(unit.route_geometry[i - 1], unit.route_geometry[i]) for i in range(1, len(unit.route_geometry))]
                total_dist = sum(seg_lens)

                if total_dist <= 0 or dist_traveled >= total_dist:
                    unit.latitude = unit.route_geometry[-1][0]
                    unit.longitude = unit.route_geometry[-1][1]
                    unit.current_node = unit.station_node
                    unit.status = ResourceStatus.AVAILABLE.value
                    unit.assigned_incident_id = None
                    unit.eta_seconds = 0
                    unit.route_geometry = []

                    workflow_coordinator.log_agent_action(
                        agent_name="EmergencyAgent",
                        role="Ready Standby",
                        action=f"{unit.call_sign} Returned to Base",
                        summary=f"{unit.call_sign} returned to station {unit.station_node} and available for dispatch.",
                        details={"unit_id": unit.unit_id}
                    )
                else:
                    rem_dist = max(0.0, total_dist - dist_traveled)
                    unit.eta_seconds = max(1, int(rem_dist / speed_mps))
                    accum = 0.0
                    for i, slen in enumerate(seg_lens):
                        if accum + slen >= dist_traveled:
                            t = (dist_traveled - accum) / slen if slen > 0 else 0.0
                            unit.latitude = unit.route_geometry[i][0] + t * (unit.route_geometry[i + 1][0] - unit.route_geometry[i][0])
                            unit.longitude = unit.route_geometry[i][1] + t * (unit.route_geometry[i + 1][1] - unit.route_geometry[i][1])
                            break
                        accum += slen

        # -----------------------------------------------------------------
        # Check overall incident resolution if all units have completed mission
        # -----------------------------------------------------------------
        if active_inc and not self.is_mission_in_progress():
            if active_inc.status != "resolved":
                incident_service.update_status(active_inc.incident_id, "resolved")
                workflow_coordinator.state.status = "resolved"
                workflow_coordinator.state.stage = "resolved"
                workflow_coordinator.state.active_routes = []
                workflow_coordinator.state.signal_priority_corridor = {"corridor_nodes": [], "active": False}
                if active_inc.affected_road_id:
                    city_graph_service.set_road_blocked(active_inc.affected_road_id, False)

                workflow_coordinator.log_agent_action(
                    agent_name="EmergencyAgent",
                    role="Mission Complete",
                    action=f"Incident {active_inc.incident_id} Resolved",
                    summary=f"Incident {active_inc.incident_id} resolved. All units returned to stations and available.",
                    details={"incident_id": active_inc.incident_id}
                )

        return self.get_all_units()


resource_service = ResourceService()
