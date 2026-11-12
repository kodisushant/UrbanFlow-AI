import React from 'react';
import { AgentLogEntry } from '../types';
import { Bot, MessageSquare, Terminal } from 'lucide-react';

interface AgentLogFeedProps {
  logs: AgentLogEntry[];
}

export const AgentLogFeed: React.FC<AgentLogFeedProps> = ({ logs }) => {
  const getAgentBadge = (name: string) => {
    switch (name) {
      case 'VisionAgent':
        return { icon: '👁️', color: 'text-amber-400 bg-amber-950/40 border-amber-800' };
      case 'IncidentAgent':
        return { icon: '🧠', color: 'text-rose-400 bg-rose-950/40 border-rose-800' };
      case 'EmergencyAgent':
        return { icon: '🚑', color: 'text-cyan-400 bg-cyan-950/40 border-cyan-800' };
      case 'RouteAgent':
        return { icon: '🗺️', color: 'text-purple-400 bg-purple-950/40 border-purple-800' };
      case 'TrafficAgent':
      default:
        return { icon: '🚦', color: 'text-emerald-400 bg-emerald-950/40 border-emerald-800' };
    }
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3.5 flex flex-col space-y-2 flex-1 min-h-[220px]">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Multi-Agent Reasoning Stream
          </span>
        </div>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-semibold">
          {logs.length} Actions
        </span>
      </div>

      <div className="space-y-2 overflow-y-auto max-h-64 pr-1 text-xs">
        {logs.map((log, index) => {
          const badge = getAgentBadge(log.agent_name);

          return (
            <div
              key={index}
              className="bg-slate-950/80 border border-slate-800/80 rounded-md p-2 space-y-1 hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs">{badge.icon}</span>
                  <span className="font-bold text-slate-200">{log.agent_name}</span>
                  <span className="text-[10px] text-slate-400 font-mono">({log.role})</span>
                </div>
                <span className="text-[10px] font-mono text-cyan-400">{log.timestamp}</span>
              </div>

              <div className="text-[11px] font-semibold text-slate-300">
                Action: <span className="text-cyan-300">{log.action}</span>
              </div>

              <p className="text-[10px] text-slate-400 leading-relaxed bg-slate-900/60 p-1.5 rounded border border-slate-900">
                {log.reasoning}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
