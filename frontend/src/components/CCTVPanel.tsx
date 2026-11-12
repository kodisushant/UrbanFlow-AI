import React from 'react';
import { Camera, AlertCircle, Eye } from 'lucide-react';

interface CCTVPanelProps {
  cameraId?: string;
  hasCandidateAlert?: boolean;
}

export const CCTVPanel: React.FC<CCTVPanelProps> = ({
  cameraId = 'cctv_camera_01',
  hasCandidateAlert = true,
}) => {
  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3 flex flex-col space-y-2">
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
        <div className="flex items-center space-x-1.5">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
          <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
            LIVE HEURISTIC
          </span>
        </div>
      </div>

      {/* Simulated Video Canvas with Bounding Box Overlays */}
      <div className="relative w-full h-44 bg-slate-950 rounded-md border border-slate-800/80 overflow-hidden flex items-center justify-center">
        {/* Background Road Grid Simulation */}
        <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px]"></div>

        {/* Lane Markings */}
        <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-24 border-y border-dashed border-slate-700/60 pointer-events-none"></div>

        {/* Bounding Box 1 (Car #14) */}
        <div className="absolute left-16 top-10 w-24 h-16 border-2 border-rose-500 bg-rose-500/10 rounded flex flex-col justify-between p-1 shadow-[0_0_10px_rgba(244,63,94,0.3)]">
          <div className="text-[9px] font-mono font-bold text-rose-300 bg-rose-950/80 px-1 rounded w-fit">
            #14 Car | Stopped
          </div>
          <div className="text-[9px] font-mono text-rose-400">
            0.02 bw/s
          </div>
        </div>

        {/* Bounding Box 2 (Truck #19) */}
        <div className="absolute left-36 top-12 w-28 h-20 border-2 border-rose-500 bg-rose-500/10 rounded flex flex-col justify-between p-1 shadow-[0_0_10px_rgba(244,63,94,0.3)]">
          <div className="text-[9px] font-mono font-bold text-rose-300 bg-rose-950/80 px-1 rounded w-fit">
            #19 Truck | Stopped
          </div>
          <div className="text-[9px] font-mono text-rose-400">
            0.01 bw/s
          </div>
        </div>

        {/* Moving Normal Vehicle (Car #22) */}
        <div className="absolute right-12 top-6 w-20 h-14 border border-emerald-500/80 bg-emerald-500/5 rounded flex flex-col justify-between p-1">
          <div className="text-[8px] font-mono text-emerald-300 bg-emerald-950/80 px-1 rounded w-fit">
            #22 Car
          </div>
          <div className="text-[8px] font-mono text-emerald-400">
            0.85 bw/s
          </div>
        </div>

        {/* Candidate Alert Banner Overlay */}
        {hasCandidateAlert && (
          <div className="absolute bottom-2 inset-x-2 bg-rose-950/90 border border-rose-600/60 rounded px-2.5 py-1.5 flex items-center justify-between text-xs backdrop-blur-sm">
            <div className="flex items-center space-x-1.5 text-rose-200">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              <span className="font-bold text-[11px] truncate">
                Candidate Collision Flagged outside stop line
              </span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-800 text-white font-bold">
              Score: 0.85
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
        <span>Vision Stride: 2 frames</span>
        <span>Resolution: 1920x1080 (ROI Calibrated)</span>
      </div>
    </div>
  );
};
