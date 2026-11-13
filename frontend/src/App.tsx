import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Header } from './components/Header';
import { CityMap } from './components/CityMap';
import { CCTVPanel } from './components/CCTVPanel';
import { IncidentPanel } from './components/IncidentPanel';
import { ResourceList } from './components/ResourceList';
import { AgentLogFeed } from './components/AgentLogFeed';
import {
  api,
  BackendStatus,
  getBackendStatus,
  onBackendStatusChange,
  registerToastHandler,
} from './services/api';
import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  OrchestrationState,
  RouteResult,
} from './types';
import {
  mockCityGraph,
  mockEmergencyUnits,
  mockOrchestrationState,
  standbyOrchestrationState,
} from './services/mockData';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface ToastMessage {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
}

export const App: React.FC = () => {
  const [cityGraph, setCityGraph] = useState<CityGraph>(mockCityGraph);
  const [orchestration, setOrchestration] = useState<OrchestrationState>(standbyOrchestrationState);
  const [emergencyUnits, setEmergencyUnits] = useState<EmergencyUnit[]>(mockEmergencyUnits);
  const [simulationTime, setSimulationTime] = useState<number>(0.0);
  const [isRunning, setIsRunning] = useState<boolean>(true);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>(getBackendStatus());

  // Operation loading states
  const [isOperating, setIsOperating] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
  const [isResolving, setIsResolving] = useState<boolean>(false);

  // Toast notifications for user feedback
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
  };

  // Subscribe to backend connectivity status & toast alerts
  useEffect(() => {
    const unregisterStatus = onBackendStatusChange((status) => {
      setBackendStatus(status);
    });

    const unregisterToast = registerToastHandler((message, type) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    });

    return () => {
      unregisterStatus();
      unregisterToast();
    };
  }, []);

  // Fetch full state from backend
  const refreshAll = useCallback(async () => {
    try {
      await api.checkHealth();
      const [graph, state, units] = await Promise.all([
        api.getCityGraph(),
        api.getOrchestrationState(),
        api.getEmergencyUnits(),
      ]);
      setCityGraph(graph);
      setOrchestration(state);
      setEmergencyUnits(units);
    } catch (err: any) {
      console.warn('Backend refresh error:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Periodic health check every 10s
  useEffect(() => {
    const timer = setInterval(() => {
      api.checkHealth();
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  // Simulation timer tick
  useEffect(() => {
    let interval: any = null;
    if (isRunning) {
      interval = setInterval(() => {
        setSimulationTime((prev) => +(prev + 0.5).toFixed(1));
      }, 500);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  // 1. One-click Hackathon Scenario Trigger (Full 8-Step Auto Demo)
  const handleRunFullScenario = async () => {
    setIsOperating(true);
    try {
      showNotification('Running full automated 8-step emergency response scenario...', 'info');
      const state = await api.runScenario('Cyber City Emergency Response', true);
      setOrchestration(state);
      const units = await api.getEmergencyUnits();
      setEmergencyUnits(units);
      const graph = await api.getCityGraph();
      setCityGraph(graph);
      showNotification('Full scenario executed: Units dispatched and Green Corridor active!', 'success');
    } catch (err: any) {
      showNotification(`Scenario trigger error: ${err.message}`, 'error');
    } finally {
      setIsOperating(false);
    }
  };

  // 2. Step-by-Step Scenario (Detection -> Operator Review -> Dispatch)
  const handleRunStepScenario = async () => {
    setIsOperating(true);
    try {
      showNotification('Simulating candidate detection at INT-03. Awaiting operator review.', 'info');
      const state = await api.runScenario('Cyber City Emergency Response', false);
      setOrchestration(state);
      await refreshAll();
      showNotification('Candidate incident detected! Review CCTV and verify or reject.', 'info');
    } catch (err: any) {
      showNotification(`Step scenario error: ${err.message}`, 'error');
    } finally {
      setIsOperating(false);
    }
  };

  // 3. Instant Reset Action
  const handleReset = async () => {
    setIsOperating(true);
    setSimulationTime(0.0);
    try {
      await api.resetSimulation();
      await refreshAll();
      showNotification('System reset to baseline standby. All corridors and units restored.', 'success');
    } catch (err: any) {
      showNotification(`Reset failed: ${err.message}`, 'error');
    } finally {
      setIsOperating(false);
    }
  };

  // 4. Operator Verification Action
  const handleVerify = async () => {
    if (!orchestration.active_incident) return;
    setIsVerifying(true);
    try {
      const updated = await api.verifyIncident(
        orchestration.active_incident.incident_id,
        true,
        'Confirmed collision via CCTV. Emergency response authorized.'
      );
      showNotification(`Incident ${updated.incident_id} verified. Emergency units allocated!`, 'success');
      await refreshAll();
    } catch (err: any) {
      showNotification(`Verification failed: ${err.message}`, 'error');
    } finally {
      setIsVerifying(false);
    }
  };

  // 5. Operator Rejection Action (False Alarm / Safety Rule)
  const handleReject = async () => {
    if (!orchestration.active_incident) return;
    setIsRejecting(true);
    try {
      const updated = await api.verifyIncident(
        orchestration.active_incident.incident_id,
        false,
        'Rejected by Operator as false alarm / normal stationary traffic.'
      );
      showNotification(`Incident ${updated.incident_id} rejected as false alarm. Dispatch aborted.`, 'info');
      await refreshAll();
    } catch (err: any) {
      showNotification(`Rejection failed: ${err.message}`, 'error');
    } finally {
      setIsRejecting(false);
    }
  };

  // 6. Dispatch Emergency Units Action
  const handleDispatch = async () => {
    if (!orchestration.active_incident) return;
    setIsDispatching(true);
    try {
      const updated = await api.dispatchIncident(orchestration.active_incident.incident_id);
      showNotification(
        `Emergency units dispatched for ${updated.incident_id}. A* route & green corridors active!`,
        'success'
      );
      await refreshAll();
    } catch (err: any) {
      showNotification(`Dispatch blocked: ${err.message}`, 'error');
    } finally {
      setIsDispatching(false);
    }
  };

  // 7. Resolve Incident Action
  const handleResolve = async () => {
    if (!orchestration.active_incident) return;
    setIsResolving(true);
    try {
      await api.resolveIncident(
        orchestration.active_incident.incident_id,
        'Scene cleared and units returned to stations.'
      );
      showNotification('Incident resolved: road closures cleared and units returned.', 'success');
      await refreshAll();
    } catch (err: any) {
      showNotification(`Resolution failed: ${err.message}`, 'error');
    } finally {
      setIsResolving(false);
    }
  };

  // 8. Simulate Incident Detection
  const handleSimulateDetection = async (
    locationNode: string = 'INT-03',
    candidateType: string = 'possible_collision'
  ) => {
    setIsOperating(true);
    try {
      const roadId = locationNode === 'INT-03' ? 'ROAD-03A' : 'ROAD-01A';
      await api.detectCandidate(locationNode, roadId, candidateType, 0.85);
      showNotification(`Candidate ${candidateType} detected at ${locationNode}.`, 'info');
      await refreshAll();
    } catch (err: any) {
      showNotification(`Detection trigger error: ${err.message}`, 'error');
    } finally {
      setIsOperating(false);
    }
  };

  // 9. Interactive Road Closure Toggle
  const handleToggleRoadClosure = async (roadId: string, currentBlocked: boolean) => {
    try {
      await api.toggleRoadClosure(roadId, !currentBlocked);
      showNotification(`Road ${roadId} ${!currentBlocked ? 'closed' : 'reopened'}.`, 'info');
      await refreshAll();
    } catch (err: any) {
      showNotification(`Failed to toggle closure: ${err.message}`, 'error');
    }
  };

  const primaryEmergencyRoute: RouteResult | null =
    orchestration.active_routes && orchestration.active_routes.length > 0
      ? orchestration.active_routes[0]
      : null;

  const diversionRoute: RouteResult | null =
    orchestration.traffic_diversions?.diversion_route || null;

  const corridorNodes =
    orchestration.signal_priority_corridor?.active
      ? orchestration.signal_priority_corridor.corridor_nodes
      : [];

  const dispatchedCount = emergencyUnits.filter((u) => u.status === 'dispatched').length;

  return (
    <div className="flex flex-col h-screen w-screen bg-[#090d16] text-slate-100 overflow-hidden font-sans">
      {/* Top Bar Header */}
      <Header
        simulationTime={simulationTime}
        isRunning={isRunning}
        onToggleTimer={() => setIsRunning(!isRunning)}
        onRunFullScenario={handleRunFullScenario}
        onRunStepScenario={handleRunStepScenario}
        onReset={handleReset}
        onRefresh={refreshAll}
        activeIncidentsCount={
          orchestration.active_incident && orchestration.active_incident.status !== 'resolved'
            ? 1
            : 0
        }
        dispatchedUnitsCount={dispatchedCount}
        activeCorridorsCount={corridorNodes.length > 0 ? 1 : 0}
        backendStatus={backendStatus}
        isOperating={isOperating}
      />

      {/* Floating Notification Toast */}
      {notification && (
        <div
          className={`absolute top-18 right-6 z-[2000] flex items-center space-x-2 px-4 py-2.5 rounded-lg shadow-2xl border text-xs backdrop-blur-md transition-all ${
            notification.type === 'error'
              ? 'bg-rose-950/90 text-rose-200 border-rose-700'
              : notification.type === 'success'
              ? 'bg-emerald-950/90 text-emerald-200 border-emerald-700'
              : 'bg-cyan-950/90 text-cyan-200 border-cyan-700'
          }`}
        >
          {notification.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          )}
          <span className="font-semibold">{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            className="ml-2 hover:opacity-75 p-0.5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Command Center Grid */}
      <main className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden">
        {/* Left Sidebar: Vision & Incident Triage (3 Cols) */}
        <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pr-0.5">
          <CCTVPanel
            cameraId={orchestration.active_incident?.source || 'cctv_camera_01'}
            hasCandidateAlert={
              !!orchestration.active_incident &&
              orchestration.active_incident.status !== 'resolved'
            }
            onAnalyzeFeed={(camId) => handleSimulateDetection(camId === 'cctv_camera_01' ? 'INT-03' : 'INT-01')}
          />
          <IncidentPanel
            incident={orchestration.active_incident}
            onVerify={handleVerify}
            onReject={handleReject}
            onDispatch={handleDispatch}
            onResolve={handleResolve}
            onSimulateDetection={handleSimulateDetection}
            isVerifying={isVerifying}
            isRejecting={isRejecting}
            isDispatching={isDispatching}
            isResolving={isResolving}
          />
        </div>

        {/* Center: Leaflet Interactive Command Center Map (6 Cols) */}
        <div className="col-span-6 rounded-lg overflow-hidden border border-slate-800 shadow-2xl relative min-h-[480px]">
          <CityMap
            cityGraph={cityGraph}
            activeIncident={orchestration.active_incident}
            emergencyUnits={emergencyUnits}
            emergencyRoute={primaryEmergencyRoute}
            diversionRoute={diversionRoute}
            activeCorridorNodes={corridorNodes}
            onToggleRoadClosure={handleToggleRoadClosure}
            onSimulateAtNode={(nodeId) => handleSimulateDetection(nodeId)}
          />
        </div>

        {/* Right Sidebar: Fleet Ops & Multi-Agent Intelligence (3 Cols) */}
        <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pl-0.5">
          <ResourceList units={emergencyUnits} />
          <AgentLogFeed logs={orchestration.agent_logs || []} />
        </div>
      </main>

      {/* Action Error & Status Toast Notifications */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col space-y-2 max-w-md pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start space-x-2.5 p-3.5 rounded-lg shadow-2xl border text-xs font-sans transition-all duration-200 ${
              toast.type === 'error'
                ? 'bg-rose-950/95 border-rose-600/80 text-rose-200'
                : toast.type === 'success'
                ? 'bg-emerald-950/95 border-emerald-600/80 text-emerald-200'
                : 'bg-slate-900/95 border-slate-700 text-slate-200'
            }`}
          >
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-bold uppercase tracking-wider text-[10px] text-rose-400">
                Action Error
              </div>
              <div className="mt-0.5 text-slate-200">{toast.message}</div>
            </div>
            <button
              onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
              className="text-slate-400 hover:text-white p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
