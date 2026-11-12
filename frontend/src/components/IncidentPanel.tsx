import React from 'react';
import { IncidentRecord } from '../types';
import { AlertTriangle, CheckCircle, Navigation, ShieldCheck } from 'lucide-react';

interface IncidentPanelProps {
  incident: IncidentRecord | null;
  onVerify: () => void;
  onDispatch: () => void;
  isVerifying: boolean;
  isDispatching: boolean;
}

export const IncidentPanel: React.FC<IncidentPanelProps> = ({
  incident,
  onVerify,
  onDispatch,
  isVerifying,
  isDispatching,
}) => {
  if (!incident) {
    return (
      <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-4 flex flex-col items-center justify-center text-slate-500 h-48">
        <ShieldCheck className="w-8 h-8 text-emerald-500/40 mb-2" />
        <span className="text-xs font-semibold uppercase tracking-wider">All Corridors Clear</span>
        <span className="text-[11px] text-slate-500">No active candidate incidents detected</span>
      </div>
    );
  }

  const isVerified = incident.status === 'verified' || incident.status === 'simulated_dispatch';
  const isDispatched = incident.status === 'simulated_dispatch';

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
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
            isVerified
              ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
              : 'bg-amber-950/80 text-amber-400 border-amber-800/60'
          }`}
        >
          {incident.status.replace('_', ' ')}
        </span>
      </div>

      {/* Title & Details */}
      <div>
        <h3 className="text-xs font-bold text-slate-100">{incident.title}</h3>
        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
          {incident.structured_report || 'CCTV heuristic detected abrupt stop and proximity outside stop-line zone.'}
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
          <span className="text-slate-400 block text-[10px] uppercase">Heuristic Score</span>
          <div className="flex items-center space-x-1 mt-0.5">
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-rose-500 rounded-full"
                style={{ width: `${(incident.heuristic_score / 0.85) * 100}%` }}
              ></div>
            </div>
            <span className="font-mono text-[10px] text-slate-200">{incident.heuristic_score}</span>
          </div>
        </div>
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase">Severity</span>
          <span className="font-bold text-amber-300 uppercase">{incident.severity}</span>
        </div>
      </div>

      {/* Operator Actions */}
      <div className="pt-1 flex items-center space-x-2">
        {!isVerified ? (
          <button
            onClick={onVerify}
            disabled={isVerifying}
            className="flex-1 py-1.5 px-3 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>{isVerifying ? 'Verifying...' : 'Verify Incident'}</span>
          </button>
        ) : (
          <button
            onClick={onDispatch}
            disabled={isDispatching || isDispatched}
            className={`flex-1 py-1.5 px-3 rounded font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-1.5 transition shadow ${
              isDispatched
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white border border-cyan-400/40'
            }`}
          >
            <Navigation className="w-3.5 h-3.5 fill-current" />
            <span>{isDispatched ? 'Units Dispatched' : 'Dispatch Emergency Units'}</span>
          </button>
        )}
      </div>

      <div className="text-[10px] text-slate-500 italic text-center">
        Human confirmation required. Simulated emergency dispatch prototype.
      </div>
    </div>
  );
};
