import React from 'react';
import {
  Activity,
  Play,
  RotateCcw,
  ShieldAlert,
  Flame,
  Truck,
  Zap,
} from 'lucide-react';

interface HeaderProps {
  simulationTime: number;
  isRunning: boolean;
  onRunScenario: () => void;
  onReset: () => void;
  activeIncidentsCount: number;
  dispatchedUnitsCount: number;
  activeCorridorsCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  simulationTime,
  isRunning,
  onRunScenario,
  onReset,
  activeIncidentsCount,
  dispatchedUnitsCount,
  activeCorridorsCount,
}) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `T+${String(mins).padStart(2, '0')}:${String(secs).padStart(4, '0')}s`;
  };

  return (
    <header className="h-16 bg-[#0f172a] border-b border-slate-800 px-6 flex items-center justify-between z-20 shrink-0">
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
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800/50">
              Simulation Mode
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Adaptive Multi-Agent Traffic Intelligence & Emergency Corridor Dispatch
          </p>
        </div>
      </div>

      {/* KPI Badges */}
      <div className="hidden lg:flex items-center space-x-4">
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

        {/* Simulation Clock */}
        <div className="px-3 py-1.5 rounded-md bg-slate-950 border border-cyan-900/50 text-cyan-300 font-mono text-sm tracking-widest font-bold">
          {formatTime(simulationTime)}
        </div>
      </div>

      {/* Scenario Action Controls */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onRunScenario}
          disabled={isRunning}
          className={`flex items-center space-x-2 px-4 py-2 rounded-md font-semibold text-xs tracking-wider uppercase transition-all duration-150 ${
            isRunning
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/40 border border-cyan-400/30'
          }`}
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{isRunning ? 'Running Demo...' : 'Run Scenario'}</span>
        </button>

        <button
          onClick={onReset}
          className="flex items-center space-x-2 px-3 py-2 rounded-md font-semibold text-xs tracking-wider uppercase bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          title="Reset Simulation to Baseline Standby"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
      </div>
    </header>
  );
};
