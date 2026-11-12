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

const BASE_URL = 'http://localhost:8000/api/v1';

async function safeFetch<T>(endpoint: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.warn(`[UrbanFlow API] Fallback activated for ${endpoint}:`, error);
    if (fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

export const api = {
  // 1. Simulation & City Graph
  getCityGraph: async (): Promise<CityGraph> => {
    return safeFetch<CityGraph>('/simulation/city-graph', undefined, mockCityGraph);
  },

  resetSimulation: async (): Promise<{ status: string; message: string }> => {
    return safeFetch('/simulation/reset', { method: 'POST' }, { status: 'success', message: 'Simulation reset to baseline' });
  },

  // 2. Multi-Agent Orchestration
  getOrchestrationState: async (): Promise<OrchestrationState> => {
    return safeFetch<OrchestrationState>('/orchestration/state', undefined, mockOrchestrationState);
  },

  runScenario: async (scenarioName = 'Cyber City Emergency Response'): Promise<OrchestrationState> => {
    return safeFetch<OrchestrationState>(
      '/orchestration/run-scenario',
      {
        method: 'POST',
        body: JSON.stringify({ scenario_name: scenarioName, auto_verify: true }),
      },
      mockOrchestrationState
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
      },
      mockOrchestrationState.active_incident!
    );
  },

  dispatchIncident: async (incidentId: string): Promise<IncidentRecord> => {
    return safeFetch<IncidentRecord>(
      `/incidents/${incidentId}/dispatch`,
      { method: 'POST' },
      mockOrchestrationState.active_incident!
    );
  },

  // 4. Resources
  getEmergencyUnits: async (): Promise<EmergencyUnit[]> => {
    return safeFetch<EmergencyUnit[]>('/resources/', undefined, mockEmergencyUnits);
  },
};
