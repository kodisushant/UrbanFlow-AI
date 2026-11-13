import React, { useState } from 'react';
import {
  Compass,
  ArrowRightLeft,
  X,
  Zap,
  Clock,
  Shuffle,
  AlertTriangle,
  MapPin,
  CheckCircle2,
  Layers,
} from 'lucide-react';
import { IntersectionNode } from '../types';

interface FindPathControlsProps {
  nodes: IntersectionNode[];
  fromNode: string | null;
  toNode: string | null;
  selectionTarget: 'from' | 'to' | null;
  onSetSelectionTarget: (target: 'from' | 'to' | null) => void;
  onSelectFromNode: (nodeId: string) => void;
  onSelectToNode: (nodeId: string) => void;
  onSwapNodes: () => void;
  onClearNodes: () => void;
  algorithm: 'astar' | 'dijkstra';
  onAlgorithmChange: (algo: 'astar' | 'dijkstra') => void;
  onCalculateOptimised: () => void;
  onCalculateBaseline: () => void;
  onCompareBoth: () => void;
  isCalculatingOptimised: boolean;
  isCalculatingBaseline: boolean;
  unreachableError: string | null;
  onRandomizeTraffic: (seed?: number) => void;
  isRandomizingTraffic: boolean;
  trafficStatusInfo?: string | null;
}

export const FindPathControls: React.FC<FindPathControlsProps> = ({
  nodes,
  fromNode,
  toNode,
  selectionTarget,
  onSetSelectionTarget,
  onSelectFromNode,
  onSelectToNode,
  onSwapNodes,
  onClearNodes,
  algorithm,
  onAlgorithmChange,
  onCalculateOptimised,
  onCalculateBaseline,
  onCompareBoth,
  isCalculatingOptimised,
  isCalculatingBaseline,
  unreachableError,
  onRandomizeTraffic,
  isRandomizingTraffic,
  trafficStatusInfo,
}) => {
  const [seedInput, setSeedInput] = useState<string>('42');

  const fromNodeObj = nodes.find((n) => n.node_id === fromNode);
  const toNodeObj = nodes.find((n) => n.node_id === toNode);

  const canCompute = Boolean(fromNode && toNode && fromNode !== toNode);
  const isComputing = isCalculatingOptimised || isCalculatingBaseline;

  const handleRandomize = () => {
    const seed = seedInput.trim() !== '' ? parseInt(seedInput.trim(), 10) : undefined;
    onRandomizeTraffic(isNaN(seed as number) ? undefined : seed);
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-3.5 text-slate-100 font-sans shadow-xl">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Compass className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-100">
              Path Optimisation Controls
            </h2>
            <p className="text-[10px] text-slate-400">
              Select origin and destination to compare algorithms
            </p>
          </div>
        </div>
        <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-700/60">
          Find Path Mode
        </span>
      </div>

      {/* Origin & Destination Step Flow */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Route Endpoints (Map Snap)
          </span>
          <div className="flex items-center space-x-1.5">
            <button
              onClick={onSwapNodes}
              disabled={!fromNode || !toNode}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-cyan-300 border border-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Swap FROM and TO"
            >
              <ArrowRightLeft className="w-3 h-3" />
            </button>
            <button
              onClick={onClearNodes}
              disabled={!fromNode && !toNode}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-rose-300 border border-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Clear selection"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* FROM Node Card */}
        <div
          onClick={() => onSetSelectionTarget(selectionTarget === 'from' ? null : 'from')}
          className={`cursor-pointer p-2.5 rounded-lg border transition flex items-center justify-between ${
            selectionTarget === 'from'
              ? 'bg-emerald-950/60 border-emerald-500 ring-1 ring-emerald-500'
              : fromNode
              ? 'bg-slate-900 border-emerald-900/60'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <div className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-emerald-400 text-xs font-black">
              A
            </div>
            <div>
              <div className="text-[10px] uppercase font-bold text-emerald-400 flex items-center space-x-1">
                <span>Origin (FROM)</span>
                {selectionTarget === 'from' && (
                  <span className="animate-pulse text-[9px] text-emerald-300">
                    — Click map to select
                  </span>
                )}
              </div>
              <div className="text-xs font-semibold text-slate-200">
                {fromNode ? `${fromNodeObj?.name || fromNode} (${fromNode})` : 'Click to select origin'}
              </div>
            </div>
          </div>
          <MapPin className={`w-4 h-4 ${fromNode ? 'text-emerald-400' : 'text-slate-500'}`} />
        </div>

        {/* Quick select dropdown for FROM */}
        <select
          value={fromNode || ''}
          onChange={(e) => onSelectFromNode(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300 rounded px-2 py-1 focus:ring-1 focus:ring-emerald-500"
        >
          <option value="">-- Or choose Origin from list --</option>
          {nodes.map((n) => (
            <option key={`from-${n.node_id}`} value={n.node_id}>
              {n.node_id} - {n.name}
            </option>
          ))}
        </select>

        {/* TO Node Card */}
        <div
          onClick={() => onSetSelectionTarget(selectionTarget === 'to' ? null : 'to')}
          className={`cursor-pointer p-2.5 rounded-lg border transition flex items-center justify-between ${
            selectionTarget === 'to'
              ? 'bg-rose-950/60 border-rose-500 ring-1 ring-rose-500'
              : toNode
              ? 'bg-slate-900 border-rose-900/60'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <div className="w-6 h-6 rounded-full bg-rose-500/20 border border-rose-500 flex items-center justify-center text-rose-400 text-xs font-black">
              B
            </div>
            <div>
              <div className="text-[10px] uppercase font-bold text-rose-400 flex items-center space-x-1">
                <span>Destination (TO)</span>
                {selectionTarget === 'to' && (
                  <span className="animate-pulse text-[9px] text-rose-300">
                    — Click map to select
                  </span>
                )}
              </div>
              <div className="text-xs font-semibold text-slate-200">
                {toNode ? `${toNodeObj?.name || toNode} (${toNode})` : 'Click to select destination'}
              </div>
            </div>
          </div>
          <MapPin className={`w-4 h-4 ${toNode ? 'text-rose-400' : 'text-slate-500'}`} />
        </div>

        {/* Quick select dropdown for TO */}
        <select
          value={toNode || ''}
          onChange={(e) => onSelectToNode(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300 rounded px-2 py-1 focus:ring-1 focus:ring-rose-500"
        >
          <option value="">-- Or choose Destination from list --</option>
          {nodes.map((n) => (
            <option key={`to-${n.node_id}`} value={n.node_id}>
              {n.node_id} - {n.name}
            </option>
          ))}
        </select>
      </div>

      {/* Algorithm Mode Toggle */}
      <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
          Optimization Algorithm
        </span>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={() => onAlgorithmChange('astar')}
            className={`py-1.5 px-2 rounded text-[11px] font-bold uppercase tracking-wider transition ${
              algorithm === 'astar'
                ? 'bg-cyan-600 text-white shadow-md border border-cyan-400/50'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
            }`}
          >
            A* (Heuristic)
          </button>
          <button
            onClick={() => onAlgorithmChange('dijkstra')}
            className={`py-1.5 px-2 rounded text-[11px] font-bold uppercase tracking-wider transition ${
              algorithm === 'dijkstra'
                ? 'bg-cyan-600 text-white shadow-md border border-cyan-400/50'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
            }`}
          >
            Dijkstra
          </button>
        </div>
        <div className="text-[9px] text-slate-500 italic mt-0.5">
          {algorithm === 'astar'
            ? 'Admissible Haversine heuristic (Euclidean / max speed limit).'
            : 'Zero heuristic uniform cost search.'}
        </div>
      </div>

      {/* Unreachable Warning */}
      {unreachableError && (
        <div className="p-2.5 rounded-lg bg-rose-950/80 border border-rose-700/80 text-rose-200 text-xs flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-tight">
            <strong>Unreachable:</strong> {unreachableError}
          </div>
        </div>
      )}

      {/* Calculate Buttons */}
      <div className="space-y-2 pt-1">
        <div className="grid grid-cols-2 gap-2">
          {/* Optimise Path Button */}
          <button
            onClick={onCalculateOptimised}
            disabled={!canCompute || isComputing}
            className="py-2 px-2.5 rounded-lg font-bold text-xs uppercase tracking-wider bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-950 border border-cyan-400/40 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center space-x-1.5 transition"
            title="Calculate route with live congestion multipliers & road closures"
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>{isCalculatingOptimised ? 'Calculating...' : 'Optimise Path'}</span>
          </button>

          {/* Without Optimisation Button */}
          <button
            onClick={onCalculateBaseline}
            disabled={!canCompute || isComputing}
            className="py-2 px-2.5 rounded-lg font-bold text-xs uppercase tracking-wider bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-600/60 dashed disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center space-x-1.5 transition"
            title="Calculate shortest distance route without live traffic data, then evaluate real delays"
          >
            <Clock className="w-3.5 h-3.5" />
            <span>{isCalculatingBaseline ? 'Evaluating...' : 'Without Optim.'}</span>
          </button>
        </div>

        {/* Compare Both Quick Button */}
        <button
          onClick={onCompareBoth}
          disabled={!canCompute || isComputing}
          className="w-full py-2 px-3 rounded-lg font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-400/50 shadow disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center space-x-1.5 transition"
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Compare Both Side by Side</span>
        </button>

        {!canCompute && (
          <div className="text-[10px] text-slate-500 text-center italic">
            Select both origin (FROM) and destination (TO) on map to enable routing.
          </div>
        )}
      </div>

      {/* Randomize Traffic & Blocks Section */}
      <div className="pt-2 border-t border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Grid Stress Testing
          </span>
          <span className="text-[9px] text-amber-400 font-mono font-semibold">2-4 Blocks</span>
        </div>

        <div className="flex space-x-2">
          <input
            type="number"
            value={seedInput}
            onChange={(e) => setSeedInput(e.target.value)}
            placeholder="Seed (e.g. 42)"
            className="w-24 bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded px-2 py-1.5 focus:ring-1 focus:ring-cyan-500 font-mono"
            title="Random seed for repeatable traffic conditions"
          />
          <button
            onClick={handleRandomize}
            disabled={isRandomizingTraffic}
            className="flex-1 py-1.5 px-3 rounded bg-amber-600/80 hover:bg-amber-500 text-white font-bold text-[11px] uppercase tracking-wider flex items-center justify-center space-x-1.5 transition shadow"
            title="Generate random road congestion & block 2-4 roads across Cyber City"
          >
            <Shuffle className={`w-3.5 h-3.5 ${isRandomizingTraffic ? 'animate-spin' : ''}`} />
            <span>{isRandomizingTraffic ? 'Setting Traffic...' : 'Randomize Traffic'}</span>
          </button>
        </div>

        {trafficStatusInfo && (
          <div className="text-[10px] text-emerald-400 flex items-center space-x-1 font-mono">
            <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
            <span>{trafficStatusInfo}</span>
          </div>
        )}
      </div>
    </div>
  );
};
