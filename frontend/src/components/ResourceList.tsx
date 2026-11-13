import React from 'react';
import { EmergencyUnit } from '../types';
import { Truck, Clock, Shield } from 'lucide-react';

interface ResourceListProps {
  units: EmergencyUnit[];
}

export const ResourceList: React.FC<ResourceListProps> = ({ units }) => {
  const getUnitBadge = (type: string) => {
    switch (type) {
      case 'ambulance':
        return { icon: '🚑', color: 'text-cyan-400 bg-cyan-950/60 border-cyan-800' };
      case 'police_patrol':
        return { icon: '🚓', color: 'text-indigo-400 bg-indigo-950/60 border-indigo-800' };
      case 'fire_engine':
      default:
        return { icon: '🚒', color: 'text-rose-400 bg-rose-950/60 border-rose-800' };
    }
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-2.5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <Truck className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Emergency Response Fleet
          </span>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-semibold">
          {units.length} Units Available
        </span>
      </div>

      <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
        {units.map((unit) => {
          const badge = getUnitBadge(unit.unit_type);
          const isActive = unit.status !== 'available' && unit.status !== 'stationed';
          const isMoving = unit.status === 'en_route' || unit.status === 'transporting' || unit.status === 'returning';

          const getStatusBadgeStyle = (st: string) => {
            switch (st) {
              case 'en_route':
                return 'bg-cyan-950 text-cyan-300 border-cyan-800 animate-pulse';
              case 'transporting':
                return 'bg-teal-950 text-teal-300 border-teal-800 animate-pulse';
              case 'returning':
                return 'bg-indigo-950 text-indigo-300 border-indigo-800';
              case 'loading':
              case 'at_hospital':
              case 'on_scene':
                return 'bg-amber-950 text-amber-300 border-amber-800';
              case 'available':
              default:
                return 'bg-slate-800 text-slate-400 border-slate-700';
            }
          };

          return (
            <div
              key={unit.unit_id}
              className={`p-2 rounded-md border transition ${
                isActive
                  ? 'bg-slate-900 border-cyan-500/40 shadow-sm shadow-cyan-950'
                  : 'bg-slate-950/60 border-slate-800/80'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-sm">{badge.icon}</span>
                  <div>
                    <div className="text-xs font-bold text-slate-100">{unit.call_sign}</div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {unit.unit_id} • Node: {unit.current_node}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${getStatusBadgeStyle(
                      unit.status
                    )}`}
                  >
                    {unit.status.replace('_', ' ')}
                  </span>
                  {unit.patient_count !== undefined && unit.patient_count > 0 && (
                    <div className="text-[9px] font-mono text-rose-400 font-bold mt-0.5">
                      🚑 {unit.patient_count} patient(s)
                    </div>
                  )}
                  {unit.eta_seconds !== undefined && unit.eta_seconds !== null && isMoving && (
                    <div className="flex items-center justify-end space-x-1 text-[10px] font-mono text-cyan-300 mt-1">
                      <Clock className="w-3 h-3 text-cyan-400" />
                      <span>{unit.eta_seconds > 60 ? `~${Math.round(unit.eta_seconds / 60)} min` : `${Math.round(unit.eta_seconds)}s`} ETA</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
