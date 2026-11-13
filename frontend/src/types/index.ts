// UrbanFlow AI - Frontend TypeScript Definitions
// Directly aligned with Member 1 & Member 4 Backend Pydantic Schemas

export type SignalState = 'normal' | 'priority_green' | 'caution_flashing';

export type CongestionLevel = 'free_flow' | 'moderate' | 'heavy' | 'severe';

export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface IntersectionNode {
  node_id: string;
  name: string;
  latitude: number;
  longitude: number;
  is_signalized: boolean;
  signal_state: SignalState;
}

export interface RoadSegment {
  road_id: string;
  name: string;
  source_node: string;
  target_node: string;
  length_meters: number;
  speed_limit_kmph: number;
  base_travel_time_seconds: number;
  current_congestion_level: CongestionLevel;
  congestion_weight_multiplier: number;
  is_blocked: boolean;
  is_diverted: boolean;
  geometry?: [number, number][];
}

export interface CityGraph {
  city_name: string;
  nodes: IntersectionNode[];
  edges: RoadSegment[];
}

<<<<<<< HEAD
export type IncidentStatus =
  | 'candidate'
  | 'verified'
  | 'response_recommended'
  | 'simulated_dispatch'
=======
export type IncidentStatus = 
  | 'candidate' 
  | 'verified' 
  | 'response_recommended' 
  | 'simulated_dispatch' 
  | 'on_scene'
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
  | 'resolved';

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical' | 'unknown';

export interface ObservedVehicle {
  vehicle_class: string;
  bbox: [number, number, number, number];
  relative_speed_bbox_widths_per_sec: number;
  is_stopped: boolean;
}

export interface IncidentRecord {
  incident_id: string;
  title: string;
  status: IncidentStatus;
  incident_type: string;
  scenario_type?: string;
  patient_count?: number;
  severity: IncidentSeverity;
  heuristic_score: number;
  location_node: string;
  affected_road_id?: string;
  latitude: number;
  longitude: number;
  source: string;
  evidence_urls: string[];
  created_at: string;
  updated_at: string;
  structured_report?: string;
  recommended_service?: string;
  assigned_unit_ids: string[];
}

export type ResourceType = 'ambulance' | 'fire_engine' | 'police_patrol';

export type ResourceStatus = 
  | 'available' 
  | 'stationed' 
  | 'dispatched' 
  | 'en_route' 
  | 'on_scene' 
  | 'loading' 
  | 'transporting' 
  | 'at_hospital' 
  | 'returning' 
  | 'maintenance';

export interface EmergencyUnit {
  unit_id: string;
  call_sign: string;
  unit_type: ResourceType;
  station_node: string;
  current_node: string;
  status: ResourceStatus;
  latitude: number;
  longitude: number;
  speed_kmph?: number;
  assigned_incident_id?: string;
  capabilities: string[];
  eta_seconds?: number;
  route_geometry?: [number, number][];
  dispatch_timestamp?: number;
  home_hospital_node?: string;
  patient_count?: number;
  phase_start_time?: number;
  phase_duration_seconds?: number;
}

export interface RouteResult {
  route_id: string;
  origin_node: string;
  destination_node: string;
  algorithm: string;
  unit_id?: string;
  incident_id?: string;
  road_ids: string[];
  node_ids: string[];
  total_distance_meters: number;
  estimated_travel_time_seconds: number;
  estimated_travel_time_minutes: number;
  coordinates: Coordinate[];
  unit_current_position?: Record<string, any>;
  eta_seconds?: number;
  route_status?: string;
  simulation_status?: string;
  primary_route?: any;
  avoided_roads: string[];
  signal_priority_nodes?: string[];
  diverted_roads?: string[];
  alternative_routes?: RouteResult[];
  explanation: string;
  unit_id?: string;
  unit_type?: string;
  route_kind?: string;
}

export interface AgentLogEntry {
  agent_name: string;
  role: string;
  action: string;
  reasoning: string;
  summary?: string;
  timestamp: string;
  simulated: boolean;
  structured_output?: Record<string, any>;
}

export interface OrchestrationState {
  workflow_id: string;
  scenario_id?: string;
  stage: string;
  status?: string;
  current_step?: number;
  total_steps?: number;
  active_incident: IncidentRecord | null;
  active_routes: RouteResult[];
  traffic_diversions: {
    diverted_road_ids: string[];
    diversion_route: RouteResult | null;
  };
  signal_priority_corridor: {
    corridor_nodes: string[];
    active: boolean;
  };
  signal_priority_nodes?: string[];
  diverted_roads?: string[];
  dispatched_units?: EmergencyUnit[];
  recommended_service?: string;
  explanation?: string;
  agent_logs: AgentLogEntry[];
  agent_log?: AgentLogEntry[];
  simulated: boolean;
}

<<<<<<< HEAD

// -----------------------------------------------------------------------------
// Find Path & Route Comparison Types
// -----------------------------------------------------------------------------

export type AppMode = 'scenario' | 'find_path';

export interface PathSegmentDetail {
  road_id: string;
  name: string;
  from_node: string;
  to_node: string;
=======
export interface SegmentCongestionInfo {
  road_id: string;
  name: string;
  source_node: string;
  target_node: string;
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
  length_meters: number;
  speed_limit_kmph: number;
  congestion_level: string;
  congestion_multiplier: number;
  is_blocked: boolean;
<<<<<<< HEAD
  travel_time_seconds: number;
=======
  segment_travel_time_seconds: number;
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
}

export interface FindPathResult {
  mode: 'optimised' | 'baseline';
  algorithm: string;
  from_node: string;
  to_node: string;
<<<<<<< HEAD
  reachable: boolean;
  total_distance_meters: number;
  total_distance_km: number;
=======
  node_sequence: string[];
  road_ids: string[];
  geometry: [number, number][];
  total_distance_km: number;
  total_distance_meters: number;
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
  estimated_travel_time_seconds: number;
  estimated_travel_time_minutes: number;
  nodes_explored: number;
  compute_ms: number;
<<<<<<< HEAD
  node_ids: string[];
  road_ids: string[];
  coordinates: Coordinate[];
  congested_segments_count: number;
  blocked_roads_hit: number;
  has_blocked_segments: boolean;
  detour_penalty_seconds: number;
  segments: PathSegmentDetail[];
  summary: string;
}

export interface PathComparison {
  time_saved_seconds: number;
  time_saved_minutes: number;
  time_saved_percent: number;
  distance_difference_meters: number;
  distance_difference_km: number;
  congested_segments_avoided: number;
  blocked_roads_avoided: number;
  summary: string;
}

export interface ComparePathResult {
  from_node: string;
  to_node: string;
  algorithm: string;
  reachable: boolean;
  optimised?: FindPathResult;
  baseline?: FindPathResult;
  comparison?: PathComparison;
  error_message?: string;
=======
  congested_segments_count: number;
  blocked_roads_count: number;
  has_blocked_segments: boolean;
  detour_penalty_applied_seconds: number;
  segments: SegmentCongestionInfo[];
  is_reachable: boolean;
  message?: string;
}

export interface ComparePathsResult {
  from_node: string;
  to_node: string;
  is_reachable: boolean;
  routes_match: boolean;
  summary: string;
  time_saved_minutes: number;
  time_saved_percent: number;
  distance_diff_km: number;
  optimised: FindPathResult;
  baseline: FindPathResult;
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
}

export interface RandomizeTrafficResult {
  status: string;
<<<<<<< HEAD
  seed?: number;
  blocked_roads: string[];
  congested_roads_count: number;
  total_roads: number;
=======
  seed_used: number;
  blocked_roads: string[];
  congested_roads_count: number;
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
}
