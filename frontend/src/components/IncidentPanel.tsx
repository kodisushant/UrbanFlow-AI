import React from 'react';
import { IncidentRecord } from '../types';
import { AlertTriangle, CheckCircle, Navigation, ShieldCheck, Flame, Users, ShieldAlert } from 'lucide-react';

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

  const isFire =
    (incident.scenario_type || '').toLowerCase() === 'fire' ||
    (incident.incident_type || '').toLowerCase().includes('fire');

  const isVerified =
    incident.status === 'verified' ||
    incident.status === 'response_recommended' ||
    incident.status === 'simulated_dispatch' ||
    incident.status === 'on_scene';
  const isDispatched =
    incident.status === 'simulated_dispatch' || incident.status === 'on_scene';

  const getUnitReason = (unitId: string) => {
    if (unitId.startsWith('AMB')) return 'Paramedic triage & emergency hospital transport';
    if (unitId.startsWith('FIRE')) return 'Rapid fire suppression & structural containment';
    if (unitId.startsWith('POLICE')) return 'Perimeter cordon & arterial traffic diversion';
    return 'Emergency incident support';
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center space-x-2">
          {isFire ? (
            <Flame className="w-4 h-4 text-orange-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          )}
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            {isFire ? 'Structure Fire Triage' : 'Traffic Collision Triage'}
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
        <div className="flex items-center space-x-2">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded border ${
            isFire ? 'bg-orange-950/80 text-orange-300 border-orange-800/60' : 'bg-rose-950/80 text-rose-300 border-rose-800/60'
          }`}>
            {isFire ? '🔥 Fire Emergency' : '⚠️ Traffic Accident'}
          </span>
        </div>
        <h3 className="text-xs font-bold text-slate-100 mt-1">{incident.title}</h3>
        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
          {incident.structured_report || (isFire ? 'Thermal infrared signature detected structural blaze with risk of smoke spread.' : 'CCTV heuristic detected abrupt multi-vehicle collision outside stop-line zone.')}
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
          <span className="text-slate-400 block text-[10px] uppercase flex items-center justify-between">
            <span>Patients</span>
            <Users className="w-3 h-3 text-rose-400" />
          </span>
          <span className="font-bold text-rose-400 font-mono">
            {incident.patient_count !== undefined ? incident.patient_count : 1} Patient(s)
          </span>
        </div>
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <span className="text-slate-400 block text-[10px] uppercase">Severity</span>
          <span className="font-bold text-amber-300 uppercase">{incident.severity}</span>
        </div>
      </div>

      {/* Dispatched Units & Operational Roles */}
      {incident.assigned_unit_ids && incident.assigned_unit_ids.length > 0 && (
        <div className="bg-slate-900/90 rounded border border-slate-800 p-2 text-[11px] space-y-1.5">
          <div className="text-[10px] font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1">
            <ShieldAlert className="w-3 h-3 text-cyan-400" />
            <span>Dispatched Fleet Units & Roles:</span>
          </div>
          <div className="space-y-1">
            {incident.assigned_unit_ids.map((uid) => (
              <div key={uid} className="flex items-start justify-between text-[10px] bg-slate-950/60 px-2 py-1 rounded border border-slate-800">
                <span className="font-mono font-bold text-cyan-300">{uid}</span>
                <span className="text-slate-400 text-right">{getUnitReason(uid)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

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
