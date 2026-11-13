import { CityGraph, EmergencyUnit, IncidentRecord, OrchestrationState, RouteResult } from '../types';
import cityGraphData from '../data/city_graph.json';

export const mockCityGraph: CityGraph = cityGraphData as unknown as CityGraph;

export const standbyOrchestrationState: OrchestrationState = {
  workflow_id: "WF-SCENARIO-STANDBY",
  stage: "idle",
  status: "idle",
  current_step: 0,
  total_steps: 5,
  active_incident: null,
  active_routes: [],
  traffic_diversions: {
    diverted_road_ids: [],
    diversion_route: null,
  },
  signal_priority_corridor: {
    corridor_nodes: [],
    active: false,
  },
  agent_logs: [
    {
      agent_name: "CoordinatorAgent",
      role: "System Orchestrator",
      action: "System Initialized",
      reasoning: "UrbanFlow AI Command Center in active standby monitoring Cyber City network.",
      timestamp: "T+00:00s",
      simulated: true,
    },
  ],
  simulated: true,
};

export const mockEmergencyUnits: EmergencyUnit[] = [
  {
<<<<<<< HEAD
    unit_id: "AMB-01",
    call_sign: "Medic One ALS",
    unit_type: "ambulance",
    station_node: "INT-04",
    current_node: "INT-04",
    status: "stationed",
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
    current_node: "INT-18",
    status: "stationed",
    latitude: 17.445,
    longitude: 78.384,
=======
    unit_id: 'AMB-01',
    call_sign: 'Medic One ALS',
    unit_type: 'ambulance',
    station_node: 'INT-04',
    current_node: 'INT-04',
    status: 'dispatched',
    latitude: 17.45806,
    longitude: 78.370666,
    speed_kmph: 55.0,
    assigned_incident_id: 'INC-DEMO-001',
    capabilities: ['advanced_life_support', 'paramedic_crew', 'ventilator', 'defibrillator'],
    eta_seconds: 212
  },
  {
    unit_id: 'AMB-02',
    call_sign: 'Medic Two BLS',
    unit_type: 'ambulance',
    station_node: 'INT-13',
    current_node: 'INT-13',
    status: 'stationed',
    latitude: 17.438042,
    longitude: 78.373479,
    speed_kmph: 50.0,
    capabilities: ['basic_life_support', 'emergency_transport']
  },
  {
    unit_id: 'FIRE-01',
    call_sign: 'Tower Rescue 7',
    unit_type: 'fire_engine',
    station_node: 'INT-07',
    current_node: 'INT-07',
    status: 'stationed',
    latitude: 17.448111,
    longitude: 78.363539,
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
    speed_kmph: 45.0,
    capabilities: ['water_tender', 'hydraulic_rescue_cutters', 'ladder', 'hazmat_containment']
  },
  {
    unit_id: 'POL-01',
    call_sign: 'Patrol Alpha',
    unit_type: 'police_patrol',
    station_node: 'INT-05',
    current_node: 'INT-05',
    status: 'dispatched',
    latitude: 17.43771,
    longitude: 78.382441,
    speed_kmph: 60.0,
    assigned_incident_id: 'INC-DEMO-001',
    capabilities: ['traffic_control', 'scene_security', 'diversion_enforcement'],
    eta_seconds: 65
  },
  {
    unit_id: 'POLICE-02',
    call_sign: 'East Patrol Delta',
    unit_type: 'police_patrol',
    station_node: 'INT-11',
    current_node: 'INT-11',
    status: 'stationed',
    latitude: 17.446986,
    longitude: 78.37782,
    speed_kmph: 65.0,
    capabilities: ['rapid_response', 'crowd_diversion', 'motorcycle_escort']
  }
];

export const mockActiveIncident: IncidentRecord = {
  incident_id: 'INC-DEMO-001',
  title: 'Candidate Multi-Vehicle Collision at Cyber Towers',
  status: 'verified',
  incident_type: 'possible_collision',
  severity: 'high',
  heuristic_score: 0.85,
  location_node: 'INT-03',
  affected_road_id: 'ROAD-03A',
  latitude: 17.447984,
  longitude: 78.374314,
  source: 'cctv_camera_01',
  evidence_urls: [
    'assets/evidence/INC-CCTV-001_frame_426.jpg',
    'assets/evidence/INC-CCTV-001_crop_14_19.jpg'
  ],
  created_at: new Date(Date.now() - 142000).toISOString(),
  updated_at: new Date().toISOString(),
  structured_report: 'CCTV automated vision heuristic detected abrupt deceleration followed by mutual bounding-box proximity outside signal stop line. Two vehicles involved (car #14, truck #19). Human operator verified scene.',
  recommended_service: 'ambulance & police_patrol',
  assigned_unit_ids: ['AMB-01', 'POL-01']
};

export const mockEmergencyRoute: RouteResult = {
  route_id: 'ROUTE-EMERGENCY-01',
  origin_node: 'INT-04',
  destination_node: 'INT-03',
  algorithm: 'astar_optimized',
  road_ids: ["ROAD-86B", "ROAD-123A", "ROAD-67A", "ROAD-252B", "ROAD-149A", "ROAD-224B", "ROAD-90B", "ROAD-204B", "ROAD-109A", "ROAD-295A", "ROAD-297A", "ROAD-106B", "ROAD-104B", "ROAD-103A", "ROAD-99A"],
  node_ids: ["INT-04", "INT-79", "INT-47", "INT-160", "INT-95", "INT-142", "INT-60", "INT-130", "INT-69", "INT-187", "INT-188", "INT-66", "INT-20", "INT-65", "INT-19", "INT-03"],
  total_distance_meters: 3391.0,
  estimated_travel_time_seconds: 212,
  estimated_travel_time_minutes: 3.5,
  coordinates: [{"latitude": 17.45806, "longitude": 78.370666}, {"latitude": 17.458253, "longitude": 78.369302}, {"latitude": 17.458278, "longitude": 78.369133}, {"latitude": 17.458347, "longitude": 78.36866}, {"latitude": 17.458363, "longitude": 78.368553}, {"latitude": 17.458426, "longitude": 78.368124}, {"latitude": 17.458444, "longitude": 78.368036}, {"latitude": 17.458458, "longitude": 78.367973}, {"latitude": 17.458494, "longitude": 78.36774}, {"latitude": 17.458519, "longitude": 78.367291}, {"latitude": 17.458523, "longitude": 78.367076}, {"latitude": 17.458542, "longitude": 78.366972}, {"latitude": 17.458575, "longitude": 78.366881}, {"latitude": 17.458747, "longitude": 78.366618}, {"latitude": 17.458801, "longitude": 78.366534}, {"latitude": 17.45887, "longitude": 78.366412}, {"latitude": 17.4589, "longitude": 78.366344}, {"latitude": 17.458913, "longitude": 78.366314}, {"latitude": 17.458933, "longitude": 78.36627}, {"latitude": 17.458941, "longitude": 78.366237}, {"latitude": 17.458966, "longitude": 78.365985}, {"latitude": 17.459032, "longitude": 78.365992}, {"latitude": 17.459098, "longitude": 78.366001}, {"latitude": 17.45903, "longitude": 78.366258}, {"latitude": 17.459023, "longitude": 78.366296}, {"latitude": 17.458913, "longitude": 78.366722}, {"latitude": 17.458861, "longitude": 78.366912}, {"latitude": 17.458842, "longitude": 78.366979}, {"latitude": 17.458767, "longitude": 78.367337}, {"latitude": 17.458719, "longitude": 78.367568}, {"latitude": 17.458702, "longitude": 78.36765}, {"latitude": 17.45867, "longitude": 78.3678}, {"latitude": 17.45858, "longitude": 78.368334}, {"latitude": 17.458569, "longitude": 78.368436}, {"latitude": 17.458508, "longitude": 78.368883}, {"latitude": 17.45848, "longitude": 78.369054}, {"latitude": 17.458467, "longitude": 78.369138}, {"latitude": 17.458451, "longitude": 78.369235}, {"latitude": 17.45833, "longitude": 78.369869}, {"latitude": 17.458277, "longitude": 78.370137}, {"latitude": 17.458254, "longitude": 78.370239}, {"latitude": 17.458151, "longitude": 78.370709}, {"latitude": 17.458127, "longitude": 78.370787}, {"latitude": 17.458121, "longitude": 78.370812}, {"latitude": 17.457984, "longitude": 78.371254}, {"latitude": 17.457975, "longitude": 78.371283}, {"latitude": 17.457959, "longitude": 78.371335}, {"latitude": 17.457845, "longitude": 78.371715}, {"latitude": 17.457819, "longitude": 78.371799}, {"latitude": 17.457702, "longitude": 78.372268}, {"latitude": 17.457675, "longitude": 78.372445}, {"latitude": 17.457669, "longitude": 78.372484}, {"latitude": 17.457659, "longitude": 78.372561}, {"latitude": 17.457627, "longitude": 78.372739}, {"latitude": 17.45762, "longitude": 78.372887}, {"latitude": 17.457617, "longitude": 78.372968}, {"latitude": 17.457592, "longitude": 78.373196}, {"latitude": 17.457567, "longitude": 78.373609}, {"latitude": 17.457557, "longitude": 78.373712}, {"latitude": 17.457549, "longitude": 78.373805}, {"latitude": 17.457525, "longitude": 78.374198}, {"latitude": 17.457489, "longitude": 78.374795}, {"latitude": 17.457462, "longitude": 78.375254}, {"latitude": 17.457415, "longitude": 78.375501}, {"latitude": 17.457344, "longitude": 78.375699}, {"latitude": 17.457159, "longitude": 78.376066}, {"latitude": 17.45699, "longitude": 78.376299}, {"latitude": 17.456924, "longitude": 78.37639}, {"latitude": 17.456841, "longitude": 78.376329}, {"latitude": 17.45691, "longitude": 78.37624}, {"latitude": 17.456944, "longitude": 78.376197}, {"latitude": 17.45706, "longitude": 78.376044}, {"latitude": 17.457264, "longitude": 78.375664}, {"latitude": 17.45733, "longitude": 78.375482}, {"latitude": 17.457372, "longitude": 78.375257}, {"latitude": 17.457383, "longitude": 78.374689}, {"latitude": 17.457425, "longitude": 78.374053}, {"latitude": 17.457435, "longitude": 78.373805}, {"latitude": 17.457437, "longitude": 78.373772}, {"latitude": 17.457198, "longitude": 78.373695}, {"latitude": 17.457133, "longitude": 78.373664}, {"latitude": 17.456886, "longitude": 78.373457}, {"latitude": 17.456781, "longitude": 78.373367}, {"latitude": 17.456068, "longitude": 78.372881}, {"latitude": 17.455502, "longitude": 78.372462}, {"latitude": 17.455142, "longitude": 78.372193}, {"latitude": 17.454322, "longitude": 78.371573}, {"latitude": 17.45379, "longitude": 78.371185}, {"latitude": 17.453589, "longitude": 78.371041}, {"latitude": 17.452916, "longitude": 78.370533}, {"latitude": 17.452235, "longitude": 78.369994}, {"latitude": 17.452165, "longitude": 78.369964}, {"latitude": 17.452095, "longitude": 78.369991}, {"latitude": 17.451622, "longitude": 78.370447}, {"latitude": 17.451569, "longitude": 78.370567}, {"latitude": 17.451576, "longitude": 78.370677}, {"latitude": 17.451721, "longitude": 78.3709}, {"latitude": 17.45175, "longitude": 78.370997}, {"latitude": 17.451724, "longitude": 78.371082}, {"latitude": 17.451471, "longitude": 78.371359}, {"latitude": 17.451334, "longitude": 78.3715}, {"latitude": 17.450905, "longitude": 78.371938}, {"latitude": 17.450449, "longitude": 78.372405}, {"latitude": 17.450367, "longitude": 78.372484}, {"latitude": 17.449811, "longitude": 78.373057}, {"latitude": 17.449796, "longitude": 78.373072}, {"latitude": 17.449444, "longitude": 78.373423}, {"latitude": 17.449345, "longitude": 78.373525}, {"latitude": 17.449219, "longitude": 78.373655}, {"latitude": 17.449064, "longitude": 78.373796}, {"latitude": 17.448915, "longitude": 78.373919}, {"latitude": 17.448615, "longitude": 78.374112}, {"latitude": 17.448516, "longitude": 78.374158}, {"latitude": 17.448175, "longitude": 78.374319}, {"latitude": 17.447995, "longitude": 78.374402}, {"latitude": 17.447984, "longitude": 78.374314}],
  avoided_roads: ['ROAD-03A'],
  explanation: 'Primary corridor avoids blocked Cyber Towers Boulevard. Signal preemption active along corridor.'
};

export const mockDiversionRoute: RouteResult = {
  route_id: 'ROUTE-DIVERSION-GEN',
  origin_node: 'INT-18',
  destination_node: 'INT-03',
  algorithm: 'dijkstra_diversion',
  road_ids: ["ROAD-18B", "ROAD-89A", "ROAD-157A", "ROAD-08B", "ROAD-09A", "ROAD-283A", "ROAD-163A", "ROAD-161A", "ROAD-35A", "ROAD-36B", "ROAD-108B", "ROAD-147A", "ROAD-297A", "ROAD-106B", "ROAD-104B", "ROAD-103A", "ROAD-99A"],
  node_ids: ["INT-18", "INT-59", "INT-100", "INT-11", "INT-12", "INT-180", "INT-104", "INT-103", "INT-28", "INT-29", "INT-68", "INT-93", "INT-188", "INT-66", "INT-20", "INT-65", "INT-19", "INT-03"],
  total_distance_meters: 3494.6,
  estimated_travel_time_seconds: 224,
  estimated_travel_time_minutes: 3.7,
  coordinates: [{"latitude": 17.443422, "longitude": 78.37711}, {"latitude": 17.443514, "longitude": 78.377107}, {"latitude": 17.443778, "longitude": 78.37709}, {"latitude": 17.443789, "longitude": 78.37709}, {"latitude": 17.444201, "longitude": 78.377099}, {"latitude": 17.444232, "longitude": 78.377098}, {"latitude": 17.444323, "longitude": 78.377098}, {"latitude": 17.444417, "longitude": 78.377102}, {"latitude": 17.444497, "longitude": 78.377111}, {"latitude": 17.444582, "longitude": 78.377121}, {"latitude": 17.444752, "longitude": 78.377147}, {"latitude": 17.445257, "longitude": 78.377232}, {"latitude": 17.445842, "longitude": 78.377314}, {"latitude": 17.445938, "longitude": 78.37733}, {"latitude": 17.446024, "longitude": 78.377343}, {"latitude": 17.44611, "longitude": 78.377363}, {"latitude": 17.446174, "longitude": 78.377383}, {"latitude": 17.446254, "longitude": 78.377409}, {"latitude": 17.446399, "longitude": 78.377473}, {"latitude": 17.446842, "longitude": 78.377733}, {"latitude": 17.446986, "longitude": 78.37782}, {"latitude": 17.447195, "longitude": 78.377944}, {"latitude": 17.447372, "longitude": 78.378051}, {"latitude": 17.447525, "longitude": 78.378149}, {"latitude": 17.447646, "longitude": 78.378233}, {"latitude": 17.448207, "longitude": 78.378708}, {"latitude": 17.448381, "longitude": 78.378838}, {"latitude": 17.4485, "longitude": 78.37891}, {"latitude": 17.448646, "longitude": 78.378987}, {"latitude": 17.448756, "longitude": 78.379035}, {"latitude": 17.448857, "longitude": 78.379075}, {"latitude": 17.448958, "longitude": 78.379107}, {"latitude": 17.449083, "longitude": 78.379142}, {"latitude": 17.449928, "longitude": 78.37933}, {"latitude": 17.450062, "longitude": 78.379368}, {"latitude": 17.450143, "longitude": 78.37939}, {"latitude": 17.450178, "longitude": 78.379402}, {"latitude": 17.450195, "longitude": 78.379409}, {"latitude": 17.450281, "longitude": 78.37945}, {"latitude": 17.45042, "longitude": 78.379487}, {"latitude": 17.450506, "longitude": 78.379531}, {"latitude": 17.450602, "longitude": 78.379603}, {"latitude": 17.450646, "longitude": 78.379644}, {"latitude": 17.450679, "longitude": 78.379676}, {"latitude": 17.450735, "longitude": 78.379743}, {"latitude": 17.451218, "longitude": 78.380448}, {"latitude": 17.451327, "longitude": 78.380608}, {"latitude": 17.451381, "longitude": 78.380647}, {"latitude": 17.451436, "longitude": 78.380676}, {"latitude": 17.45151, "longitude": 78.380693}, {"latitude": 17.451585, "longitude": 78.380701}, {"latitude": 17.451678, "longitude": 78.3807}, {"latitude": 17.451769, "longitude": 78.380686}, {"latitude": 17.451859, "longitude": 78.38066}, {"latitude": 17.451944, "longitude": 78.380622}, {"latitude": 17.452011, "longitude": 78.380575}, {"latitude": 17.452637, "longitude": 78.380007}, {"latitude": 17.45302, "longitude": 78.379666}, {"latitude": 17.453071, "longitude": 78.379625}, {"latitude": 17.453209, "longitude": 78.379513}, {"latitude": 17.453987, "longitude": 78.378871}, {"latitude": 17.454285, "longitude": 78.378648}, {"latitude": 17.454969, "longitude": 78.378075}, {"latitude": 17.45504, "longitude": 78.378023}, {"latitude": 17.455048, "longitude": 78.378007}, {"latitude": 17.455637, "longitude": 78.377565}, {"latitude": 17.456003, "longitude": 78.377311}, {"latitude": 17.456238, "longitude": 78.377121}, {"latitude": 17.45631, "longitude": 78.377022}, {"latitude": 17.456338, "longitude": 78.376986}, {"latitude": 17.45648, "longitude": 78.376795}, {"latitude": 17.456841, "longitude": 78.376329}, {"latitude": 17.45691, "longitude": 78.37624}, {"latitude": 17.456944, "longitude": 78.376197}, {"latitude": 17.45706, "longitude": 78.376044}, {"latitude": 17.457264, "longitude": 78.375664}, {"latitude": 17.45733, "longitude": 78.375482}, {"latitude": 17.457372, "longitude": 78.375257}, {"latitude": 17.457383, "longitude": 78.374689}, {"latitude": 17.457425, "longitude": 78.374053}, {"latitude": 17.457435, "longitude": 78.373805}, {"latitude": 17.457437, "longitude": 78.373772}, {"latitude": 17.457198, "longitude": 78.373695}, {"latitude": 17.457133, "longitude": 78.373664}, {"latitude": 17.456886, "longitude": 78.373457}, {"latitude": 17.456781, "longitude": 78.373367}, {"latitude": 17.456068, "longitude": 78.372881}, {"latitude": 17.455502, "longitude": 78.372462}, {"latitude": 17.455142, "longitude": 78.372193}, {"latitude": 17.454322, "longitude": 78.371573}, {"latitude": 17.45379, "longitude": 78.371185}, {"latitude": 17.453589, "longitude": 78.371041}, {"latitude": 17.452916, "longitude": 78.370533}, {"latitude": 17.452235, "longitude": 78.369994}, {"latitude": 17.452165, "longitude": 78.369964}, {"latitude": 17.452095, "longitude": 78.369991}, {"latitude": 17.451622, "longitude": 78.370447}, {"latitude": 17.451569, "longitude": 78.370567}, {"latitude": 17.451576, "longitude": 78.370677}, {"latitude": 17.451721, "longitude": 78.3709}, {"latitude": 17.45175, "longitude": 78.370997}, {"latitude": 17.451724, "longitude": 78.371082}, {"latitude": 17.451471, "longitude": 78.371359}, {"latitude": 17.451334, "longitude": 78.3715}, {"latitude": 17.450905, "longitude": 78.371938}, {"latitude": 17.450449, "longitude": 78.372405}, {"latitude": 17.450367, "longitude": 78.372484}, {"latitude": 17.449811, "longitude": 78.373057}, {"latitude": 17.449796, "longitude": 78.373072}, {"latitude": 17.449444, "longitude": 78.373423}, {"latitude": 17.449345, "longitude": 78.373525}, {"latitude": 17.449219, "longitude": 78.373655}, {"latitude": 17.449064, "longitude": 78.373796}, {"latitude": 17.448915, "longitude": 78.373919}, {"latitude": 17.448615, "longitude": 78.374112}, {"latitude": 17.448516, "longitude": 78.374158}, {"latitude": 17.448175, "longitude": 78.374319}, {"latitude": 17.447995, "longitude": 78.374402}, {"latitude": 17.447984, "longitude": 78.374314}],
  avoided_roads: ['ROAD-03A'],
  explanation: 'General traffic diverted away from incident zone via bypass arterial.'
};

export const mockOrchestrationState: OrchestrationState = {
  workflow_id: 'WF-SCENARIO-DEMO-01',
  stage: 'active_emergency_response',
  active_incident: mockActiveIncident,
  active_routes: [mockEmergencyRoute],
  traffic_diversions: {
    diverted_road_ids: ['ROAD-03A'],
    diversion_route: mockDiversionRoute
  },
  signal_priority_corridor: {
    corridor_nodes: ["INT-04", "INT-79", "INT-47", "INT-160", "INT-95", "INT-142", "INT-60", "INT-130", "INT-69", "INT-187", "INT-188", "INT-66", "INT-20", "INT-65", "INT-19"],
    active: true
  },
  agent_logs: [
    { agent_name: 'VisionAgent', role: 'CCTV Perception', action: 'Flagged candidate incident', reasoning: 'Relative deceleration detected on 2 tracked vehicles; overlap outside queue for 3.5s. Heuristic score: 0.85.', timestamp: 'T+00:02s', simulated: true },
    { agent_name: 'IncidentAgent', role: 'Triage & Classification', action: 'Verified candidate incident', reasoning: 'Human operator confirmed collision at Cyber Towers. Severity updated to High.', timestamp: 'T+00:05s', simulated: true },
    { agent_name: 'EmergencyAgent', role: 'Resource Dispatch', action: 'Recommended AMB-01 & POL-01', reasoning: 'Medic One ALS is nearest available ALS unit.', timestamp: 'T+00:07s', simulated: true },
    { agent_name: 'RouteAgent', role: 'Graph Optimization', action: 'Computed A* Route & Diversion', reasoning: 'Avoided blocked ROAD-03A; routed emergency units with full OSM geometry.', timestamp: 'T+00:10s', simulated: true },
    { agent_name: 'TrafficAgent', role: 'Signal & Corridor Control', action: 'Activated Green Corridor', reasoning: 'Preempted signals along corridor for emergency wave.', timestamp: 'T+00:12s', simulated: true }
  ],
  simulated: true
};
