import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { CityMap } from './components/CityMap';
import { CCTVPanel } from './components/CCTVPanel';
import { IncidentPanel } from './components/IncidentPanel';
import { ResourceList } from './components/ResourceList';
import { AgentLogFeed } from './components/AgentLogFeed';
import { api } from './services/api';
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
} from './services/mockData';

export const App: React.FC = () => {
  const [cityGraph, setCityGraph] = useState<CityGraph>(mockCityGraph);
  const [orchestration, setOrchestration] = useState<OrchestrationState>(mockOrchestrationState);
  const [emergencyUnits, setEmergencyUnits] = useState<EmergencyUnit[]>(mockEmergencyUnits);
  const [simulationTime, setSimulationTime] = useState<number>(14.2);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);

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

  // One-click Hackathon Scenario Trigger
  const handleRunScenario = async () => {
    setIsRunning(true);
    try {
      const state = await api.runScenario('Cyber City Emergency Response');
      setOrchestration(state);
      const units = await api.getEmergencyUnits();
      setEmergencyUnits(units);
    } catch (err) {
      console.error('Failed to trigger scenario:', err);
    } finally {
      setIsRunning(false);
    }
  };

  // Instant Reset Action
  const handleReset = async () => {
    setIsRunning(false);
    setSimulationTime(0.0);
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
      const updated = await api.dispatchIncident(orchestration.active_incident.incident_id);
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

  const dispatchedCount = emergencyUnits.filter((u) => u.status === 'dispatched').length;

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
      />

      {/* Main Command Center Grid */}
      <main className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden">
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
            emergencyRoute={primaryEmergencyRoute}
            diversionRoute={diversionRoute}
            activeCorridorNodes={corridorNodes}
          />
        </div>

        {/* Right Sidebar: Fleet Ops & Multi-Agent Intelligence (3 Cols) */}
        <div className="col-span-3 flex flex-col space-y-3 overflow-y-auto pl-0.5">
          <ResourceList units={emergencyUnits} />
          <AgentLogFeed logs={orchestration.agent_logs || []} />
        </div>
      </main>
    </div>
  );
};
