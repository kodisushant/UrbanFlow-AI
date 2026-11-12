import { CityGraph, EmergencyUnit, IncidentRecord, OrchestrationState, RouteResult } from '../types';

export const mockCityGraph: CityGraph = {
  city_name: "Metropolis Cyber City Grid",
  nodes: [
    { node_id: "INT-01", name: "City Center Square", latitude: 17.442, longitude: 78.380, is_signalized: true, signal_state: "priority_green" },
    { node_id: "INT-02", name: "North Tech Park Junction", latitude: 17.456, longitude: 78.381, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-03", name: "Cyber Towers Intersection", latitude: 17.4485, longitude: 78.374, is_signalized: true, signal_state: "caution_flashing" },
    { node_id: "INT-04", name: "North Hospital Center", latitude: 17.460, longitude: 78.372, is_signalized: true, signal_state: "priority_green" },
    { node_id: "INT-05", name: "Outer Ring Interchange", latitude: 17.458, longitude: 78.361, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-06", name: "West Industrial Zone", latitude: 17.443, longitude: 78.358, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-07", name: "West Fire Station #1", latitude: 17.449, longitude: 78.355, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-08", name: "Financial District South", latitude: 17.431, longitude: 78.368, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-09", name: "Gachibowli Stadium Crossing", latitude: 17.440, longitude: 78.365, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-10", name: "BioTech Valley Gate", latitude: 17.452, longitude: 78.367, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-11", name: "HITEC City Metro Station", latitude: 17.447, longitude: 78.378, is_signalized: true, signal_state: "priority_green" },
    { node_id: "INT-12", name: "Knowledge City Link", latitude: 17.435, longitude: 78.376, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-13", name: "South General Hospital", latitude: 17.422, longitude: 78.373, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-14", name: "Airport Expressway Toll", latitude: 17.418, longitude: 78.382, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-15", name: "East Cyber Gateway", latitude: 17.438, longitude: 78.390, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-16", name: "Inorbit Mall Junction", latitude: 17.433, longitude: 78.386, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-17", name: "Durgam Cheruvu View", latitude: 17.436, longitude: 78.384, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-18", name: "Police Headquarters Link", latitude: 17.445, longitude: 78.388, is_signalized: true, signal_state: "normal" },
    { node_id: "INT-19", name: "Madhapur Main Crossing", latitude: 17.445, longitude: 78.384, is_signalized: true, signal_state: "priority_green" },
    { node_id: "INT-20", name: "Silicon Ridge North", latitude: 17.454, longitude: 78.375, is_signalized: true, signal_state: "priority_green" }
  ],
  edges: [
    { road_id: "ROAD-01A", name: "Main Avenue North", source_node: "INT-01", target_node: "INT-19", length_meters: 650, speed_limit_kmph: 50, base_travel_time_seconds: 46, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-01B", name: "Main Avenue South", source_node: "INT-19", target_node: "INT-01", length_meters: 650, speed_limit_kmph: 50, base_travel_time_seconds: 46, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-02A", name: "Tech Park Link", source_node: "INT-01", target_node: "INT-02", length_meters: 1550, speed_limit_kmph: 60, base_travel_time_seconds: 93, current_congestion_level: "moderate", congestion_weight_multiplier: 1.4, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-03A", name: "Cyber Towers Boulevard North", source_node: "INT-19", target_node: "INT-03", length_meters: 1100, speed_limit_kmph: 50, base_travel_time_seconds: 79, current_congestion_level: "severe", congestion_weight_multiplier: 5.0, is_blocked: true, is_diverted: true },
    { road_id: "ROAD-03B", name: "Cyber Towers Boulevard South", source_node: "INT-03", target_node: "INT-19", length_meters: 1100, speed_limit_kmph: 50, base_travel_time_seconds: 79, current_congestion_level: "severe", congestion_weight_multiplier: 5.0, is_blocked: true, is_diverted: true },
    { road_id: "ROAD-04A", name: "Outer Ring West", source_node: "INT-06", target_node: "INT-07", length_meters: 750, speed_limit_kmph: 60, base_travel_time_seconds: 45, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-11A", name: "Hospital Emergency Corridor", source_node: "INT-04", target_node: "INT-20", length_meters: 720, speed_limit_kmph: 50, base_travel_time_seconds: 51, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-11B", name: "Silicon Ridge Link", source_node: "INT-20", target_node: "INT-11", length_meters: 840, speed_limit_kmph: 50, base_travel_time_seconds: 60, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-12A", name: "Metro Transit Spine", source_node: "INT-11", target_node: "INT-19", length_meters: 670, speed_limit_kmph: 45, base_travel_time_seconds: 53, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false },
    { road_id: "ROAD-15A", name: "Diversion Bypass Arterial", source_node: "INT-02", target_node: "INT-20", length_meters: 900, speed_limit_kmph: 50, base_travel_time_seconds: 64, current_congestion_level: "moderate", congestion_weight_multiplier: 1.3, is_blocked: false, is_diverted: true },
    { road_id: "ROAD-18A", name: "Police Patrol Access", source_node: "INT-18", target_node: "INT-19", length_meters: 420, speed_limit_kmph: 50, base_travel_time_seconds: 30, current_congestion_level: "free_flow", congestion_weight_multiplier: 1.0, is_blocked: false, is_diverted: false }
  ]
};

export const mockEmergencyUnits: EmergencyUnit[] = [
  {
    unit_id: "AMB-01",
    call_sign: "Medic One ALS",
    unit_type: "ambulance",
    station_node: "INT-04",
    current_node: "INT-20",
    status: "dispatched",
    latitude: 17.454,
    longitude: 78.375,
    speed_kmph: 58.0,
    assigned_incident_id: "INC-DEMO-001",
    capabilities: ["advanced_life_support", "paramedic_crew", "ventilator", "defibrillator"],
    eta_seconds: 142
  },
  {
    unit_id: "POL-01",
    call_sign: "Patrol Delta-9",
    unit_type: "police_patrol",
    station_node: "INT-18",
    current_node: "INT-19",
    status: "dispatched",
    latitude: 17.445,
    longitude: 78.384,
    speed_kmph: 45.0,
    assigned_incident_id: "INC-DEMO-001",
    capabilities: ["traffic_control", "scene_security", "diversion_enforcement"],
    eta_seconds: 65
  },
  {
    unit_id: "FIRE-01",
    call_sign: "Heavy Rescue 1",
    unit_type: "fire_engine",
    station_node: "INT-07",
    current_node: "INT-07",
    status: "stationed",
    latitude: 17.449,
    longitude: 78.355,
    speed_kmph: 0.0,
    capabilities: ["water_tender", "hydraulic_rescue_cutters", "hazmat_containment"]
  }
];

export const mockActiveIncident: IncidentRecord = {
  incident_id: "INC-DEMO-001",
  title: "Candidate Multi-Vehicle Collision at Cyber Towers",
  status: "verified",
  incident_type: "possible_collision",
  severity: "high",
  heuristic_score: 0.85,
  location_node: "INT-03",
  affected_road_id: "ROAD-03A",
  latitude: 17.4485,
  longitude: 78.374,
  source: "cctv_camera_01",
  evidence_urls: [
    "assets/evidence/INC-CCTV-001_frame_426.jpg",
    "assets/evidence/INC-CCTV-001_crop_14_19.jpg"
  ],
  created_at: new Date(Date.now() - 142000).toISOString(),
  updated_at: new Date().toISOString(),
  structured_report: "CCTV automated vision heuristic detected abrupt deceleration followed by mutual bounding-box proximity outside signal stop line. Two vehicles involved (car #14, truck #19). Human operator verified scene.",
  recommended_service: "ambulance & police_patrol",
  assigned_unit_ids: ["AMB-01", "POL-01"]
};

export const mockEmergencyRoute: RouteResult = {
  route_id: "ROUTE-EMERGENCY-01",
  origin_node: "INT-04",
  destination_node: "INT-03",
  algorithm: "astar_optimized",
  road_ids: ["ROAD-11A", "ROAD-11B", "ROAD-12A"],
  node_ids: ["INT-04", "INT-20", "INT-11", "INT-19", "INT-03"],
  total_distance_meters: 2880,
  estimated_travel_time_seconds: 184,
  estimated_travel_time_minutes: 3.1,
  coordinates: [
    { latitude: 17.460, longitude: 78.372 },
    { latitude: 17.454, longitude: 78.375 },
    { latitude: 17.447, longitude: 78.378 },
    { latitude: 17.445, longitude: 78.384 },
    { latitude: 17.4485, longitude: 78.374 }
  ],
  avoided_roads: ["ROAD-03A", "ROAD-03B"],
  explanation: "Primary corridor avoids blocked Cyber Towers Boulevard. Signal preemption active on 4 intersections."
};

export const mockDiversionRoute: RouteResult = {
  route_id: "ROUTE-DIVERSION-GEN",
  origin_node: "INT-02",
  destination_node: "INT-01",
  algorithm: "dijkstra_diversion",
  road_ids: ["ROAD-15A", "ROAD-11B", "ROAD-01B"],
  node_ids: ["INT-02", "INT-20", "INT-19", "INT-01"],
  total_distance_meters: 3450,
  estimated_travel_time_seconds: 245,
  estimated_travel_time_minutes: 4.1,
  coordinates: [
    { latitude: 17.456, longitude: 78.381 },
    { latitude: 17.454, longitude: 78.375 },
    { latitude: 17.445, longitude: 78.384 },
    { latitude: 17.442, longitude: 78.380 }
  ],
  avoided_roads: ["ROAD-03A", "ROAD-03B"],
  explanation: "General traffic diverted away from incident zone via North Bypass Arterial."
};

export const mockOrchestrationState: OrchestrationState = {
  workflow_id: "WF-SCENARIO-DEMO-01",
  stage: "active_emergency_response",
  active_incident: mockActiveIncident,
  active_routes: [mockEmergencyRoute],
  traffic_diversions: {
    diverted_road_ids: ["ROAD-03A", "ROAD-03B"],
    diversion_route: mockDiversionRoute
  },
  signal_priority_corridor: {
    corridor_nodes: ["INT-04", "INT-20", "INT-11", "INT-19"],
    active: true
  },
  agent_logs: [
    { agent_name: "VisionAgent", role: "CCTV Perception", action: "Flagged candidate incident", reasoning: "Relative deceleration detected on 2 tracked vehicles; overlap outside queue for 3.5s. Heuristic score: 0.85.", timestamp: "T+00:02s", simulated: true },
    { agent_name: "IncidentAgent", role: "Triage & Classification", action: "Verified candidate incident", reasoning: "Human operator confirmed collision at Cyber Towers. Severity updated to High.", timestamp: "T+00:05s", simulated: true },
    { agent_name: "EmergencyAgent", role: "Resource Dispatch", action: "Recommended AMB-01 & POL-01", reasoning: "Medic One ALS is nearest available ALS unit (1.8km, ETA 2.4 min).", timestamp: "T+00:07s", simulated: true },
    { agent_name: "RouteAgent", role: "Graph Optimization", action: "Computed A* Route & Diversion", reasoning: "Avoided blocked ROAD-03A; routed emergency units via Silicon Ridge Link.", timestamp: "T+00:10s", simulated: true },
    { agent_name: "TrafficAgent", role: "Signal & Corridor Control", action: "Activated Green Corridor", reasoning: "Preempted signals at INT-20, INT-11, and INT-19 for emergency corridor.", timestamp: "T+00:12s", simulated: true }
  ],
  simulated: true
};
