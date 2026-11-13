import React from 'react';
import {
  Activity,
  Play,
  Pause,
  RotateCcw,
  RefreshCw,
  ShieldAlert,
  Truck,
  Zap,
  Wifi,
  WifiOff,
  Radio,
} from 'lucide-react';

interface HeaderProps {
  simulationTime: number;
  isRunning: boolean;
  onToggleTimer: () => void;
  onRunFullScenario: () => void;
  onRunStepScenario: () => void;
  onReset: () => void;
  onRefresh: () => void;
  activeIncidentsCount: number;
  dispatchedUnitsCount: number;
  activeCorridorsCount: number;
  isBackendOnline: boolean;
  isOperating: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  simulationTime,
  isRunning,
  onToggleTimer,
  onRunFullScenario,
  onRunStepScenario,
  onReset,
  onRefresh,
  activeIncidentsCount,
  dispatchedUnitsCount,
  activeCorridorsCount,
  isBackendOnline,
  isOperating,
}) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `T+${String(mins).padStart(2, '0')}:${String(secs).padStart(4, '0')}s`;
  };

  return (
    <header className="h-16 bg-[#0f172a] border-b border-slate-800 px-5 flex items-center justify-between z-20 shrink-0">
      {/* Title & Branding */}
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
          <Zap className="w-5 h-5 animate-pulse text-cyan-400" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold tracking-wider text-slate-100 uppercase">
              UrbanFlow AI
            </h1>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">
              Command Center
            </span>

            {/* Backend Connectivity Badge */}
            <div
              className={`flex items-center space-x-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                isBackendOnline
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/50'
                  : 'bg-rose-950/80 text-rose-400 border-rose-800/50'
              }`}
              title={isBackendOnline ? 'FastAPI Backend Connected' : 'Backend Unreachable'}
            >
              {isBackendOnline ? (
                <>
                  <Wifi className="w-3 h-3 text-emerald-400" />
                  <span>API Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-rose-400" />
                  <span>API Offline</span>
                </>
              )}
            </div>
          </div>
          <p className="text-xs text-slate-400">
            Multi-Agent Autonomous Traffic Intelligence & Emergency Corridor Dispatch
          </p>
        </div>
      </div>

      {/* KPI Badges */}
      <div className="hidden xl:flex items-center space-x-3">
        {/* Incident Badge */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <div className="text-left">
            <div className="text-[10px] text-slate-400 uppercase font-medium">Active Incidents</div>
            <div className="text-xs font-bold text-rose-400">{activeIncidentsCount} Detected</div>
          </div>
        </div>

        {/* Units Dispatched */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
          <Truck className="w-4 h-4 text-cyan-400" />
          <div className="text-left">
            <div className="text-[10px] text-slate-400 uppercase font-medium">Units Dispatched</div>
            <div className="text-xs font-bold text-cyan-400">{dispatchedUnitsCount} En Route</div>
          </div>
        </div>

        {/* Signal Preemption Corridors */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
          <Activity className="w-4 h-4 text-emerald-400" />
          <div className="text-left">
            <div className="text-[10px] text-slate-400 uppercase font-medium">Green Corridors</div>
            <div className="text-xs font-bold text-emerald-400">{activeCorridorsCount} Active</div>
          </div>
        </div>

        {/* Simulation Clock & Play/Pause */}
        <button
          onClick={onToggleTimer}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-950 border border-cyan-900/50 text-cyan-300 font-mono text-xs tracking-wider font-bold hover:bg-slate-900 transition"
          title={isRunning ? 'Pause Simulation Clock' : 'Resume Simulation Clock'}
        >
          {isRunning ? <Pause className="w-3 h-3 text-amber-400" /> : <Play className="w-3 h-3 text-emerald-400" />}
          <span>{formatTime(simulationTime)}</span>
        </button>
      </div>

      {/* Scenario Action Controls */}
      <div className="flex items-center space-x-2.5">
        {/* Step-by-Step Scenario */}
        <button
          onClick={onRunStepScenario}
          disabled={isOperating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-semibold text-xs tracking-wider uppercase bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-800/60 transition shadow"
          title="Detect incident and wait for human operator verification"
        >
          <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>Step Triage</span>
        </button>

        {/* Full Auto Demo Scenario */}
        <button
          onClick={onRunFullScenario}
          disabled={isOperating}
          className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-md font-semibold text-xs tracking-wider uppercase transition shadow ${
            isOperating
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-950 border border-cyan-400/40'
          }`}
          title="Run complete 8-step pipeline from detection to diversion"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{isOperating ? 'Processing...' : 'Run Auto Demo'}</span>
        </button>

        {/* Reset */}
        <button
          onClick={onReset}
          disabled={isOperating}
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md font-semibold text-xs tracking-wider uppercase bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          title="Reset Simulation to Baseline Standby"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          disabled={isOperating}
          className="p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 transition"
          title="Refresh Backend Data"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
