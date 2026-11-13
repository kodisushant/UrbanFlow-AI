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

export type IncidentStatus = 
  | 'candidate' 
  | 'verified' 
  | 'response_recommended' 
  | 'simulated_dispatch' 
  | 'on_scene'
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
  road_ids: string[];
  node_ids: string[];
  total_distance_meters: number;
  estimated_travel_time_seconds: number;
  estimated_travel_time_minutes: number;
  coordinates: Coordinate[];
  avoided_roads: string[];
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
  timestamp: string;
  simulated: boolean;
}

export interface OrchestrationState {
  workflow_id: string;
  stage: string;
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
  agent_logs: AgentLogEntry[];
  simulated: boolean;
}

export interface SegmentCongestionInfo {
  road_id: string;
  name: string;
  source_node: string;
  target_node: string;
  length_meters: number;
  speed_limit_kmph: number;
  congestion_level: string;
  congestion_multiplier: number;
  is_blocked: boolean;
  segment_travel_time_seconds: number;
}

export interface FindPathResult {
  mode: 'optimised' | 'baseline';
  algorithm: string;
  from_node: string;
  to_node: string;
  node_sequence: string[];
  road_ids: string[];
  geometry: [number, number][];
  total_distance_km: number;
  total_distance_meters: number;
  estimated_travel_time_seconds: number;
  estimated_travel_time_minutes: number;
  nodes_explored: number;
  compute_ms: number;
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
}

export interface RandomizeTrafficResult {
  status: string;
  seed_used: number;
  blocked_roads: string[];
  congested_roads_count: number;
}
