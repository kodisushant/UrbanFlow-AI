import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  OrchestrationState,
} from '../types';
import {
  mockCityGraph,
  mockEmergencyUnits,
  mockOrchestrationState,
  standbyOrchestrationState,
} from './mockData';

// Centralized API configuration
// Supports Vite reverse proxy `/api/v1` or explicit backend URL via environment variable
const BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string) || '/api/v1';
const DIRECT_BACKEND_URL = 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const primaryUrl = `${BASE_URL}${endpoint}`;
  let response: Response;

  try {
    response = await fetch(primaryUrl, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  } catch (netErr) {
    // If reverse proxy failed or Vite isn't proxying, attempt direct backend call
    if (!BASE_URL.startsWith('http')) {
      try {
        const directUrl = `${DIRECT_BACKEND_URL}${endpoint}`;
        response = await fetch(directUrl, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
          },
        });
      } catch {
        throw netErr;
      }
    } else {
      throw netErr;
    }
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    let errorCode: string | undefined;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        if (typeof errJson.detail === 'object') {
          errorDetail = errJson.detail.message || JSON.stringify(errJson.detail);
          errorCode = errJson.detail.code;
        } else {
          errorDetail = String(errJson.detail);
        }
      }
    } catch {
      // ignore json parse error on error responses
    }
    throw new ApiError(errorDetail, response.status, errorCode);
  }

  return (await response.json()) as T;
}

export const api = {
  // Check backend health
  checkHealth: async (): Promise<{ status: string; online: boolean }> => {
    try {
      const res = await fetch('/healthz');
      if (res.ok) {
        const data = await res.json();
        return { status: data.status || 'healthy', online: true };
      }
      return { status: 'offline', online: false };
    } catch {
      // Also try direct localhost:8000/healthz in case proxy is bypassing
      try {
        const direct = await fetch('http://localhost:8000/healthz');
        if (direct.ok) {
          const data = await direct.json();
          return { status: data.status || 'healthy', online: true };
        }
      } catch {
        // unreachable
      }
      return { status: 'unreachable', online: false };
    }
  },

  // 1. Simulation & City Graph
  getCityGraph: async (): Promise<CityGraph> => {
    try {
      return await request<CityGraph>('/simulation/city-graph');
    } catch (err) {
      console.warn('[UrbanFlow API] Fallback to seeded city graph:', err);
      return mockCityGraph;
    }
  },

  resetSimulation: async (): Promise<{ status: string; message: string }> => {
    return await request<{ status: string; message: string }>('/simulation/reset', {
      method: 'POST',
    });
  },

  toggleRoadClosure: async (roadId: string, isBlocked: boolean): Promise<any> => {
    return await request('/simulation/road-closure', {
      method: 'POST',
      body: JSON.stringify({ road_id: roadId, is_blocked: isBlocked }),
    });
  },

  toggleRoadDivert: async (roadId: string, isDiverted: boolean): Promise<any> => {
    return await request('/simulation/road-divert', {
      method: 'POST',
      body: JSON.stringify({ road_id: roadId, is_diverted: isDiverted }),
    });
  },

  setSignalPriority: async (nodeIds: string[], active: boolean = true): Promise<any> => {
    return await request('/simulation/signal-priority', {
      method: 'POST',
      body: JSON.stringify({ node_ids: nodeIds, active }),
    });
  },

  detectCandidate: async (
    locationNode: string = 'INT-03',
    roadId: string = 'ROAD-03A',
    candidateType: string = 'possible_collision',
    confidence: number = 0.85
  ): Promise<IncidentRecord> => {
    return await request<IncidentRecord>('/simulation/detect-candidate', {
      method: 'POST',
      body: JSON.stringify({
        location_node: locationNode,
        road_id: roadId,
        candidate_type: candidateType,
        confidence,
        camera_id: 'cctv_camera_01',
      }),
    });
  },

  // 2. Multi-Agent Orchestration
  getOrchestrationState: async (): Promise<OrchestrationState> => {
    try {
      return await request<OrchestrationState>('/orchestration/state');
    } catch (err) {
      console.warn('[UrbanFlow API] Fallback to standby orchestration state:', err);
      return standbyOrchestrationState;
    }
  },

  runScenario: async (
    scenarioName: string = 'Cyber City Emergency Response',
    autoVerify: boolean = false
  ): Promise<OrchestrationState> => {
    return await request<OrchestrationState>('/orchestration/run-scenario', {
      method: 'POST',
      body: JSON.stringify({
        scenario_name: scenarioName,
        auto_verify: autoVerify,
        operator_id: 'OP-CHIEF-01',
        operator_notes: autoVerify
          ? 'Automated verification for full demo run.'
          : 'Candidate event queued for manual operator verification.',
      }),
    });
  },

  // 3. Incidents
  getIncidents: async (): Promise<IncidentRecord[]> => {
    try {
      return await request<IncidentRecord[]>('/incidents');
    } catch (err) {
      console.warn('[UrbanFlow API] Fallback to seeded incidents:', err);
      return [mockOrchestrationState.active_incident!];
    }
  },

  verifyIncident: async (
    incidentId: string,
    verified: boolean = true,
    notes: string = 'Verified by Command Center Operator via CCTV evidence snapshot.'
  ): Promise<IncidentRecord> => {
    return await request<IncidentRecord>(`/incidents/${incidentId}/verify`, {
      method: 'POST',
      body: JSON.stringify({
        verified,
        operator_id: 'OP-CHIEF-01',
        notes,
      }),
    });
  },

  dispatchIncident: async (incidentId: string): Promise<IncidentRecord> => {
    return await request<IncidentRecord>(`/incidents/${incidentId}/dispatch`, {
      method: 'POST',
    });
  },

  resolveIncident: async (
    incidentId: string,
    notes: string = 'Scene cleared and incident resolved by Command Center.'
  ): Promise<IncidentRecord> => {
    return await request<IncidentRecord>(`/incidents/${incidentId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({
        operator_id: 'OP-CHIEF-01',
        notes,
      }),
    });
  },

  // 4. Resources
  getEmergencyUnits: async (): Promise<EmergencyUnit[]> => {
    try {
      return await request<EmergencyUnit[]>('/resources');
    } catch (err) {
      console.warn('[UrbanFlow API] Fallback to seeded emergency fleet:', err);
      return mockEmergencyUnits;
    }
  },

  // 5. Routing
  calculateRoute: async (
    origin: string,
    destination: string,
    avoidRoads: string[] = [],
    algorithm: string = 'astar'
  ): Promise<any> => {
    return await request('/routing/calculate', {
      method: 'POST',
      body: JSON.stringify({
        origin_node: origin,
        destination_node: destination,
        avoid_road_ids: avoidRoads,
        algorithm,
      }),
    });
  },

  // 6. Traffic Intelligence & ML Forecasting (Member 3)
  getRoadForecast: async (roadId: string): Promise<any> => {
    return await request(`/traffic/forecast/${roadId}`);
  },

  getTrafficOverview: async (): Promise<any> => {
    return await request('/traffic/overview');
  },
};
