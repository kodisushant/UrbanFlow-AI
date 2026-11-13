import React, { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Header, DashboardMode } from './components/Header';
import { CityMap } from './components/CityMap';
import { CCTVPanel } from './components/CCTVPanel';
import { IncidentPanel } from './components/IncidentPanel';
import { ResourceList } from './components/ResourceList';
import { AgentLogFeed } from './components/AgentLogFeed';
import { FindPathControls } from './components/FindPathControls';
import { PathComparisonPanel } from './components/PathComparisonPanel';
import {
  api,
  BackendStatus,
  getBackendStatus,
  onBackendStatusChange,
  registerToastHandler,
  triggerToast,
} from './services/api';
import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  OrchestrationState,
  RouteResult,
  IntersectionNode,
  FindPathResult,
  ComparePathsResult,
} from './types';
import {
  mockCityGraph,
  mockEmergencyUnits,
  mockOrchestrationState,
} from './services/mockData';

interface ToastMessage {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info';
}

export const App: React.FC = () => {
  const [cityGraph, setCityGraph] = useState<CityGraph>(mockCityGraph);
  const [orchestration, setOrchestration] = useState<OrchestrationState>(mockOrchestrationState);
  const [emergencyUnits, setEmergencyUnits] = useState<EmergencyUnit[]>(mockEmergencyUnits);
  const [simulationTime, setSimulationTime] = useState<number>(0.0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>(getBackendStatus());
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Find Path Mode State
  const [dashboardMode, setDashboardMode] = useState<DashboardMode>('scenario');
  const [fromNode, setFromNode] = useState<IntersectionNode | null>(null);
  const [toNode, setToNode] = useState<IntersectionNode | null>(null);
  const [selectionStep, setSelectionStep] = useState<'from' | 'to'>('from');
  const [optimisedRoute, setOptimisedRoute] = useState<FindPathResult | null>(null);
  const [baselineRoute, setBaselineRoute] = useState<FindPathResult | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparePathsResult | null>(null);
  const [isPathComputing, setIsPathComputing] = useState<boolean>(false);
  const [reachabilityError, setReachabilityError] = useState<string | null>(null);

  // Phase 3 Route Animation / Race Simulation State
  const [isRaceAnimating, setIsRaceAnimating] = useState<boolean>(false);
  const [isRacePaused, setIsRacePaused] = useState<boolean>(false);
  const [raceSpeed, setRaceSpeed] = useState<number>(1);
  const [animProgressOpt, setAnimProgressOpt] = useState<number>(0.0);
  const [animProgressBase, setAnimProgressBase] = useState<number>(0.0);
  const [animPosOpt, setAnimPosOpt] = useState<[number, number] | null>(null);
  const [animPosBase, setAnimPosBase] = useState<[number, number] | null>(null);
  const [baseBlockedPause, setBaseBlockedPause] = useState<boolean>(false);
  const [optArrived, setOptArrived] = useState<boolean>(false);
  const [baseArrived, setBaseArrived] = useState<boolean>(false);
  const [optElapsedTimeSec, setOptElapsedTimeSec] = useState<number>(0);
  const [baseElapsedTimeSec, setBaseElapsedTimeSec] = useState<number>(0);

  // Animation frame ref for clean cancellation
  const animFrameRef = React.useRef<number | null>(null);
  const animStateRef = React.useRef({
    startTime: 0,
    pausedTime: 0,
    isPaused: false,
    speed: 1,
    optDuration: 0,
    baseDuration: 0,
    hasBlock: false,
    blockRatio: 0.5,
  });

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

  // Initial load
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [graph, state, units] = await Promise.all([
          api.getCityGraph(),
          api.getOrchestrationState(),
          api.getEmergencyUnits(),
        ]);
        setCityGraph(graph);
        setOrchestration(state);
        setEmergencyUnits(units);
      } catch (err) {
        console.warn('Using seeded tactical mock data:', err);
      }
    }
    loadInitialData();
  }, []);

  const hasActiveUnits = emergencyUnits.some(
    (u) => u.status !== 'available' && u.status !== 'stationed'
  );

  // Poll units every 1s while any unit is active (en route, on scene, loading, transporting, at hospital, returning)
  // Run the T+ simulation clock whenever units are active, and stop it when all return to standby.
  useEffect(() => {
    let interval: any = null;
    if (hasActiveUnits) {
      interval = setInterval(async () => {
        setSimulationTime((prev) => +(prev + 1.0).toFixed(1));
        try {
          const [updatedUnits, state] = await Promise.all([
            api.getSimulationTick(),
            api.getOrchestrationState(),
          ]);
          setEmergencyUnits(updatedUnits);
          setOrchestration(state);
        } catch (err) {
          console.warn('Polling simulation tick failed:', err);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [hasActiveUnits]);

  // One-click Hackathon Scenario Trigger (Auto-verifies & Auto-dispatches)
  const handleRunScenario = async () => {
    setIsRunning(true);
    setSimulationTime(0.0);
    try {
      const state = await api.runScenario('Cyber City Emergency Response', true);
      setOrchestration(state);
      const units = await api.getEmergencyUnits();
      setEmergencyUnits(units);
    } catch (err) {
      console.error('Failed to trigger scenario:', err);
    } finally {
      setIsRunning(false);
    }
  };

  // Instant Reset Action (Works in both modes without leaving stale state)
  const handleReset = async () => {
    setIsRunning(false);
    setSimulationTime(0.0);
    // Clear Find Path state
    setFromNode(null);
    setToNode(null);
    setOptimisedRoute(null);
    setBaselineRoute(null);
    setComparisonResult(null);
    setReachabilityError(null);
    setSelectionStep('from');

    try {
      await api.resetSimulation();
      const [graph, state, units] = await Promise.all([
        api.getCityGraph(),
        api.getOrchestrationState(),
        api.getEmergencyUnits(),
      ]);
      setCityGraph(graph);
      setOrchestration(state);
      setEmergencyUnits(units);
    } catch (err) {
      console.error('Failed to reset simulation:', err);
    }
  };

  // Find Path Mode Handlers
  const handleMapNodeClick = (node: IntersectionNode) => {
    setReachabilityError(null);
    if (selectionStep === 'from') {
      setFromNode(node);
      setSelectionStep('to');
    } else {
      setToNode(node);
    }
  };

  const stopRaceAnimation = () => {
    if (animFrameRef.current !== null) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    setIsRaceAnimating(false);
    setIsRacePaused(false);
  };

  const handleResetRace = () => {
    stopRaceAnimation();
    setAnimProgressOpt(0.0);
    setAnimProgressBase(0.0);
    setAnimPosOpt(null);
    setAnimPosBase(null);
    setBaseBlockedPause(false);
    setOptArrived(false);
    setBaseArrived(false);
    setOptElapsedTimeSec(0);
    setBaseElapsedTimeSec(0);
  };

  // Clean up animation on unmount or mode switch
  useEffect(() => {
    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  // Helper to interpolate along polyline geometry by progress (0 to 1)
  const interpolateAlongGeometry = (
    geometry: [number, number][],
    progress: number
  ): [number, number] => {
    if (!geometry || geometry.length === 0) return [17.4485, 78.374];
    if (geometry.length === 1 || progress <= 0) return geometry[0];
    if (progress >= 1) return geometry[geometry.length - 1];

    const segLens: number[] = [];
    let totalLen = 0;
    for (let i = 0; i < geometry.length - 1; i++) {
      const d = Math.hypot(
        geometry[i + 1][0] - geometry[i][0],
        geometry[i + 1][1] - geometry[i][1]
      );
      segLens.push(d);
      totalLen += d;
    }
    if (totalLen <= 0) return geometry[0];

    const targetDist = progress * totalLen;
    let accumulated = 0;
    for (let i = 0; i < segLens.length; i++) {
      if (accumulated + segLens[i] >= targetDist) {
        const segProgress = (targetDist - accumulated) / segLens[i];
        return [
          geometry[i][0] + segProgress * (geometry[i + 1][0] - geometry[i][0]),
          geometry[i][1] + segProgress * (geometry[i + 1][1] - geometry[i][1]),
        ];
      }
      accumulated += segLens[i];
    }
    return geometry[geometry.length - 1];
  };

  const handleStartRace = () => {
    stopRaceAnimation();
    if (!optimisedRoute && !baselineRoute) return;

    // Simulation scale: 1 simulated minute = 1 real second = 1000ms
    // Real travel times are in seconds. Simulated duration in ms = (travel_time_seconds / 60) * 1000 = travel_time_seconds * 16.666ms
    const optDuration = (optimisedRoute?.estimated_travel_time_seconds || 60) * 16.666;
    const baseDuration = (baselineRoute?.estimated_travel_time_seconds || 90) * 16.666;
    const hasBlock = baselineRoute?.has_blocked_segments || false;

    animStateRef.current = {
      startTime: performance.now(),
      pausedTime: 0,
      isPaused: false,
      speed: raceSpeed,
      optDuration,
      baseDuration,
      hasBlock,
      blockRatio: 0.5,
    };

    setIsRaceAnimating(true);
    setIsRacePaused(false);
    setOptArrived(false);
    setBaseArrived(false);
    setBaseBlockedPause(false);

    const step = (now: number) => {
      if (animStateRef.current.isPaused) return;

      const elapsed = (now - animStateRef.current.startTime) * animStateRef.current.speed;

      // 1. Optimised Vehicle Progress
      let pOpt = Math.min(1.0, elapsed / animStateRef.current.optDuration);
      if (optimisedRoute?.geometry?.length) {
        setAnimProgressOpt(pOpt);
        setAnimPosOpt(interpolateAlongGeometry(optimisedRoute.geometry, pOpt));
        const elapsedSecOpt = Math.min(
          optimisedRoute.estimated_travel_time_seconds,
          (elapsed / animStateRef.current.optDuration) * optimisedRoute.estimated_travel_time_seconds
        );
        setOptElapsedTimeSec(elapsedSecOpt);
        if (pOpt >= 1.0) setOptArrived(true);
      }

      // 2. Baseline Vehicle Progress with Block Pause
      let pBase = 0.0;
      if (baselineRoute?.geometry?.length) {
        if (animStateRef.current.hasBlock) {
          // Pause at 50% for detour penalty duration
          const preBlockDuration = animStateRef.current.baseDuration * 0.45;
          const pauseDuration = 4000; // 4s visible blocked delay
          if (elapsed < preBlockDuration) {
            pBase = (elapsed / preBlockDuration) * 0.5;
            setBaseBlockedPause(false);
          } else if (elapsed < preBlockDuration + pauseDuration) {
            pBase = 0.5;
            setBaseBlockedPause(true);
          } else {
            setBaseBlockedPause(false);
            const postElapsed = elapsed - (preBlockDuration + pauseDuration);
            const postDuration = animStateRef.current.baseDuration * 0.55;
            pBase = 0.5 + Math.min(0.5, (postElapsed / postDuration) * 0.5);
          }
        } else {
          pBase = Math.min(1.0, elapsed / animStateRef.current.baseDuration);
        }

        setAnimProgressBase(pBase);
        setAnimPosBase(interpolateAlongGeometry(baselineRoute.geometry, pBase));
        const elapsedSecBase = Math.min(
          baselineRoute.estimated_travel_time_seconds,
          pBase * baselineRoute.estimated_travel_time_seconds
        );
        setBaseElapsedTimeSec(elapsedSecBase);
        if (pBase >= 1.0) setBaseArrived(true);
      }

      if (pOpt >= 1.0 && pBase >= 1.0) {
        setIsRaceAnimating(false);
        return;
      }

      animFrameRef.current = requestAnimationFrame(step);
    };

    animFrameRef.current = requestAnimationFrame(step);
  };

  const handlePauseRace = () => {
    if (animFrameRef.current !== null) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    animStateRef.current.pausedTime = performance.now();
    animStateRef.current.isPaused = true;
    setIsRacePaused(true);
  };

  const handleResumeRace = () => {
    if (!isRaceAnimating) return;
    const pauseDelta = performance.now() - animStateRef.current.pausedTime;
    animStateRef.current.startTime += pauseDelta;
    animStateRef.current.isPaused = false;
    setIsRacePaused(false);

    const step = (now: number) => {
      if (animStateRef.current.isPaused) return;
      const elapsed = (now - animStateRef.current.startTime) * animStateRef.current.speed;

      let pOpt = Math.min(1.0, elapsed / animStateRef.current.optDuration);
      if (optimisedRoute?.geometry?.length) {
        setAnimProgressOpt(pOpt);
        setAnimPosOpt(interpolateAlongGeometry(optimisedRoute.geometry, pOpt));
        const elapsedSecOpt = Math.min(
          optimisedRoute.estimated_travel_time_seconds,
          (elapsed / animStateRef.current.optDuration) * optimisedRoute.estimated_travel_time_seconds
        );
        setOptElapsedTimeSec(elapsedSecOpt);
        if (pOpt >= 1.0) setOptArrived(true);
      }

      let pBase = 0.0;
      if (baselineRoute?.geometry?.length) {
        if (animStateRef.current.hasBlock) {
          const preBlockDuration = animStateRef.current.baseDuration * 0.45;
          const pauseDuration = 4000;
          if (elapsed < preBlockDuration) {
            pBase = (elapsed / preBlockDuration) * 0.5;
            setBaseBlockedPause(false);
          } else if (elapsed < preBlockDuration + pauseDuration) {
            pBase = 0.5;
            setBaseBlockedPause(true);
          } else {
            setBaseBlockedPause(false);
            const postElapsed = elapsed - (preBlockDuration + pauseDuration);
            const postDuration = animStateRef.current.baseDuration * 0.55;
            pBase = 0.5 + Math.min(0.5, (postElapsed / postDuration) * 0.5);
          }
        } else {
          pBase = Math.min(1.0, elapsed / animStateRef.current.baseDuration);
        }

        setAnimProgressBase(pBase);
        setAnimPosBase(interpolateAlongGeometry(baselineRoute.geometry, pBase));
        const elapsedSecBase = Math.min(
          baselineRoute.estimated_travel_time_seconds,
          pBase * baselineRoute.estimated_travel_time_seconds
        );
        setBaseElapsedTimeSec(elapsedSecBase);
        if (pBase >= 1.0) setBaseArrived(true);
      }

      if (pOpt >= 1.0 && pBase >= 1.0) {
        setIsRaceAnimating(false);
        return;
      }
      animFrameRef.current = requestAnimationFrame(step);
    };

    animFrameRef.current = requestAnimationFrame(step);
  };

  const handleSpeedChange = (speed: number) => {
    setRaceSpeed(speed);
    animStateRef.current.speed = speed;
  };

  // Mode Switch Helper
  const handleModeChange = (mode: DashboardMode) => {
    stopRaceAnimation();
    setDashboardMode(mode);
  };

  const handleClearPoints = () => {
    stopRaceAnimation();
    setFromNode(null);
    setToNode(null);
    setOptimisedRoute(null);
    setBaselineRoute(null);
    setComparisonResult(null);
    setReachabilityError(null);
    setSelectionStep('from');
  };

  const handleSwapPoints = () => {
    stopRaceAnimation();
    const prevFrom = fromNode;
    setFromNode(toNode);
    setToNode(prevFrom);
    setOptimisedRoute(null);
    setBaselineRoute(null);
    setComparisonResult(null);
    setReachabilityError(null);
  };

  const handleOptimisePath = async () => {
    if (!fromNode || !toNode) return;
    stopRaceAnimation();
    setIsPathComputing(true);
    setReachabilityError(null);
    try {
      const comp = await api.comparePaths(fromNode.node_id, toNode.node_id, 'astar');
      setComparisonResult(comp);
      setOptimisedRoute(comp.optimised);
      if (!comp.is_reachable || !comp.optimised.is_reachable) {
        setReachabilityError(`Destination '${toNode.name}' is unreachable from '${fromNode.name}' avoiding road closures.`);
      }
    } catch (err: any) {
      setReachabilityError(err?.message || 'Failed to compute optimised route.');
    } finally {
      setIsPathComputing(false);
    }
  };

  const handleBaselinePath = async () => {
    if (!fromNode || !toNode) return;
    stopRaceAnimation();
    setIsPathComputing(true);
    setReachabilityError(null);
    try {
      const comp = await api.comparePaths(fromNode.node_id, toNode.node_id, 'astar');
      setComparisonResult(comp);
      setBaselineRoute(comp.baseline);
      if (!comp.baseline.is_reachable) {
        setReachabilityError(`Destination '${toNode.name}' has no physical graph connection from '${fromNode.name}'.`);
      }
    } catch (err: any) {
      setReachabilityError(err?.message || 'Failed to compute baseline route.');
    } finally {
      setIsPathComputing(false);
    }
  };

  const handleCongestBaseline = async () => {
    if (!fromNode || !toNode) return;
    stopRaceAnimation();
    setIsPathComputing(true);
    try {
      const res = await api.congestBaselineRoute(fromNode.node_id, toNode.node_id);
      const graph = await api.getCityGraph();
      setCityGraph(graph);
      triggerToast(res.message || 'Congested the baseline route (Demo).', 'info');

      // Re-evaluate paths
      const comp = await api.comparePaths(fromNode.node_id, toNode.node_id, 'astar');
      setComparisonResult(comp);
      setOptimisedRoute(comp.optimised);
      setBaselineRoute(comp.baseline);
    } catch (err: any) {
      triggerToast(`Failed to congest baseline: ${err?.message}`, 'error');
    } finally {
      setIsPathComputing(false);
    }
  };

  const handleRandomizeTraffic = async (seed?: number) => {
    stopRaceAnimation();
    setIsPathComputing(true);
    try {
      await api.randomizeTraffic(seed);
      const graph = await api.getCityGraph();
      setCityGraph(graph);
      triggerToast('Randomized traffic congestion and blocked 2-4 roads across city.', 'info');

      // If points are already selected, re-evaluate to show updated impact live
      if (fromNode && toNode) {
        const comp = await api.comparePaths(fromNode.node_id, toNode.node_id, 'astar');
        setComparisonResult(comp);
        if (optimisedRoute) setOptimisedRoute(comp.optimised);
        if (baselineRoute) setBaselineRoute(comp.baseline);
      }
    } catch (err: any) {
      triggerToast(`Failed to randomize traffic: ${err?.message}`, 'error');
    } finally {
      setIsPathComputing(false);
    }
  };

  // Operator Verification Action
  const handleVerify = async () => {
    if (!orchestration.active_incident) return;
    setIsVerifying(true);
    try {
      const updated = await api.verifyIncident(orchestration.active_incident.incident_id);
      setOrchestration((prev) => ({
        ...prev,
        active_incident: updated,
      }));
    } catch (err) {
      console.error('Verification failed:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  // Dispatch Action
  const handleDispatch = async () => {
    if (!orchestration.active_incident) return;
    setIsDispatching(true);
    try {
      await api.dispatchIncident(orchestration.active_incident.incident_id);
      const [state, units] = await Promise.all([
        api.getOrchestrationState(),
        api.getEmergencyUnits(),
      ]);
      setOrchestration(state);
      setEmergencyUnits(units);
    } catch (err) {
      console.error('Dispatch failed:', err);
    } finally {
      setIsDispatching(false);
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

  const dispatchedCount = emergencyUnits.filter(
    (u) => u.status !== 'available' && u.status !== 'stationed'
  ).length;

  return (
    <div className="flex flex-col h-screen w-screen bg-[#090d16] text-slate-100 overflow-hidden font-sans">
      {/* Top Bar Header */}
      <Header
        simulationTime={simulationTime}
        isRunning={isRunning}
        onRunScenario={handleRunScenario}
        onReset={handleReset}
        activeIncidentsCount={orchestration.active_incident ? 1 : 0}
        dispatchedUnitsCount={dispatchedCount}
        activeCorridorsCount={corridorNodes.length > 0 ? 1 : 0}
        backendStatus={backendStatus}
        mode={dashboardMode}
        onModeChange={handleModeChange}
      />

      {/* Main Command Center Grid */}
      <main className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden">
        {dashboardMode === 'find_path' ? (
          <>
            {/* FIND PATH MODE: 3 COLUMNS (Left: Controls, Center: Map, Right: Comparison) */}
            {/* Left Column: Controls (3 Cols) */}
            <div className="col-span-3 h-full rounded-lg overflow-hidden border border-slate-800 shadow-2xl">
              <FindPathControls
                fromNode={fromNode}
                toNode={toNode}
                selectionStep={selectionStep}
                onSetSelectionStep={setSelectionStep}
                onClearPoints={handleClearPoints}
                onSwapPoints={handleSwapPoints}
                onOptimisePath={handleOptimisePath}
                onBaselinePath={handleBaselinePath}
                onRandomizeTraffic={handleRandomizeTraffic}
                onCongestBaseline={handleCongestBaseline}
                isComputing={isPathComputing}
                reachabilityError={reachabilityError}
              />
            </div>

            {/* Center Column: Map (6 Cols) */}
            <div className="col-span-6 h-full rounded-lg overflow-hidden border border-slate-800 shadow-2xl relative">
              <CityMap
                cityGraph={cityGraph}
                activeIncident={null}
                emergencyUnits={[]}
                activeRoutes={[]}
                emergencyRoute={null}
                diversionRoute={null}
                activeCorridorNodes={[]}
                isFindPathMode={true}
                fromNode={fromNode}
                toNode={toNode}
                onMapNodeClick={handleMapNodeClick}
                findPathOptimised={optimisedRoute}
                findPathBaseline={baselineRoute}
                animProgressOpt={animProgressOpt}
                animProgressBase={animProgressBase}
                animPosOpt={animPosOpt}
                animPosBase={animPosBase}
                baseBlockedPause={baseBlockedPause}
              />
            </div>

            {/* Right Column: Comparison (3 Cols) */}
            <div className="col-span-3 h-full rounded-lg overflow-hidden border border-slate-800 shadow-2xl">
              <PathComparisonPanel
                optimisedRoute={optimisedRoute}
                baselineRoute={baselineRoute}
                comparison={comparisonResult}
                isComputing={isPathComputing}
                isRaceAnimating={isRaceAnimating}
                isRacePaused={isRacePaused}
                onStartRace={handleStartRace}
                onPauseRace={handlePauseRace}
                onResumeRace={handleResumeRace}
                onResetRace={handleResetRace}
                raceSpeed={raceSpeed}
                onRaceSpeedChange={handleSpeedChange}
                optArrived={optArrived}
                baseArrived={baseArrived}
                optElapsedTimeSec={optElapsedTimeSec}
                baseElapsedTimeSec={baseElapsedTimeSec}
              />
            </div>
          </>
        ) : (
          <>
            {/* SCENARIO MODE: Vision & Incident Panels, Map, Fleet & Agent Feed */}
            {/* Left Sidebar: Vision & Incident Triage (3 Cols) */}
            <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pr-0.5">
              <CCTVPanel
                cameraId={orchestration.active_incident?.source || 'cctv_camera_01'}
                hasCandidateAlert={!!orchestration.active_incident}
              />
              <IncidentPanel
                incident={orchestration.active_incident}
                onVerify={handleVerify}
                onDispatch={handleDispatch}
                isVerifying={isVerifying}
                isDispatching={isDispatching}
              />
            </div>

            {/* Center: Leaflet Interactive Command Center Map (6 Cols) */}
            <div className="col-span-6 rounded-lg overflow-hidden border border-slate-800 shadow-2xl relative">
              <CityMap
                cityGraph={cityGraph}
                activeIncident={orchestration.active_incident}
                emergencyUnits={emergencyUnits}
                activeRoutes={orchestration.active_routes || []}
                emergencyRoute={primaryEmergencyRoute}
                diversionRoute={diversionRoute}
                activeCorridorNodes={corridorNodes}
                isFindPathMode={false}
              />
            </div>

            {/* Right Sidebar: Fleet Ops & Multi-Agent Intelligence (3 Cols) */}
            <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pl-0.5">
              <ResourceList units={emergencyUnits} />
              <AgentLogFeed logs={orchestration.agent_logs || []} />
            </div>
          </>
        )}
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
