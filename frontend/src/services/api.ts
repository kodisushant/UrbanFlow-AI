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
} from './mockData';

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
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  } catch (netErr: any) {
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
  // 1. Simulation & City Graph
  getCityGraph: async (): Promise<CityGraph> => {
    return safeFetch<CityGraph>('/simulation/city-graph', undefined, mockCityGraph);
  },

  resetSimulation: async (): Promise<{ status: string; message: string }> => {
    return safeFetch('/simulation/reset', { method: 'POST' });
  },

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
  },

  // 3. Incidents
  getIncidents: async (): Promise<IncidentRecord[]> => {
    return safeFetch<IncidentRecord[]>('/incidents/', undefined, [mockOrchestrationState.active_incident!]);
  },

  verifyIncident: async (incidentId: string, notes = 'Verified by Command Center Operator'): Promise<IncidentRecord> => {
    return safeFetch<IncidentRecord>(
      `/incidents/${incidentId}/verify`,
      {
        method: 'POST',
        body: JSON.stringify({ verified: true, operator_id: 'OP-CHIEF-01', notes }),
      }
    );
  },

  dispatchIncident: async (incidentId: string): Promise<IncidentRecord> => {
    return safeFetch<IncidentRecord>(
      `/incidents/${incidentId}/dispatch`,
      { method: 'POST' }
    );
  },

  // 4. Resources
  getEmergencyUnits: async (): Promise<EmergencyUnit[]> => {
    return safeFetch<EmergencyUnit[]>('/resources/', undefined, mockEmergencyUnits);
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
};
