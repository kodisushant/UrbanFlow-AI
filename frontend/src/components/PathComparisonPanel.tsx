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
      </div>
    );
  }

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
    </div>
  );
};
