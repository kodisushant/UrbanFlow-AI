import React from 'react';
import {
  TrendingUp,
  Clock,
  Navigation,
  AlertTriangle,
  Cpu,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Zap,
  Play,
  Pause,
  RotateCcw,
} from 'lucide-react';
import { FindPathResult, ComparePathsResult } from '../types';

interface PathComparisonPanelProps {
  optimisedRoute: FindPathResult | null;
  baselineRoute: FindPathResult | null;
  comparison: ComparePathsResult | null;
  isComputing: boolean;
  // Animation props
  isRaceAnimating?: boolean;
  isRacePaused?: boolean;
  onStartRace?: () => void;
  onPauseRace?: () => void;
  onResumeRace?: () => void;
  onResetRace?: () => void;
  raceSpeed?: number;
  onRaceSpeedChange?: (speed: number) => void;
  optArrived?: boolean;
  baseArrived?: boolean;
  optElapsedTimeSec?: number;
  baseElapsedTimeSec?: number;
}

export const PathComparisonPanel: React.FC<PathComparisonPanelProps> = ({
  optimisedRoute,
  baselineRoute,
  comparison,
  isComputing,
  isRaceAnimating = false,
  isRacePaused = false,
  onStartRace,
  onPauseRace,
  onResumeRace,
  onResetRace,
  raceSpeed = 1,
  onRaceSpeedChange,
  optArrived = false,
  baseArrived = false,
  optElapsedTimeSec = 0,
  baseElapsedTimeSec = 0,
}) => {
  // Empty State before any computation
  if (!optimisedRoute && !baselineRoute) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-slate-900 border-l border-slate-800 p-6 text-center text-slate-400">
        <div className="w-14 h-14 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-cyan-400 mb-4 shadow-inner">
          <Navigation className="w-7 h-7" />
        </div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200 mb-1">
          No Route Evaluated
        </h3>
        <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
          Select origin and destination nodes on the map and click <strong>"Optimise Path"</strong> or <strong>"Without Optimisation"</strong> to inspect side-by-side performance.
        </p>
      </div>
    );
  }

  const optTimeMin = optimisedRoute?.estimated_travel_time_minutes ?? 0;
  const baseTimeMin = baselineRoute?.estimated_travel_time_minutes ?? 0;
  const optDistKm = optimisedRoute?.total_distance_km ?? 0;
  const baseDistKm = baselineRoute?.total_distance_km ?? 0;

  return (
    <div className="h-full flex flex-col bg-slate-900 border-l border-slate-800 p-4 overflow-y-auto space-y-4">
      {/* Header */}
      <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2 text-cyan-400 font-bold text-sm tracking-wider uppercase">
            <TrendingUp className="w-4 h-4" />
            <span>Path Comparison</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Defensible algorithmic evaluation under live city conditions
          </p>
        </div>
        {isComputing && (
          <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono animate-pulse">
            Computing...
          </span>
        )}
      </div>

      {/* Summary Highlight Banner */}
      {comparison?.summary && (
        <div className={`p-3 rounded-lg border text-xs leading-relaxed ${
          comparison.routes_match
            ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
            : comparison.time_saved_percent > 0
            ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-200'
            : 'bg-slate-800/80 border-slate-700 text-slate-200'
        }`}>
          <div className="font-bold flex items-center space-x-1.5 mb-1 text-[11px] uppercase tracking-wider">
            {comparison.routes_match ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : (
              <Zap className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            )}
            <span>Outcome Summary</span>
          </div>
          <span>{comparison.summary}</span>
        </div>
      )}

      {/* Race Simulation Controls (Phase 3) */}
      {(optimisedRoute || baselineRoute) && (
        <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
              <span>🏎️</span>
              <span>Route Simulation Race</span>
            </span>
            {/* Speed Multiplier selector (1x, 2x, 4x) */}
            <div className="flex items-center space-x-1 bg-slate-900 border border-slate-700/60 rounded p-0.5">
              {[1, 2, 4].map((spd) => (
                <button
                  key={spd}
                  onClick={() => onRaceSpeedChange && onRaceSpeedChange(spd)}
                  className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${
                    raceSpeed === spd ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {!isRaceAnimating ? (
              <button
                onClick={onStartRace}
                className="flex-1 py-1.5 px-3 rounded text-xs font-bold uppercase tracking-wider bg-cyan-600 hover:bg-cyan-500 text-white flex items-center justify-center space-x-1.5 shadow-md shadow-cyan-950"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Race Routes</span>
              </button>
            ) : isRacePaused ? (
              <button
                onClick={onResumeRace}
                className="flex-1 py-1.5 px-3 rounded text-xs font-bold uppercase tracking-wider bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center space-x-1.5 shadow-md"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Resume</span>
              </button>
            ) : (
              <button
                onClick={onPauseRace}
                className="flex-1 py-1.5 px-3 rounded text-xs font-bold uppercase tracking-wider bg-amber-600 hover:bg-amber-500 text-white flex items-center justify-center space-x-1.5 shadow-md"
              >
                <Pause className="w-3.5 h-3.5" />
                <span>Pause</span>
              </button>
            )}

            <button
              onClick={onResetRace}
              className="py-1.5 px-2.5 rounded text-xs font-bold uppercase bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center space-x-1"
              title="Reset Race"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Replay</span>
            </button>
          </div>

          {/* Live Progress / Arrived status per vehicle */}
          <div className="space-y-1.5 pt-1 text-xs font-mono">
            {optimisedRoute && (
              <div className="flex items-center justify-between bg-slate-900/60 px-2 py-1 rounded border border-cyan-900/40">
                <span className="text-cyan-400 font-semibold flex items-center space-x-1">
                  <span>⚡ Optimised:</span>
                </span>
                <span className={optArrived ? 'text-emerald-400 font-bold' : 'text-slate-200'}>
                  {optArrived ? `Arrived! (${(optElapsedTimeSec / 60).toFixed(1)}m)` : `${(optElapsedTimeSec / 60).toFixed(1)} min elapsed`}
                </span>
              </div>
            )}
            {baselineRoute && (
              <div className="flex items-center justify-between bg-slate-900/60 px-2 py-1 rounded border border-amber-900/40">
                <span className="text-amber-400 font-semibold flex items-center space-x-1">
                  <span>🧭 Baseline:</span>
                </span>
                <span className={baseArrived ? 'text-emerald-400 font-bold' : 'text-slate-200'}>
                  {baseArrived ? `Arrived! (${(baseElapsedTimeSec / 60).toFixed(1)}m)` : `${(baseElapsedTimeSec / 60).toFixed(1)} min elapsed`}
                </span>
              </div>
            )}
            {optArrived && baseArrived && (
              <div className="text-[11px] font-sans font-bold text-center text-emerald-400 pt-0.5">
                🏁 Race Complete! A* Optimised arrived {Math.max(0, +((baseElapsedTimeSec - optElapsedTimeSec) / 60).toFixed(1))} min earlier.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Side-by-Side Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* OPTIMISED CARD */}
        <div className={`p-3 rounded-lg border ${
          optimisedRoute
            ? 'border-cyan-500/60 bg-cyan-950/20'
            : 'border-slate-800 bg-slate-950/40 opacity-50'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
              Optimised (A*)
            </span>
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]"></div>
          </div>
          {optimisedRoute ? (
            <div className="space-y-1.5 text-xs">
              <div>
                <div className="text-[10px] text-slate-400">Travel Time</div>
                <div className="text-base font-black text-cyan-300 font-mono">
                  {optimisedRoute.estimated_travel_time_minutes} min
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Distance</div>
                <div className="text-xs font-bold text-slate-200 font-mono">
                  {optimisedRoute.total_distance_km} km
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Congested Segments</div>
                <div className="text-xs font-semibold text-amber-300">
                  {optimisedRoute.congested_segments_count}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Blocked Roads Hit</div>
                <div className="text-xs font-semibold text-emerald-400">
                  {optimisedRoute.blocked_roads_count} (Avoided)
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-slate-500 italic py-4 text-center">
              Pending run
            </div>
          )}
        </div>

        {/* BASELINE CARD */}
        <div className={`p-3 rounded-lg border ${
          baselineRoute
            ? 'border-amber-500/60 bg-amber-950/20'
            : 'border-slate-800 bg-slate-950/40 opacity-50'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
              Baseline
            </span>
            <div className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-dashed border-amber-300"></div>
          </div>
          {baselineRoute ? (
            <div className="space-y-1.5 text-xs">
              <div>
                <div className="text-[10px] text-slate-400">Travel Time</div>
                <div className="text-base font-black text-amber-300 font-mono">
                  {baselineRoute.estimated_travel_time_minutes} min
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Distance</div>
                <div className="text-xs font-bold text-slate-200 font-mono">
                  {baselineRoute.total_distance_km} km
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Congested Segments</div>
                <div className="text-xs font-semibold text-amber-300">
                  {baselineRoute.congested_segments_count}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Blocked Roads Hit</div>
                <div className={`text-xs font-bold ${
                  baselineRoute.blocked_roads_count > 0 ? 'text-rose-400' : 'text-slate-300'
                }`}>
                  {baselineRoute.blocked_roads_count} {baselineRoute.blocked_roads_count > 0 && '(+Detour Penalty)'}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-slate-500 italic py-4 text-center">
              Pending run
            </div>
          )}
        </div>
      </div>

      {/* Detailed Comparison Metrics Table */}
      {optimisedRoute && baselineRoute && (
        <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-2.5">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800/80 pb-1.5">
            Key Performance Delta
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Time Saved</span>
              <span className="font-bold text-emerald-400 font-mono">
                {comparison?.time_saved_minutes ?? Math.max(0, +(baseTimeMin - optTimeMin).toFixed(1))} min ({comparison?.time_saved_percent ?? 0}%)
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Distance Difference</span>
              <span className="font-bold text-slate-300 font-mono">
                {Math.abs(+(baseDistKm - optDistKm).toFixed(2))} km {baseDistKm > optDistKm ? '(baseline is longer)' : '(optimised detour)'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Blocked Segments Penalised</span>
              <span className={`font-bold font-mono ${
                baselineRoute.has_blocked_segments ? 'text-rose-400' : 'text-emerald-400'
              }`}>
                {baselineRoute.has_blocked_segments ? `Yes (${baselineRoute.detour_penalty_applied_seconds}s penalty)` : 'None'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Algorithm Computational Stats */}
      <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3 space-y-2">
        <div className="flex items-center space-x-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span>A* Algorithmic Stats</span>
        </div>

        <div className="space-y-1.5 text-[11px] text-slate-300 font-mono">
          {optimisedRoute && (
            <div className="flex items-center justify-between border-b border-slate-800/50 pb-1">
              <span className="text-slate-400">Nodes Explored:</span>
              <span className="font-bold text-cyan-400">{optimisedRoute.nodes_explored} nodes</span>
            </div>
          )}
          {optimisedRoute && (
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Compute Time:</span>
              <span className="font-bold text-cyan-400">{optimisedRoute.compute_ms} ms</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
