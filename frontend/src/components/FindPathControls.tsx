import React, { useState } from 'react';
import {
  MapPin,
  ArrowRight,
  ArrowLeftRight,
  Sparkles,
  Compass,
  Shuffle,
  AlertCircle,
  CheckCircle2,
  Trash2,
} from 'lucide-react';
import { IntersectionNode } from '../types';

interface FindPathControlsProps {
  fromNode: IntersectionNode | null;
  toNode: IntersectionNode | null;
  selectionStep: 'from' | 'to';
  onSetSelectionStep: (step: 'from' | 'to') => void;
  onClearPoints: () => void;
  onSwapPoints: () => void;
  onOptimisePath: (algorithm: 'astar' | 'dijkstra') => void;
  onBaselinePath: () => void;
  onRandomizeTraffic: (seed?: number) => void;
  isComputing: boolean;
  reachabilityError: string | null;
  algorithm: 'astar' | 'dijkstra';
  onAlgorithmChange: (algo: 'astar' | 'dijkstra') => void;
}

export const FindPathControls: React.FC<FindPathControlsProps> = ({
  fromNode,
  toNode,
  selectionStep,
  onSetSelectionStep,
  onClearPoints,
  onSwapPoints,
  onOptimisePath,
  onBaselinePath,
  onRandomizeTraffic,
  isComputing,
  reachabilityError,
  algorithm,
  onAlgorithmChange,
}) => {
  const [customSeed, setCustomSeed] = useState<string>('');

  const canCompute = fromNode !== null && toNode !== null && !isComputing;

  return (
    <div className="h-full flex flex-col bg-slate-900 border-r border-slate-800 p-4 overflow-y-auto space-y-4">
      {/* Title & Guidance */}
      <div className="border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2 text-cyan-400 font-bold text-sm tracking-wider uppercase">
          <Compass className="w-4 h-4" />
          <span>Route Optimisation</span>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Select origin and destination nodes by clicking on the map or buttons below, then compare algorithmic routing against static baseline navigation.
        </p>
      </div>

      {/* Point Selection Step Flow */}
      <div className="space-y-2">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Point Selection
        </div>

        {/* FROM Selection */}
        <div
          onClick={() => onSetSelectionStep('from')}
          className={`p-3 rounded-lg border cursor-pointer transition flex items-center justify-between ${
            selectionStep === 'from'
              ? 'border-emerald-500 bg-emerald-950/20 ring-1 ring-emerald-500/50'
              : fromNode
              ? 'border-slate-700 bg-slate-800/60'
              : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              fromNode ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400'
            }`}>
              A
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                Origin (FROM)
              </div>
              <div className="text-xs font-bold text-slate-200">
                {fromNode ? `${fromNode.name} (${fromNode.node_id})` : 'Click map to select FROM'}
              </div>
            </div>
          </div>
          {selectionStep === 'from' && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-900 text-emerald-300 font-bold uppercase animate-pulse">
              Selecting
            </span>
          )}
        </div>

        {/* SWAP / CLEAR BUTTONS */}
        <div className="flex items-center justify-end space-x-2 py-0.5">
          <button
            onClick={onSwapPoints}
            disabled={!fromNode || !toNode}
            className="flex items-center space-x-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition px-2 py-1 rounded bg-slate-800/50 border border-slate-700/50"
            title="Swap Origin and Destination"
          >
            <ArrowLeftRight className="w-3 h-3" />
            <span>Swap</span>
          </button>
          <button
            onClick={onClearPoints}
            disabled={!fromNode && !toNode}
            className="flex items-center space-x-1 text-[11px] text-rose-400 hover:text-rose-300 disabled:opacity-40 disabled:cursor-not-allowed transition px-2 py-1 rounded bg-rose-950/20 border border-rose-900/40"
            title="Clear points"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear</span>
          </button>
        </div>

        {/* TO Selection */}
        <div
          onClick={() => onSetSelectionStep('to')}
          className={`p-3 rounded-lg border cursor-pointer transition flex items-center justify-between ${
            selectionStep === 'to'
              ? 'border-indigo-500 bg-indigo-950/20 ring-1 ring-indigo-500/50'
              : toNode
              ? 'border-slate-700 bg-slate-800/60'
              : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              toNode ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400'
            }`}>
              B
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-400">
                Destination (TO)
              </div>
              <div className="text-xs font-bold text-slate-200">
                {toNode ? `${toNode.name} (${toNode.node_id})` : 'Click map to select TO'}
              </div>
            </div>
          </div>
          {selectionStep === 'to' && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-900 text-indigo-300 font-bold uppercase animate-pulse">
              Selecting
            </span>
          )}
        </div>
      </div>

      {/* Reachability Warning / Error Message */}
      {reachabilityError && (
        <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-200 text-xs flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{reachabilityError}</span>
        </div>
      )}

      {/* Algorithm Choice Toggle for Optimised */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Optimiser Algorithm
          </span>
          <span className="text-[10px] text-cyan-400 font-mono">
            {algorithm === 'astar' ? 'Admissible A*' : 'Dijkstra'}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onAlgorithmChange('astar')}
            className={`py-1.5 px-3 rounded text-xs font-semibold tracking-wide transition ${
              algorithm === 'astar'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40 border border-cyan-400/50'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
            }`}
          >
            A* (Heuristic)
          </button>
          <button
            onClick={() => onAlgorithmChange('dijkstra')}
            className={`py-1.5 px-3 rounded text-xs font-semibold tracking-wide transition ${
              algorithm === 'dijkstra'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40 border border-cyan-400/50'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
            }`}
          >
            Dijkstra
          </button>
        </div>
      </div>

      {/* Action Buttons: Optimise vs Baseline */}
      <div className="space-y-2 pt-1">
        <button
          onClick={() => onOptimisePath(algorithm)}
          disabled={!canCompute}
          className={`w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg font-bold text-xs tracking-wider uppercase transition shadow-lg ${
            canCompute
              ? 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-900/40 border border-cyan-400/50 ring-1 ring-cyan-400/30'
              : 'bg-slate-800/80 text-slate-500 border border-slate-800 cursor-not-allowed'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>{isComputing ? 'Computing...' : 'Optimise Path'}</span>
        </button>

        <button
          onClick={onBaselinePath}
          disabled={!canCompute}
          className={`w-full flex items-center justify-center space-x-2 py-2 px-4 rounded-lg font-bold text-xs tracking-wider uppercase transition ${
            canCompute
              ? 'bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-600/40 hover:border-amber-500'
              : 'bg-slate-800/50 text-slate-600 border border-slate-800/60 cursor-not-allowed'
          }`}
          title="Baseline path: shortest distance ignoring congestion and road closures"
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Without Optimisation</span>
        </button>
      </div>

      {/* Randomize Traffic Tool */}
      <div className="mt-auto pt-4 border-t border-slate-800 space-y-3">
        <div className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-300">
          <Shuffle className="w-3.5 h-3.5 text-purple-400" />
          <span>Randomize Traffic & Closures</span>
        </div>
        <p className="text-[11px] text-slate-400">
          Injects realistic random congestion multipliers and blocks 2–4 roads across Cyber City to stress-test route comparisons.
        </p>

        <div className="flex items-center space-x-2">
          <input
            type="number"
            placeholder="Seed (opt)"
            value={customSeed}
            onChange={(e) => setCustomSeed(e.target.value)}
            className="w-24 px-2 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-purple-500 font-mono"
          />
          <button
            onClick={() => {
              const seedNum = customSeed ? parseInt(customSeed, 10) : undefined;
              onRandomizeTraffic(seedNum);
            }}
            disabled={isComputing}
            className="flex-1 py-1.5 px-3 rounded text-xs font-bold tracking-wider uppercase bg-purple-950/70 hover:bg-purple-900 text-purple-200 border border-purple-700/60 hover:border-purple-500 transition flex items-center justify-center space-x-1.5"
          >
            <Shuffle className="w-3 h-3 text-purple-300" />
            <span>Apply Traffic</span>
          </button>
        </div>
      </div>
    </div>
  );
};
