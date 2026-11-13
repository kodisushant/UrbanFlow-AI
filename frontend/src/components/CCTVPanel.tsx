import React, { useState, useEffect } from 'react';
import { Camera, AlertCircle, Eye, RefreshCw, Radio } from 'lucide-react';

interface CCTVPanelProps {
  cameraId?: string;
  hasCandidateAlert?: boolean;
  onCameraChange?: (camId: string) => void;
  onAnalyzeFeed?: (camId: string) => void;
  isAnalyzing?: boolean;
}

export const CCTVPanel: React.FC<CCTVPanelProps> = ({
  cameraId = 'cctv_camera_01',
  hasCandidateAlert = false,
  onCameraChange,
  onAnalyzeFeed,
  isAnalyzing = false,
}) => {
  const [activeCam, setActiveCam] = useState(cameraId);

  useEffect(() => {
    setActiveCam(cameraId);
  }, [cameraId]);

  const handleSelect = (cam: string) => {
    setActiveCam(cam);
    if (onCameraChange) onCameraChange(cam);
  };

  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-lg p-3 flex flex-col space-y-2">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <Camera className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            CCTV Analysis Feed
          </span>
          <select
            value={activeCam}
            onChange={(e) => handleSelect(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-[10px] font-mono text-cyan-300 rounded px-1.5 py-0.5 focus:ring-0"
          >
            <option value="cctv_camera_01">cctv_camera_01 (INT-03)</option>
            <option value="cctv_camera_02">cctv_camera_02 (INT-01)</option>
          </select>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className={`w-2 h-2 rounded-full ${hasCandidateAlert ? 'bg-rose-500 animate-ping' : 'bg-emerald-500'}`} />
          <span className={`text-[10px] font-bold uppercase tracking-wider ${hasCandidateAlert ? 'text-rose-400' : 'text-emerald-400'}`}>
            {hasCandidateAlert ? 'ALERT ACTIVE' : 'MONITORING'}
          </span>
        </div>
      </div>

      {/* Simulated Video Canvas with Bounding Box Overlays */}
      <div className="relative w-full h-44 bg-slate-950 rounded-md border border-slate-800/80 overflow-hidden flex items-center justify-center">
        {/* Background Road Grid Simulation */}
        <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px]"></div>

        {/* Lane Markings */}
        <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 h-24 border-y border-dashed border-slate-700/60 pointer-events-none"></div>

        {/* Bounding Box 1 (Car #14) */}
        <div className={`absolute left-14 top-10 w-24 h-16 border-2 rounded flex flex-col justify-between p-1 transition shadow ${
          hasCandidateAlert ? 'border-rose-500 bg-rose-500/15 shadow-[0_0_12px_rgba(244,63,94,0.35)]' : 'border-emerald-500/60 bg-emerald-500/5'
        }`}>
          <div className="text-[9px] font-mono font-bold text-slate-200 bg-slate-900/90 px-1 rounded w-fit">
            #14 Car | {hasCandidateAlert ? 'Stopped 0.00' : 'Cruising 48km/h'}
          </div>
          <div className="text-[8px] font-mono text-slate-400">
            {hasCandidateAlert ? 'Outside stop line' : 'In-lane tracked'}
          </div>
        </div>

        {/* Bounding Box 2 (Truck #19) */}
        {hasCandidateAlert && (
          <div className="absolute left-34 top-12 w-28 h-20 border-2 border-rose-500 bg-rose-500/15 rounded flex flex-col justify-between p-1 shadow-[0_0_12px_rgba(244,63,94,0.35)]">
            <div className="text-[9px] font-mono font-bold text-rose-300 bg-rose-950/90 px-1 rounded w-fit">
              #19 Truck | Stopped 0.00
            </div>
            <div className="text-[8px] font-mono text-rose-400">
              Kinematics: 0.01 bw/s
            </div>
          </div>
        )}

        {/* Moving Normal Vehicle (Car #22) */}
        <div className="absolute right-10 top-6 w-20 h-14 border border-emerald-500/80 bg-emerald-500/5 rounded flex flex-col justify-between p-1">
          <div className="text-[8px] font-mono text-emerald-300 bg-emerald-950/80 px-1 rounded w-fit">
            #22 Car
          </div>
          <div className="text-[8px] font-mono text-emerald-400">
            0.85 bw/s (Moving)
          </div>
        </div>

        {/* Candidate Alert Banner Overlay */}
        {hasCandidateAlert ? (
          <div className="absolute bottom-2 inset-x-2 bg-rose-950/90 border border-rose-600/70 rounded px-2.5 py-1.5 flex items-center justify-between text-xs backdrop-blur-sm">
            <div className="flex items-center space-x-1.5 text-rose-200">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              <span className="font-bold text-[11px] truncate">
                Candidate Collision Flagged at {activeCam === 'cctv_camera_01' ? 'INT-03' : 'INT-01'}
              </span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-800 text-white font-bold">
              Score: 0.85
            </span>
          </div>
        ) : (
          <div className="absolute bottom-2 inset-x-2 bg-slate-900/90 border border-slate-700/60 rounded px-2.5 py-1 flex items-center justify-between text-xs">
            <span className="text-[11px] text-slate-400">Stream nominal. 0 anomalies detected.</span>
            {onAnalyzeFeed && (
              <button
                onClick={() => onAnalyzeFeed(activeCam)}
                disabled={isAnalyzing}
                className="text-[10px] font-semibold text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
              >
                <Radio className="w-3 h-3 animate-pulse" />
                <span>Trigger Analysis</span>
              </button>
            )}
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
