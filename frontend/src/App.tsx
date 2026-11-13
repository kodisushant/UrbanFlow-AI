import React, { useState, useEffect, useCallback } from 'react';
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
<<<<<<< HEAD
  AppMode,
  FindPathResult,
  PathComparison,
=======
  IntersectionNode,
  FindPathResult,
  ComparePathsResult,
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
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
  // App Mode: 'scenario' (Emergency response demo) or 'find_path' (Route optimization lab)
  const [appMode, setAppMode] = useState<AppMode>('scenario');

  const [cityGraph, setCityGraph] = useState<CityGraph>(mockCityGraph);
  const [orchestration, setOrchestration] = useState<OrchestrationState>(standbyOrchestrationState);
  const [emergencyUnits, setEmergencyUnits] = useState<EmergencyUnit[]>(mockEmergencyUnits);
  const [simulationTime, setSimulationTime] = useState<number>(0.0);
<<<<<<< HEAD
  const [isRunning, setIsRunning] = useState<boolean>(true);
=======
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
  const [backendStatus, setBackendStatus] = useState<BackendStatus>(getBackendStatus());

  // Operation loading states
  const [isOperating, setIsOperating] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
  const [isResolving, setIsResolving] = useState<boolean>(false);

  // Find Path Mode state
  const [fromNode, setFromNode] = useState<string | null>('INT-01');
  const [toNode, setToNode] = useState<string | null>('INT-10');
  const [selectionTarget, setSelectionTarget] = useState<'from' | 'to' | null>(null);
  const [findPathAlgorithm, setFindPathAlgorithm] = useState<'astar' | 'dijkstra'>('astar');
  const [optimisedResult, setOptimisedResult] = useState<FindPathResult | null>(null);
  const [baselineResult, setBaselineResult] = useState<FindPathResult | null>(null);
  const [comparison, setComparison] = useState<PathComparison | null>(null);
  const [unreachableError, setUnreachableError] = useState<string | null>(null);
  const [trafficStatusInfo, setTrafficStatusInfo] = useState<string | null>(null);
  const [isCalculatingOptimised, setIsCalculatingOptimised] = useState<boolean>(false);
  const [isCalculatingBaseline, setIsCalculatingBaseline] = useState<boolean>(false);
  const [isRandomizingTraffic, setIsRandomizingTraffic] = useState<boolean>(false);

  // Toast notifications for user feedback
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

<<<<<<< HEAD
  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ message, type });
  };
=======
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
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7

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

<<<<<<< HEAD
  // -------------------------------------------------------------------------
  // Scenario Mode Handlers
  // -------------------------------------------------------------------------

  const handleRunFullScenario = async () => {
    setIsOperating(true);
    try {
      showNotification('Running full automated 8-step emergency response scenario...', 'info');
=======
  // One-click Hackathon Scenario Trigger (Auto-verifies & Auto-dispatches)
  const handleRunScenario = async () => {
    setIsRunning(true);
    setSimulationTime(0.0);
    try {
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
      const state = await api.runScenario('Cyber City Emergency Response', true);
      setOrchestration(state);
      const units = await api.getEmergencyUnits();
      setEmergencyUnits(units);
<<<<<<< HEAD
      const graph = await api.getCityGraph();
=======
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
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
      setCityGraph(graph);
      showNotification('Full scenario executed: Units dispatched and Green Corridor active!', 'success');
    } catch (err: any) {
      showNotification(`Scenario trigger error: ${err.message}`, 'error');
    } finally {
      setIsOperating(false);
    }
  };

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

<<<<<<< HEAD
=======
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
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
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

  const handleDispatch = async () => {
    if (!orchestration.active_incident) return;
    setIsDispatching(true);
    try {
<<<<<<< HEAD
      const updated = await api.dispatchIncident(orchestration.active_incident.incident_id);
      showNotification(
        `Emergency units dispatched for ${updated.incident_id}. A* route & green corridors active!`,
        'success'
      );
      await refreshAll();
    } catch (err: any) {
      showNotification(`Dispatch blocked: ${err.message}`, 'error');
=======
      await api.dispatchIncident(orchestration.active_incident.incident_id);
      const [state, units] = await Promise.all([
        api.getOrchestrationState(),
        api.getEmergencyUnits(),
      ]);
      setOrchestration(state);
      setEmergencyUnits(units);
    } catch (err) {
      console.error('Dispatch failed:', err);
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
    } finally {
      setIsDispatching(false);
    }
  };

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

  const handleToggleRoadClosure = async (roadId: string, currentBlocked: boolean) => {
    try {
      await api.toggleRoadClosure(roadId, !currentBlocked);
      showNotification(`Road ${roadId} ${!currentBlocked ? 'closed' : 'reopened'}.`, 'info');
      await refreshAll();
      // If in find path mode, re-fetch routes to reflect road closure change
      if (appMode === 'find_path' && fromNode && toNode) {
        if (optimisedResult || baselineResult) {
          handleCompareBoth();
        }
      }
    } catch (err: any) {
      showNotification(`Failed to toggle closure: ${err.message}`, 'error');
    }
  };

  // -------------------------------------------------------------------------
  // Find Path Mode Handlers
  // -------------------------------------------------------------------------

  const handleSelectNode = (nodeId: string) => {
    if (selectionTarget === 'from') {
      setFromNode(nodeId);
      setSelectionTarget('to');
      setOptimisedResult(null);
      setBaselineResult(null);
      setComparison(null);
      setUnreachableError(null);
      showNotification(`Origin set to ${nodeId}. Now click destination node.`, 'info');
    } else if (selectionTarget === 'to') {
      setToNode(nodeId);
      setSelectionTarget(null);
      setOptimisedResult(null);
      setBaselineResult(null);
      setComparison(null);
      setUnreachableError(null);
      showNotification(`Destination set to ${nodeId}. Ready to calculate!`, 'info');
    } else {
      if (!fromNode) {
        setFromNode(nodeId);
        setSelectionTarget('to');
        showNotification(`Origin set to ${nodeId}. Now select destination.`, 'info');
      } else {
        setToNode(nodeId);
        setSelectionTarget(null);
        showNotification(`Destination set to ${nodeId}.`, 'info');
      }
      setOptimisedResult(null);
      setBaselineResult(null);
      setComparison(null);
      setUnreachableError(null);
    }
  };

  const handleSwapNodes = () => {
    const temp = fromNode;
    setFromNode(toNode);
    setToNode(temp);
    setOptimisedResult(null);
    setBaselineResult(null);
    setComparison(null);
    setUnreachableError(null);
  };

  const handleClearNodes = () => {
    setFromNode(null);
    setToNode(null);
    setSelectionTarget('from');
    setOptimisedResult(null);
    setBaselineResult(null);
    setComparison(null);
    setUnreachableError(null);
  };

  const handleCalculateOptimised = async () => {
    if (!fromNode || !toNode) return;
    setIsCalculatingOptimised(true);
    setUnreachableError(null);
    try {
      const res = await api.findPath(fromNode, toNode, 'optimised', findPathAlgorithm);
      if (!res.reachable) {
        setUnreachableError(res.summary);
        showNotification(res.summary, 'error');
        setOptimisedResult(null);
      } else {
        setOptimisedResult(res);
        showNotification(
          `Optimised route calculated: ${res.total_distance_km} km in ${res.estimated_travel_time_minutes} min`,
          'success'
        );
        // If baseline already exists for this pair, recompute comparison
        if (baselineResult && baselineResult.from_node === fromNode && baselineResult.to_node === toNode) {
          const comp = await api.comparePaths(fromNode, toNode, findPathAlgorithm);
          setComparison(comp.comparison || null);
        }
      }
    } catch (err: any) {
      showNotification(`Optimization error: ${err.message}`, 'error');
    } finally {
      setIsCalculatingOptimised(false);
    }
  };

  const handleCalculateBaseline = async () => {
    if (!fromNode || !toNode) return;
    setIsCalculatingBaseline(true);
    try {
      const res = await api.findPath(fromNode, toNode, 'baseline', findPathAlgorithm);
      setBaselineResult(res);
      showNotification(
        `Baseline route evaluated: ${res.total_distance_km} km in ${res.estimated_travel_time_minutes} min`,
        'info'
      );
      // If optimised already exists for this pair, recompute comparison
      if (optimisedResult && optimisedResult.from_node === fromNode && optimisedResult.to_node === toNode) {
        const comp = await api.comparePaths(fromNode, toNode, findPathAlgorithm);
        setComparison(comp.comparison || null);
      }
    } catch (err: any) {
      showNotification(`Baseline calculation error: ${err.message}`, 'error');
    } finally {
      setIsCalculatingBaseline(false);
    }
  };

  const handleCompareBoth = async () => {
    if (!fromNode || !toNode) return;
    setIsCalculatingOptimised(true);
    setIsCalculatingBaseline(true);
    setUnreachableError(null);
    try {
      const comp = await api.comparePaths(fromNode, toNode, findPathAlgorithm);
      if (!comp.reachable) {
        setUnreachableError(comp.error_message || 'Destination is unreachable due to road closures.');
        showNotification(comp.error_message || 'Destination is unreachable due to road closures.', 'error');
      } else {
        setOptimisedResult(comp.optimised || null);
        setBaselineResult(comp.baseline || null);
        setComparison(comp.comparison || null);
        showNotification(comp.comparison?.summary || 'Comparison complete!', 'success');
      }
    } catch (err: any) {
      showNotification(`Comparison error: ${err.message}`, 'error');
    } finally {
      setIsCalculatingOptimised(false);
      setIsCalculatingBaseline(false);
    }
  };

  const handleRandomizeTraffic = async (seed?: number) => {
    setIsRandomizingTraffic(true);
    try {
      const res = await api.randomizeTraffic(seed);
      setTrafficStatusInfo(
        `Seed ${res.seed ?? 'Random'}: ${res.blocked_roads.length} road(s) closed, ${res.congested_roads_count} congested segments`
      );
      showNotification(
        `Traffic randomized: ${res.blocked_roads.length} road closures applied.`,
        'info'
      );
      // Refresh map so edge colors and dashes immediately update
      const graph = await api.getCityGraph();
      setCityGraph(graph);

      // Recompute active routes if already shown
      if (fromNode && toNode && fromNode !== toNode) {
        if (optimisedResult && baselineResult) {
          const comp = await api.comparePaths(fromNode, toNode, findPathAlgorithm);
          setOptimisedResult(comp.optimised || null);
          setBaselineResult(comp.baseline || null);
          setComparison(comp.comparison || null);
        } else if (optimisedResult) {
          const opt = await api.findPath(fromNode, toNode, 'optimised', findPathAlgorithm);
          setOptimisedResult(opt);
        } else if (baselineResult) {
          const base = await api.findPath(fromNode, toNode, 'baseline', findPathAlgorithm);
          setBaselineResult(base);
        }
      }
    } catch (err: any) {
      showNotification(`Failed to randomize traffic: ${err.message}`, 'error');
    } finally {
      setIsRandomizingTraffic(false);
    }
  };

  // Reset (works in BOTH modes)
  const handleReset = async () => {
    setIsOperating(true);
    setSimulationTime(0.0);
    try {
      await api.resetSimulation();
      await refreshAll();
      // Clear find path state
      setOptimisedResult(null);
      setBaselineResult(null);
      setComparison(null);
      setUnreachableError(null);
      setTrafficStatusInfo(null);
      showNotification(
        'System reset to baseline standby. All corridors, units, and roadblocks restored.',
        'success'
      );
    } catch (err: any) {
      showNotification(`Reset failed: ${err.message}`, 'error');
    } finally {
      setIsOperating(false);
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
<<<<<<< HEAD
        isOperating={isOperating}
        mode={appMode}
        onModeChange={(newMode) => {
          setAppMode(newMode);
          showNotification(
            newMode === 'find_path'
              ? 'Switched to Find Path Mode: Route Optimization Lab.'
              : 'Switched to Run Scenario Mode: Emergency Response & Triage.',
            'info'
          );
        }}
=======
        mode={dashboardMode}
        onModeChange={handleModeChange}
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
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
<<<<<<< HEAD
        {appMode === 'scenario' ? (
          <>
            {/* Left Sidebar: Vision & Incident Triage (3 Cols) */}
            <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pr-0.5">
              <CCTVPanel
                cameraId={orchestration.active_incident?.source || 'cctv_camera_01'}
                hasCandidateAlert={
                  !!orchestration.active_incident &&
                  orchestration.active_incident.status !== 'resolved'
                }
                onAnalyzeFeed={(camId) =>
                  handleSimulateDetection(camId === 'cctv_camera_01' ? 'INT-03' : 'INT-01')
                }
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
                appMode="scenario"
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

=======
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

>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
            {/* Right Sidebar: Fleet Ops & Multi-Agent Intelligence (3 Cols) */}
            <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pl-0.5">
              <ResourceList units={emergencyUnits} />
              <AgentLogFeed logs={orchestration.agent_logs || []} />
            </div>
          </>
<<<<<<< HEAD
        ) : (
          <>
            {/* Left Column: Find Path Controls (3 Cols) */}
            <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pr-0.5">
              <FindPathControls
                nodes={cityGraph.nodes}
                fromNode={fromNode}
                toNode={toNode}
                selectionTarget={selectionTarget}
                onSetSelectionTarget={setSelectionTarget}
                onSelectFromNode={(nid) => {
                  setFromNode(nid);
                  setOptimisedResult(null);
                  setBaselineResult(null);
                  setComparison(null);
                  setUnreachableError(null);
                }}
                onSelectToNode={(nid) => {
                  setToNode(nid);
                  setOptimisedResult(null);
                  setBaselineResult(null);
                  setComparison(null);
                  setUnreachableError(null);
                }}
                onSwapNodes={handleSwapNodes}
                onClearNodes={handleClearNodes}
                algorithm={findPathAlgorithm}
                onAlgorithmChange={setFindPathAlgorithm}
                onCalculateOptimised={handleCalculateOptimised}
                onCalculateBaseline={handleCalculateBaseline}
                onCompareBoth={handleCompareBoth}
                isCalculatingOptimised={isCalculatingOptimised}
                isCalculatingBaseline={isCalculatingBaseline}
                unreachableError={unreachableError}
                onRandomizeTraffic={handleRandomizeTraffic}
                isRandomizingTraffic={isRandomizingTraffic}
                trafficStatusInfo={trafficStatusInfo}
              />
            </div>

            {/* Center Column: Interactive Map in Find Path Mode (6 Cols) */}
            <div className="col-span-6 rounded-lg overflow-hidden border border-slate-800 shadow-2xl relative min-h-[480px]">
              <CityMap
                appMode="find_path"
                cityGraph={cityGraph}
                activeIncident={null}
                emergencyUnits={emergencyUnits}
                emergencyRoute={null}
                diversionRoute={null}
                activeCorridorNodes={[]}
                fromNode={fromNode}
                toNode={toNode}
                selectionTarget={selectionTarget}
                onSelectNode={handleSelectNode}
                findPathOptimisedRoute={optimisedResult}
                findPathBaselineRoute={baselineResult}
                onToggleRoadClosure={handleToggleRoadClosure}
              />
            </div>

            {/* Right Column: Path Comparison & Performance Analytics (3 Cols) */}
            <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pl-0.5">
              <PathComparisonPanel
                optimisedResult={optimisedResult}
                baselineResult={baselineResult}
                comparison={comparison}
                fromNode={fromNode}
                toNode={toNode}
              />
            </div>
          </>
=======
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
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
