import React, { useState } from 'react';
import { IncidentRecord } from '../types';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Navigation,
  ShieldCheck,
  Check,
  Radio,
  FileText,
  Clock,
} from 'lucide-react';

interface IncidentPanelProps {
  incident: IncidentRecord | null;
  onVerify: () => void;
  onReject: () => void;
  onDispatch: () => void;
  onResolve: () => void;
  onSimulateDetection: (nodeId?: string, candidateType?: string) => void;
  isVerifying: boolean;
  isDispatching: boolean;
  isResolving: boolean;
  isRejecting: boolean;
}

export const IncidentPanel: React.FC<IncidentPanelProps> = ({
  incident,
  onVerify,
  onReject,
  onDispatch,
  onResolve,
  onSimulateDetection,
  isVerifying,
  isDispatching,
  isResolving,
  isRejecting,
}) => {
  const [selectedType, setSelectedType] = useState('possible_collision');

  // If no incident or incident is resolved
  if (!incident || incident.status === 'resolved') {
    return (
      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 flex flex-col space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Incident Triage
            </span>
          </div>
          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60">
            Standby
          </span>
        </div>

        <div className="text-center py-3 text-slate-400 text-xs">
          <p className="font-semibold text-slate-300">All Corridors Clear</p>
          <p className="text-[11px] text-slate-500 mt-1">
            {incident?.status === 'resolved'
              ? 'Prior incident resolved. Ready for next scenario.'
              : 'Awaiting computer vision detection or scenario trigger.'}
          </p>
        </div>

        {/* Trigger Detection Controls */}
        <div className="pt-1 border-t border-slate-800/80 space-y-2">
          <label className="text-[10px] text-slate-400 uppercase font-semibold block">
            Simulate Candidate Event
          </label>
          <div className="flex space-x-2">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded px-2 py-1.5 flex-1 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="possible_collision">Collision at Cyber Towers (INT-03)</option>
              <option value="stationary_vehicle">Stationary Vehicle Test (Safety Rule)</option>
            </select>
          </div>
          <button
            onClick={() => onSimulateDetection('INT-03', selectedType)}
            className="w-full py-2 px-3 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow"
          >
            <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-200" />
            <span>Detect Incident</span>
          </button>
        </div>
      </div>
    );
  }

  const isCandidate = incident.status === 'candidate';
  const isVerified =
    incident.status === 'verified' || incident.status === 'response_recommended';
  const isDispatched = incident.status === 'simulated_dispatch';

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Incident Triage
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">
            {incident.incident_id}
          </span>
        </div>
        <span
          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
            isDispatched
              ? 'bg-cyan-950 text-cyan-400 border-cyan-800/80'
              : isVerified
              ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
              : 'bg-amber-950/80 text-amber-400 border-amber-800/60 animate-pulse'
          }`}
        >
          {incident.status.replace('_', ' ')}
        </span>
      </div>

      {/* Title & Structured Report */}
      <div>
        <h3 className="text-xs font-bold text-slate-100">{incident.title}</h3>
        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed bg-slate-950/60 p-2 rounded border border-slate-800/60">
          {incident.structured_report ||
            'CCTV heuristic flagged vehicle deceleration and abrupt stop outside signal zone.'}
        </p>
      </div>

      {/* Metric Breakdown Grid */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase">Location Node</span>
          <span className="font-bold text-cyan-400">{incident.location_node}</span>
        </div>
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase">Blocked Road</span>
          <span className="font-bold text-rose-400">{incident.affected_road_id || 'ROAD-03A'}</span>
        </div>
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase">Heuristic Confidence</span>
          <div className="flex items-center space-x-1.5 mt-0.5">
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-rose-500 rounded-full"
                style={{ width: `${Math.min(100, (incident.heuristic_score || 0.85) * 100)}%` }}
              />
            </div>
            <span className="font-mono text-[10px] text-slate-200">
              {(incident.heuristic_score || 0.85).toFixed(2)}
            </span>
          </div>
        </div>
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase">Severity</span>
          <span className="font-bold text-amber-300 uppercase">{incident.severity}</span>
        </div>
      </div>

      {/* Recommended Emergency Service */}
      {incident.recommended_service && (
        <div className="bg-cyan-950/40 border border-cyan-800/50 rounded p-2 text-xs">
          <span className="text-[10px] text-cyan-400 uppercase font-bold block">
            Recommended Service
          </span>
          <span className="text-slate-200 font-semibold uppercase text-[11px]">
            {incident.recommended_service}
          </span>
        </div>
      )}

      {/* Operator Action Buttons */}
      <div className="pt-1 flex flex-col space-y-2">
        {/* Step 1: Candidate Verification / Rejection */}
        {isCandidate && (
          <div className="flex space-x-2">
            <button
              onClick={onVerify}
              disabled={isVerifying || isRejecting}
              className="flex-1 py-2 px-3 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{isVerifying ? 'Verifying...' : 'Verify Incident'}</span>
            </button>
            <button
              onClick={onReject}
              disabled={isVerifying || isRejecting}
              className="py-2 px-3 rounded bg-rose-800 hover:bg-rose-700 text-white font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow"
              title="Reject as false alarm / ignore stationary vehicle"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>{isRejecting ? 'Rejecting...' : 'Reject (False Alarm)'}</span>
            </button>
          </div>
        )}

        {/* Step 2: Verified -> Dispatch Units */}
        {isVerified && (
          <button
            onClick={onDispatch}
            disabled={isDispatching}
            className="w-full py-2 px-3 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow border border-cyan-400/40"
          >
            <Navigation className="w-3.5 h-3.5 fill-current" />
            <span>{isDispatching ? 'Computing A* Route...' : 'Dispatch Emergency Units'}</span>
          </button>
        )}

        {/* Step 3: Dispatched -> Resolve Incident */}
        {isDispatched && (
          <button
            onClick={onResolve}
            disabled={isResolving}
            className="w-full py-2 px-3 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow border border-emerald-500/40"
          >
            <Check className="w-3.5 h-3.5" />
            <span>{isResolving ? 'Resolving Scene...' : 'Resolve Incident & Reopen Corridors'}</span>
          </button>
        )}
      </div>

      <div className="text-[10px] text-slate-500 italic text-center">
        {isCandidate
          ? 'Human operator verification strictly required. Safety policy active.'
          : isVerified
          ? 'Incident verified. Emergency units allocated and ready for dispatch.'
          : 'Emergency corridor and signal preemption active.'}
      </div>
    </div>
  );
};
