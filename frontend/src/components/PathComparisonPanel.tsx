<<<<<<< HEAD
import React, { useState } from 'react';
import {
  Zap,
  Clock,
  TrendingDown,
  Navigation,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  BarChart2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { FindPathResult, PathComparison } from '../types';

interface PathComparisonPanelProps {
  optimisedResult: FindPathResult | null;
  baselineResult: FindPathResult | null;
  comparison: PathComparison | null;
  fromNode: string | null;
  toNode: string | null;
}

export const PathComparisonPanel: React.FC<PathComparisonPanelProps> = ({
  optimisedResult,
  baselineResult,
  comparison,
  fromNode,
  toNode,
}) => {
  const [showSegmentDetails, setShowSegmentDetails] = useState<boolean>(false);

  const hasAnyResult = Boolean(optimisedResult || baselineResult);
  const hasBothResults = Boolean(optimisedResult && baselineResult);

  if (!hasAnyResult) {
    return (
      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-5 flex flex-col items-center justify-center text-center h-full min-h-[480px] shadow-xl text-slate-100 font-sans">
        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-3">
          <BarChart2 className="w-6 h-6 animate-pulse" />
        </div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
          Route Performance Comparison
        </h3>
        <p className="text-[11px] text-slate-400 mt-1 max-w-[240px] leading-relaxed">
          {fromNode && toNode
            ? `Endpoints selected (${fromNode} → ${toNode}). Click "Optimise Path" or "Without Optimisation" to compute route analytics.`
            : 'Select origin (FROM) and destination (TO) intersections to compare congestion-aware A* routing against the static distance baseline.'}
        </p>

        <div className="mt-5 w-full max-w-[260px] p-3 rounded-lg bg-slate-900/80 border border-slate-800/80 text-left text-[11px] space-y-2">
          <div className="text-[10px] font-bold uppercase text-slate-400 border-b border-slate-800 pb-1">
            Comparison Metrics
          </div>
          <div className="text-slate-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span>Travel time with live congestion &amp; closures</span>
          </div>
          <div className="text-slate-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            <span>Static shortest-distance path under real conditions</span>
          </div>
          <div className="text-slate-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-400"></span>
            <span>Detour penalties (+5 min) for hitting blocked roads</span>
          </div>
          <div className="text-slate-400 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
            <span>Nodes explored &amp; CPU compute latency (ms)</span>
          </div>
        </div>
=======
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
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
      </div>
    );
  }

<<<<<<< HEAD
  // Format summary text
  const summaryLine =
    comparison?.summary ||
    (optimisedResult
      ? `Optimised ${optimisedResult.algorithm.toUpperCase()} path: ${optimisedResult.total_distance_km} km in ${optimisedResult.estimated_travel_time_minutes} min.`
      : baselineResult
      ? `Baseline path: ${baselineResult.total_distance_km} km in ${baselineResult.estimated_travel_time_minutes} min.`
      : '');

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-3 shadow-xl text-slate-100 font-sans h-full overflow-y-auto">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <BarChart2 className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Route Comparison Analytics
          </h2>
        </div>
        <span className="text-[10px] font-mono text-slate-400">
          {fromNode} → {toNode}
        </span>
      </div>

      {/* Prominent Summary Banner */}
      <div
        className={`p-2.5 rounded-lg border text-xs font-sans leading-relaxed shadow-lg ${
          comparison && comparison.time_saved_seconds > 0
            ? 'bg-gradient-to-r from-cyan-950/90 to-indigo-950/80 border-cyan-500/60 text-cyan-100'
            : baselineResult?.has_blocked_segments
            ? 'bg-rose-950/90 border-rose-600/70 text-rose-100'
            : 'bg-slate-900 border-slate-700 text-slate-200'
        }`}
      >
        <div className="flex items-start space-x-2">
          {comparison && comparison.time_saved_seconds > 0 ? (
            <Zap className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5 fill-current" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          )}
          <div className="font-semibold text-xs">{summaryLine}</div>
        </div>
      </div>

      {/* Side-by-Side Comparison Grid */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        {/* Column 1: Optimised Path */}
        <div className="p-2.5 rounded-lg bg-slate-900/90 border border-cyan-800/60 flex flex-col space-y-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1">
            <span className="text-[10px] font-bold uppercase text-cyan-400 flex items-center space-x-1">
              <Zap className="w-3 h-3 fill-current" />
              <span>Optimised</span>
            </span>
            <span className="text-[9px] font-mono uppercase bg-cyan-950 text-cyan-300 px-1.5 py-0.2 rounded border border-cyan-800/50">
              {optimisedResult?.algorithm || 'A*'}
            </span>
          </div>

          {optimisedResult ? (
            <>
              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Travel Time</span>
                <div className="text-sm font-bold text-cyan-300 font-mono">
                  {optimisedResult.estimated_travel_time_minutes} min{' '}
                  <span className="text-[10px] font-normal text-slate-400">
                    ({optimisedResult.estimated_travel_time_seconds}s)
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Distance</span>
                <div className="font-semibold text-slate-200 font-mono">
                  {optimisedResult.total_distance_km} km{' '}
                  <span className="text-[10px] text-slate-500">
                    ({optimisedResult.total_distance_meters}m)
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Congestion</span>
                <div className="font-semibold text-emerald-400">
                  {optimisedResult.congested_segments_count === 0
                    ? '0 congested segments'
                    : `${optimisedResult.congested_segments_count} congested segments`}
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Blocked Roads</span>
                <div className="font-semibold text-emerald-400">0 hit (All avoided)</div>
              </div>

              <div className="pt-1 border-t border-slate-800 text-[10px] text-slate-400 flex justify-between font-mono">
                <span>Explored: {optimisedResult.nodes_explored}</span>
                <span>{optimisedResult.compute_ms} ms</span>
              </div>
            </>
          ) : (
            <div className="py-6 text-center text-slate-500 text-[11px] italic">
              Click &quot;Optimise Path&quot; to calculate
            </div>
          )}
        </div>

        {/* Column 2: Baseline (Without Optimisation) */}
        <div className="p-2.5 rounded-lg bg-slate-900/90 border border-amber-800/60 flex flex-col space-y-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1">
            <span className="text-[10px] font-bold uppercase text-amber-400 flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>Baseline</span>
            </span>
            <span className="text-[9px] font-mono uppercase bg-amber-950 text-amber-300 px-1.5 py-0.2 rounded border border-amber-800/50">
              Distance Only
            </span>
          </div>

          {baselineResult ? (
            <>
              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Travel Time</span>
                <div className="text-sm font-bold text-amber-300 font-mono">
                  {baselineResult.estimated_travel_time_minutes} min{' '}
                  <span className="text-[10px] font-normal text-slate-400">
                    ({baselineResult.estimated_travel_time_seconds}s)
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Distance</span>
                <div className="font-semibold text-slate-200 font-mono">
                  {baselineResult.total_distance_km} km{' '}
                  <span className="text-[10px] text-slate-500">
                    ({baselineResult.total_distance_meters}m)
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Congestion</span>
                <div
                  className={`font-semibold ${
                    baselineResult.congested_segments_count > 0 ? 'text-amber-400' : 'text-slate-300'
                  }`}
                >
                  {baselineResult.congested_segments_count} congested segments
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block uppercase">Blocked Roads</span>
                <div
                  className={`font-semibold ${
                    baselineResult.blocked_roads_hit > 0 ? 'text-rose-400' : 'text-emerald-400'
                  }`}
                >
                  {baselineResult.blocked_roads_hit > 0
                    ? `⚠️ ${baselineResult.blocked_roads_hit} hit (+${Math.round(
                        baselineResult.detour_penalty_seconds / 60
                      )}m penalty)`
                    : '0 hit'}
                </div>
              </div>

              <div className="pt-1 border-t border-slate-800 text-[10px] text-slate-400 flex justify-between font-mono">
                <span>Explored: {baselineResult.nodes_explored}</span>
                <span>{baselineResult.compute_ms} ms</span>
              </div>
            </>
          ) : (
            <div className="py-6 text-center text-slate-500 text-[11px] italic">
              Click &quot;Without Optimisation&quot; to evaluate
            </div>
          )}
        </div>
      </div>

      {/* Difference Highlights Card (when both exist) */}
      {hasBothResults && comparison && (
        <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between border-b border-slate-800 pb-1">
            <span>Optimization Gains</span>
            <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-950/70 p-2 rounded border border-slate-800/80">
              <span className="text-[9px] uppercase text-slate-400 block">Time Saved</span>
              <span
                className={`font-mono font-bold text-xs ${
                  comparison.time_saved_seconds > 0 ? 'text-emerald-400' : 'text-slate-300'
                }`}
              >
                {comparison.time_saved_minutes > 0
                  ? `-${comparison.time_saved_minutes} min (${comparison.time_saved_percent}%)`
                  : '0.0 min (0%)'}
              </span>
            </div>

            <div className="bg-slate-950/70 p-2 rounded border border-slate-800/80">
              <span className="text-[9px] uppercase text-slate-400 block">Distance Delta</span>
              <span className="font-mono font-bold text-xs text-slate-300">
                {comparison.distance_difference_meters > 0
                  ? `+${comparison.distance_difference_meters}m (+${comparison.distance_difference_km} km)`
                  : `${comparison.distance_difference_meters}m`}
              </span>
            </div>

            <div className="bg-slate-950/70 p-2 rounded border border-slate-800/80">
              <span className="text-[9px] uppercase text-slate-400 block">Congestion Avoided</span>
              <span className="font-mono font-bold text-xs text-cyan-400">
                {comparison.congested_segments_avoided} segment(s)
              </span>
            </div>

            <div className="bg-slate-950/70 p-2 rounded border border-slate-800/80">
              <span className="text-[9px] uppercase text-slate-400 block">Roadblocks Avoided</span>
              <span
                className={`font-mono font-bold text-xs ${
                  comparison.blocked_roads_avoided > 0 ? 'text-emerald-400' : 'text-slate-400'
                }`}
              >
                {comparison.blocked_roads_avoided} closure(s)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Segment Details Accordion */}
      {hasAnyResult && (
        <div className="pt-1">
          <button
            onClick={() => setShowSegmentDetails(!showSegmentDetails)}
            className="w-full py-1 px-2 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200 flex items-center justify-between transition"
          >
            <span>Segment-by-Segment Details</span>
            {showSegmentDetails ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {showSegmentDetails && (
            <div className="mt-2 space-y-2 max-h-56 overflow-y-auto pr-1 text-[10px] font-mono">
              {optimisedResult && (
                <div>
                  <div className="text-[9px] font-bold uppercase text-cyan-400 mb-1">
                    Optimised Route Segments ({optimisedResult.segments.length}):
                  </div>
                  {optimisedResult.segments.map((s, idx) => (
                    <div
                      key={`opt-seg-${idx}`}
                      className="bg-slate-950 p-1.5 rounded border border-slate-800/80 mb-1 flex justify-between"
                    >
                      <div>
                        <span className="text-slate-200 font-bold">{s.road_id}</span> ({s.name})
                        <div className="text-[9px] text-slate-500">
                          {s.length_meters}m • {s.speed_limit_kmph} km/h • {s.congestion_level} (x{s.congestion_multiplier})
                        </div>
                      </div>
                      <div className="text-right text-cyan-300 font-bold">{s.travel_time_seconds}s</div>
                    </div>
                  ))}
                </div>
              )}

              {baselineResult && (
                <div className="pt-1">
                  <div className="text-[9px] font-bold uppercase text-amber-400 mb-1">
                    Baseline Route Segments ({baselineResult.segments.length}):
                  </div>
                  {baselineResult.segments.map((s, idx) => (
                    <div
                      key={`base-seg-${idx}`}
                      className={`p-1.5 rounded border mb-1 flex justify-between ${
                        s.is_blocked
                          ? 'bg-rose-950/60 border-rose-700/80'
                          : 'bg-slate-950 border-slate-800/80'
                      }`}
                    >
                      <div>
                        <span className={`font-bold ${s.is_blocked ? 'text-rose-400' : 'text-slate-200'}`}>
                          {s.road_id} {s.is_blocked && '⛔ [BLOCKED]'}
                        </span>{' '}
                        ({s.name})
                        <div className="text-[9px] text-slate-500">
                          {s.length_meters}m • {s.speed_limit_kmph} km/h • {s.congestion_level} (x{s.congestion_multiplier})
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={s.is_blocked ? 'text-rose-400 font-bold' : 'text-amber-300 font-bold'}>
                          {s.travel_time_seconds}s
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
=======
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
>>>>>>> d90ee6792b56d2d6e2a40fe0f9f641b92714d2f7
    </div>
  );
};
