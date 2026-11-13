import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  OrchestrationState,
  FindPathResult,
  ComparePathResult,
  RandomizeTrafficResult,
} from '../types';
import {
  mockCityGraph,
  mockEmergencyUnits,
  mockOrchestrationState,
  standbyOrchestrationState,
} from './mockData';

// Centralized API configuration
// Supports Vite reverse proxy `/api/v1` or explicit backend URL via environment variable
const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1';

export type BackendStatus = 'live' | 'offline';

type StatusListener = (status: BackendStatus) => void;
type ToastListener = (message: string, type: 'error' | 'success' | 'info') => void;

const statusListeners: Set<StatusListener> = new Set();
let toastListener: ToastListener | null = null;
let currentBackendStatus: BackendStatus = 'offline';

export function getBackendStatus(): BackendStatus {
  return currentBackendStatus;
}

export function onBackendStatusChange(listener: StatusListener): () => void {
  statusListeners.add(listener);
  listener(currentBackendStatus);
  return () => {
    statusListeners.delete(listener);
  };
}

export function registerToastHandler(handler: ToastListener): () => void {
  toastListener = handler;
  return () => {
    if (toastListener === handler) {
      toastListener = null;
    }
  };
}

export function triggerToast(message: string, type: 'error' | 'success' | 'info' = 'error') {
  if (toastListener) {
    toastListener(message, type);
  }
}

function updateBackendStatus(newStatus: BackendStatus) {
  if (currentBackendStatus !== newStatus) {
    currentBackendStatus = newStatus;
    statusListeners.forEach((l) => l(newStatus));
  }
}

async function safeFetch<T>(endpoint: string, options?: RequestInit, fallback?: T): Promise<T> {
  const isPost = options?.method?.toUpperCase() === 'POST';
<<<<<<< HEAD
  const url = `${BASE_URL}${endpoint}`;

  try {
    const res = await fetch(url, {
=======
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${endpoint}`, {
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
<<<<<<< HEAD

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          errorDetail = typeof errJson.detail === 'object'
            ? errJson.detail.message || JSON.stringify(errJson.detail)
            : String(errJson.detail);
        }
      } catch {
        // ignore json parse errors on error responses
      }
      throw new Error(errorDetail);
    }

    updateBackendStatus('live');
    return await res.json();
  } catch (error: any) {
    // On network failure, attempt direct localhost:8000 as fallback if proxy-relative
    if (!BASE_URL.startsWith('http') && !error.message?.startsWith('HTTP')) {
      try {
        const directUrl = `http://localhost:8000/api/v1${endpoint}`;
        const directRes = await fetch(directUrl, {
          ...options,
          headers: { 'Content-Type': 'application/json', ...options?.headers },
        });
        if (directRes.ok) {
          updateBackendStatus('live');
          return await directRes.json();
        }
      } catch {
        // direct fallback also failed
      }
    }

=======
  } catch (netErr: any) {
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
    updateBackendStatus('offline');
    console.warn(`[UrbanFlow API] Network failure for ${endpoint}:`, netErr);
    if (isPost) {
      const errorMsg = `Action failed: Backend is down (${netErr?.message || 'Network unreachable'}). Live simulation actions require the FastAPI backend.`;
      triggerToast(errorMsg, 'error');
      throw new Error(errorMsg);
    }
    if (fallback !== undefined) {
      return fallback;
    }
    throw netErr;
  }

  // Backend responded!
  updateBackendStatus('live');
  if (!res.ok) {
    let detailMsg = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) {
        if (typeof body.detail === 'string') detailMsg = body.detail;
        else if (body.detail.message) detailMsg = body.detail.message;
      }
    } catch (_) {}
    const errorMsg = detailMsg || `API error ${res.status}`;
    if (isPost) {
      triggerToast(errorMsg, 'error');
    }
    throw new Error(errorMsg);
  }

  return await res.json();
}

export const api = {
  // Check backend health
  checkHealth: async (): Promise<{ status: string; online: boolean }> => {
    try {
      const res = await fetch('/healthz');
      if (res.ok) {
        const data = await res.json();
        updateBackendStatus('live');
        return { status: data.status || 'healthy', online: true };
      }
      return { status: 'offline', online: false };
    } catch {
      // Also try direct localhost:8000/healthz in case proxy is bypassing
      try {
        const direct = await fetch('http://localhost:8000/healthz');
        if (direct.ok) {
          const data = await direct.json();
          updateBackendStatus('live');
          return { status: data.status || 'healthy', online: true };
        }
      } catch {
        // unreachable
      }
      updateBackendStatus('offline');
      return { status: 'unreachable', online: false };
    }
  },

  // 1. Simulation & City Graph
  getCityGraph: async (): Promise<CityGraph> => {
    return safeFetch<CityGraph>('/simulation/city-graph', undefined, mockCityGraph);
  },

  resetSimulation: async (): Promise<{ status: string; message: string }> => {
    return safeFetch('/simulation/reset', { method: 'POST' });
  },

<<<<<<< HEAD
  toggleRoadClosure: async (roadId: string, isBlocked: boolean): Promise<any> => {
    return safeFetch('/simulation/road-closure', {
      method: 'POST',
      body: JSON.stringify({ road_id: roadId, is_blocked: isBlocked }),
    });
  },

  toggleRoadDivert: async (roadId: string, isDiverted: boolean): Promise<any> => {
    return safeFetch('/simulation/road-divert', {
      method: 'POST',
      body: JSON.stringify({ road_id: roadId, is_diverted: isDiverted }),
    });
  },

  setSignalPriority: async (nodeIds: string[], active: boolean = true): Promise<any> => {
    return safeFetch('/simulation/signal-priority', {
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
    return safeFetch<IncidentRecord>('/simulation/detect-candidate', {
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
    return safeFetch<OrchestrationState>('/orchestration/state', undefined, standbyOrchestrationState);
  },

  runScenario: async (
    scenarioName: string = 'Cyber City Emergency Response',
    autoVerify: boolean = false
  ): Promise<OrchestrationState> => {
    return safeFetch<OrchestrationState>('/orchestration/run-scenario', {
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
=======
  getSimulationTick: async (speed = 5.0): Promise<EmergencyUnit[]> => {
    return safeFetch<EmergencyUnit[]>(`/simulation/tick?speed=${speed}`, undefined, mockEmergencyUnits);
  },

  // 2. Multi-Agent Orchestration
  getOrchestrationState: async (): Promise<OrchestrationState> => {
    return safeFetch<OrchestrationState>('/orchestration/state', undefined, mockOrchestrationState);
  },

  runScenario: async (
    scenarioName = 'Cyber City Emergency Response',
    autoVerify = true,
    scenarioType?: string,
    seed?: number
  ): Promise<OrchestrationState> => {
    return safeFetch<OrchestrationState>(
      '/orchestration/run-scenario',
      {
        method: 'POST',
        body: JSON.stringify({
          scenario_name: scenarioName,
          auto_verify: autoVerify,
          scenario_type: scenarioType,
          seed: seed,
        }),
      }
    );
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
  },

  // 3. Incidents
  getIncidents: async (): Promise<IncidentRecord[]> => {
    return safeFetch<IncidentRecord[]>('/incidents', undefined, [mockOrchestrationState.active_incident!]);
  },

  verifyIncident: async (
    incidentId: string,
    verified: boolean = true,
    notes: string = 'Verified by Command Center Operator via CCTV evidence snapshot.'
  ): Promise<IncidentRecord> => {
    return safeFetch<IncidentRecord>(`/incidents/${incidentId}/verify`, {
      method: 'POST',
      body: JSON.stringify({
        verified,
        operator_id: 'OP-CHIEF-01',
        notes,
      }),
    });
  },

  dispatchIncident: async (incidentId: string): Promise<IncidentRecord> => {
    return safeFetch<IncidentRecord>(`/incidents/${incidentId}/dispatch`, {
      method: 'POST',
    });
  },

  resolveIncident: async (
    incidentId: string,
    notes: string = 'Scene cleared and incident resolved by Command Center.'
  ): Promise<IncidentRecord> => {
    return safeFetch<IncidentRecord>(`/incidents/${incidentId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({
        operator_id: 'OP-CHIEF-01',
        notes,
      }),
    });
  },

  // 4. Resources
  getEmergencyUnits: async (): Promise<EmergencyUnit[]> => {
    return safeFetch<EmergencyUnit[]>('/resources', undefined, mockEmergencyUnits);
  },

  // 5. Routing
  calculateRoute: async (
    origin: string,
    destination: string,
    avoidRoads: string[] = [],
    algorithm: string = 'astar'
  ): Promise<any> => {
    return safeFetch('/routing/calculate', {
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
    return safeFetch(`/traffic/forecast/${roadId}`);
  },

  getTrafficOverview: async (): Promise<any> => {
    return safeFetch('/traffic/overview');
  },

  // 7. Route Optimization & Comparison (Find Path Mode)
  findPath: async (
    fromNode: string,
    toNode: string,
    mode: 'optimised' | 'baseline' = 'optimised',
    algorithm: 'astar' | 'dijkstra' = 'astar'
  ): Promise<FindPathResult> => {
    return safeFetch<FindPathResult>('/routing/find-path', {
      method: 'POST',
      body: JSON.stringify({
        from_node: fromNode,
        to_node: toNode,
        mode,
        algorithm,
      }),
    });
  },

  comparePaths: async (
    fromNode: string,
    toNode: string,
    algorithm: 'astar' | 'dijkstra' = 'astar'
  ): Promise<ComparePathResult> => {
    return safeFetch<ComparePathResult>('/routing/compare', {
      method: 'POST',
      body: JSON.stringify({
        from_node: fromNode,
        to_node: toNode,
        algorithm,
      }),
    });
  },

  randomizeTraffic: async (
    seed?: number,
    minBlocks: number = 2,
    maxBlocks: number = 4
  ): Promise<RandomizeTrafficResult> => {
    return safeFetch<RandomizeTrafficResult>('/routing/randomize-traffic', {
      method: 'POST',
      body: JSON.stringify({
        seed,
        min_blocks: minBlocks,
        max_blocks: maxBlocks,
      }),
    });
  },

  // 5. Find Path Mode & Traffic Comparison
  findPath: async (
    fromNode: string,
    toNode: string,
    mode: 'optimised' | 'baseline' = 'optimised',
    algorithm: 'astar' | 'dijkstra' = 'astar'
  ): Promise<any> => {
    return safeFetch(
      '/routing/find-path',
      {
        method: 'POST',
        body: JSON.stringify({
          from_node: fromNode,
          to_node: toNode,
          mode: mode,
          algorithm: algorithm,
        }),
      }
    );
  },

  comparePaths: async (
    fromNode: string,
    toNode: string,
    algorithm: 'astar' | 'dijkstra' = 'astar'
  ): Promise<any> => {
    return safeFetch(
      '/routing/compare',
      {
        method: 'POST',
        body: JSON.stringify({
          from_node: fromNode,
          to_node: toNode,
          algorithm: algorithm,
        }),
      }
    );
  },

  randomizeTraffic: async (seed?: number, numBlocked?: number): Promise<any> => {
    return safeFetch(
      '/routing/randomize-traffic',
      {
        method: 'POST',
        body: JSON.stringify({
          seed: seed,
          num_blocked_roads: numBlocked,
        }),
      }
    );
  },

  congestBaselineRoute: async (fromNode: string, toNode: string): Promise<any> => {
    return safeFetch(
      '/routing/congest-baseline',
      {
        method: 'POST',
        body: JSON.stringify({
          from_node: fromNode,
          to_node: toNode,
        }),
      }
    );
  },
};
