import React, { useState } from 'react';
import { Camera, AlertCircle, Eye, ShieldCheck, Layers, Image as ImageIcon } from 'lucide-react';
import { IncidentRecord } from '../types';

interface CCTVPanelProps {
  cameraId?: string;
  hasCandidateAlert?: boolean;
  incident?: IncidentRecord | null;
}

// Tactical Corner Reticles for YOLO / OpenCV computer-vision bounding boxes
const CornerReticles: React.FC<{ color?: string }> = ({ color = '#f43f5e' }) => (
  <>
    <span className="absolute -top-0.5 -left-0.5 w-2 h-2 border-t-2 border-l-2 pointer-events-none" style={{ borderColor: color }} />
    <span className="absolute -top-0.5 -right-0.5 w-2 h-2 border-t-2 border-r-2 pointer-events-none" style={{ borderColor: color }} />
    <span className="absolute -bottom-0.5 -left-0.5 w-2 h-2 border-b-2 border-l-2 pointer-events-none" style={{ borderColor: color }} />
    <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 border-b-2 border-r-2 pointer-events-none" style={{ borderColor: color }} />
  </>
);

export const CCTVPanel: React.FC<CCTVPanelProps> = ({
  cameraId = 'cctv_camera_01',
  hasCandidateAlert = false,
  incident = null,
}) => {
  const [viewMode, setViewMode] = useState<'boxes' | 'snapshot'>('boxes');

  const isIncidentActive = hasCandidateAlert || !!incident;
  const heuristicScore = incident?.heuristic_score ?? 0.85;

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3 flex flex-col space-y-2">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <Camera className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            CCTV Analysis Feed
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {cameraId}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* View Mode Toggle when incident is active */}
          {isIncidentActive && (
            <div className="flex items-center bg-slate-900 border border-slate-800 rounded p-0.5 text-[10px]">
              <button
                onClick={() => setViewMode('boxes')}
                className={`px-1.5 py-0.5 rounded font-mono transition flex items-center space-x-1 ${
                  viewMode === 'boxes'
                    ? 'bg-rose-900/80 text-rose-200 border border-rose-700/60 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="YOLO Bounding Box Overlay"
              >
                <Layers className="w-2.5 h-2.5" />
                <span>Boxes</span>
              </button>
              <button
                onClick={() => setViewMode('snapshot')}
                className={`px-1.5 py-0.5 rounded font-mono transition flex items-center space-x-1 ${
                  viewMode === 'snapshot'
                    ? 'bg-rose-900/80 text-rose-200 border border-rose-700/60 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Raw Evidence Snapshot"
              >
                <ImageIcon className="w-2.5 h-2.5" />
                <span>Photo</span>
              </button>
            </div>
          )}

          {/* Live Indicator */}
          {isIncidentActive ? (
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                LIVE HEURISTIC
              </span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                LIVE MONITORING
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Video & Bounding Box Canvas */}
      <div className="relative w-full h-44 bg-slate-950 rounded-md border border-slate-800/80 overflow-hidden flex items-center justify-center">
        {/* Background Real CCTV Traffic Snapshot / Grid */}
        <img
          src={isIncidentActive ? '/assets/incident_evidence.jpg' : '/assets/cctv_feed.jpg'}
          alt="CCTV Feed"
          className="absolute inset-0 w-full h-full object-cover opacity-35 filter brightness-75 contrast-125"
        />

        {/* Overlay Dark Vignette Grid */}
        <div className="absolute inset-0 bg-slate-950/40 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none"></div>

        {/* Lane Markings */}
        <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-24 border-y border-dashed border-slate-600/40 pointer-events-none"></div>

        {/* ============================================================== */}
        {/* SCENARIO ACTIVE: INCIDENT PROOF WITH VEHICLE-SIZED BOUNDING BOXES */}
        {/* ============================================================== */}
        {isIncidentActive ? (
          viewMode === 'boxes' ? (
            <>
              {/* 1. Bounding Box: Compact Car #14 (Sedan Box: w-24 h-16) */}
              <div
                className="absolute left-10 top-8 w-24 h-16 border-2 border-rose-500 bg-rose-500/20 rounded flex flex-col justify-between p-1 shadow-[0_0_14px_rgba(244,63,94,0.45)] transition-all animate-pulse"
                style={{ animationDuration: '2.5s' }}
              >
                <CornerReticles color="#f43f5e" />
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono font-bold text-rose-200 bg-rose-950/90 px-1 rounded shadow-sm">
                    #14 Car | Stopped
                  </span>
                  <span className="text-[8px] font-mono font-semibold text-rose-300 bg-rose-900/60 px-0.5 rounded">
                    Sedan
                  </span>
                </div>
                <div className="flex items-center justify-between text-[8px] font-mono">
                  <span className="text-rose-400 font-bold">0.02 bw/s</span>
                  <span className="text-slate-400 text-[7px]">[96×64]</span>
                </div>
              </div>

              {/* 2. Bounding Box: Large Freight Truck #19 (Significantly larger commercial rectangle: w-36 h-22) */}
              <div
                className="absolute left-30 top-6 w-36 h-22 border-2 border-rose-500 bg-rose-500/20 rounded flex flex-col justify-between p-1.5 shadow-[0_0_16px_rgba(244,63,94,0.5)] transition-all animate-pulse"
                style={{ animationDuration: '2.5s' }}
              >
                <CornerReticles color="#f43f5e" />
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono font-bold text-rose-200 bg-rose-950/90 px-1 rounded shadow-sm">
                    #19 Truck | Stopped
                  </span>
                  <span className="text-[8px] font-mono font-semibold text-rose-300 bg-rose-900/60 px-0.5 rounded">
                    Heavy Freight
                  </span>
                </div>
                <div className="flex items-center justify-between text-[8px] font-mono">
                  <span className="text-rose-400 font-bold">0.01 bw/s</span>
                  <span className="text-slate-400 text-[7px]">[144×88]</span>
                </div>
              </div>

              {/* 3. Collision Overlap / Proximity Impact Zone */}
              <div className="absolute left-28 top-12 w-10 h-10 border border-dashed border-amber-400 bg-amber-500/20 rounded flex items-center justify-center animate-ping pointer-events-none" style={{ animationDuration: '1.8s' }}>
                <span className="text-[8px] font-black text-amber-300 select-none">💥</span>
              </div>

              {/* 4. Normal Flowing Vehicle (Car #22) */}
              <div className="absolute right-8 top-5 w-20 h-14 border border-emerald-500/80 bg-emerald-500/10 rounded flex flex-col justify-between p-1 transition-all">
                <CornerReticles color="#10b981" />
                <div className="text-[8px] font-mono text-emerald-300 bg-emerald-950/90 px-1 rounded w-fit">
                  #22 Car
                </div>
                <div className="text-[8px] font-mono text-emerald-400">
                  0.85 bw/s (Flowing)
                </div>
              </div>
            </>
          ) : (
            /* Full Snapshot View with Camera Watermark */
            <div className="relative w-full h-full flex flex-col justify-between p-2">
              <div className="flex items-center justify-between text-[9px] font-mono bg-slate-950/80 px-2 py-1 rounded border border-slate-800/80 w-fit">
                <span className="text-rose-400 font-bold">● EVIDENCE FRAME #426</span>
                <span className="text-slate-400 ml-2">1080p ROI CALIBRATED</span>
              </div>
              <div className="text-[9px] font-mono bg-slate-950/80 px-2 py-1 rounded border border-rose-700/60 text-rose-300 w-fit">
                Two-Vehicle Impact Confirmed outside stop line
              </div>
            </div>
          )
        ) : (
          /* ============================================================== */
          /* BASELINE / IDLE: NORMAL MONITORING TRAFFIC BOUNDING BOXES      */
          /* ============================================================== */
          <>
            {/* Flowing Car #07 (Normal compact rectangle) */}
            <div className="absolute left-12 top-10 w-22 h-14 border border-emerald-500/70 bg-emerald-500/10 rounded flex flex-col justify-between p-1">
              <CornerReticles color="#10b981" />
              <div className="text-[8px] font-mono text-emerald-300 bg-emerald-950/80 px-1 rounded w-fit">
                #07 Sedan
              </div>
              <div className="text-[8px] font-mono text-emerald-400">
                0.82 bw/s
              </div>
            </div>

            {/* Flowing Bus #03 (Commercial long rectangle: w-32 h-18) */}
            <div className="absolute left-38 top-8 w-32 h-18 border border-emerald-500/70 bg-emerald-500/10 rounded flex flex-col justify-between p-1">
              <CornerReticles color="#10b981" />
              <div className="text-[8px] font-mono text-emerald-300 bg-emerald-950/80 px-1 rounded w-fit">
                #03 Transit Bus
              </div>
              <div className="text-[8px] font-mono text-emerald-400">
                0.74 bw/s
              </div>
            </div>

            {/* Flowing Car #12 */}
            <div className="absolute right-10 top-6 w-20 h-14 border border-emerald-500/70 bg-emerald-500/10 rounded flex flex-col justify-between p-1">
              <CornerReticles color="#10b981" />
              <div className="text-[8px] font-mono text-emerald-300 bg-emerald-950/80 px-1 rounded w-fit">
                #12 Sedan
              </div>
              <div className="text-[8px] font-mono text-emerald-400">
                0.88 bw/s
              </div>
            </div>
          </>
        )}

        {/* Bottom Banner */}
        {isIncidentActive ? (
          <div className="absolute bottom-2 inset-x-2 bg-rose-950/90 border border-rose-600/70 rounded px-2.5 py-1.5 flex items-center justify-between text-xs backdrop-blur-sm shadow-lg">
            <div className="flex items-center space-x-1.5 text-rose-200">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 animate-bounce" />
              <span className="font-bold text-[11px] truncate">
                Candidate Collision Flagged outside stop line
              </span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-800 text-white font-bold shrink-0">
              Score: {heuristicScore.toFixed(2)}
            </span>
          </div>
        ) : (
          <div className="absolute bottom-2 inset-x-2 bg-slate-900/90 border border-emerald-600/40 rounded px-2.5 py-1 flex items-center justify-between text-xs backdrop-blur-sm">
            <div className="flex items-center space-x-1.5 text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="text-[10px] text-emerald-300 font-semibold truncate">
                All Corridors Clear • Monitoring Traffic Flow
              </span>
            </div>
            <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 border border-emerald-800/60 text-emerald-300 font-bold">
              NOMINAL
            </span>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
        <span>Vision Stride: 2 frames</span>
        <span>Resolution: 1920x1080 (ROI Calibrated)</span>
      </div>
    </div>
  );
};
