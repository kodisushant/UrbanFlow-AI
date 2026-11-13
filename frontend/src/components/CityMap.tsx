import React, { useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Marker,
  Popup,
  Tooltip,
} from 'react-leaflet';
import L from 'leaflet';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';
import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  RouteResult,
} from '../types';
import { Layers, ShieldAlert, Navigation, Car, AlertTriangle } from 'lucide-react';

// Fix Leaflet marker icons in React using local bundled assets
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl,
});

// Custom Unit Icons
const createUnitIcon = (type: string, status: string) => {
  const iconEmoji = type === 'ambulance' ? '🚑' : type === 'police_patrol' ? '🚓' : '🚒';
  const borderColor = status === 'dispatched' ? '#06b6d4' : '#10b981';
  const pulseClass = status === 'dispatched' ? 'animate-bounce' : '';

  return L.divIcon({
    className: 'custom-unit-icon',
    html: `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-slate-900 border-2 ${pulseClass}" style="border-color: ${borderColor}; box-shadow: 0 0 12px ${borderColor}80;">
        <span class="text-sm select-none">${iconEmoji}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Incident Pin Icon
const incidentIcon = L.divIcon({
  className: 'custom-incident-icon',
  html: `
    <div class="relative flex items-center justify-center w-9 h-9">
      <div class="absolute inset-0 rounded-full bg-rose-500/40 animate-ping"></div>
      <div class="relative flex items-center justify-center w-7 h-7 rounded-full bg-rose-600 border-2 border-white shadow-lg text-white">
        <span class="text-xs font-black">⚠️</span>
      </div>
    </div>
  `,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
});

interface CityMapProps {
  cityGraph: CityGraph;
  activeIncident: IncidentRecord | null;
  emergencyUnits: EmergencyUnit[];
  emergencyRoute: RouteResult | null;
  diversionRoute: RouteResult | null;
  activeCorridorNodes: string[];
}

export const CityMap: React.FC<CityMapProps> = ({
  cityGraph,
  activeIncident,
  emergencyUnits,
  emergencyRoute,
  diversionRoute,
  activeCorridorNodes,
}) => {
  const [showCongestion, setShowCongestion] = useState(true);
  const [showSignals, setShowSignals] = useState(true);
  const [showUnits, setShowUnits] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);

  // Map center default (Cyber City / Hyderabad)
  const defaultCenter: [number, number] = [17.445, 78.375];

  // Helper to resolve coordinates between two node IDs
  const getNodeCoord = (nodeId: string): [number, number] | null => {
    const node = cityGraph.nodes.find((n) => n.node_id === nodeId);
    return node ? [node.latitude, node.longitude] : null;
  };

  // Congestion styling for edges
  const getEdgeStyle = (edge: any) => {
    if (edge.is_blocked) {
      return { color: '#ef4444', weight: 6, dashArray: '6, 6', opacity: 0.9 };
    }
    if (edge.is_diverted) {
      return { color: '#a855f7', weight: 4, dashArray: '4, 4', opacity: 0.8 };
    }
    switch (edge.current_congestion_level) {
      case 'severe':
        return { color: '#dc2626', weight: 5, opacity: 0.85 };
      case 'heavy':
        return { color: '#f97316', weight: 4.5, opacity: 0.8 };
      case 'moderate':
        return { color: '#f59e0b', weight: 3.5, opacity: 0.75 };
      case 'free_flow':
      default:
        return { color: '#10b981', weight: 2.5, opacity: 0.65 };
    }
  };

  return (
    <div className="relative w-full h-full bg-[#090d16] overflow-hidden">
      <MapContainer
        center={defaultCenter}
        zoom={14}
        zoomControl={false}
        className="w-full h-full"
      >
        {/* Dark Matter Base Tiles */}
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
          className="dark-tiles"
        />

        {/* 1. Road Network Congestion Layer */}
        {showCongestion &&
          cityGraph.edges.map((edge) => {
            const p1 = getNodeCoord(edge.source_node);
            const p2 = getNodeCoord(edge.target_node);
            if (!p1 || !p2) return null;

            return (
              <Polyline
                key={edge.road_id}
                positions={[p1, p2]}
                pathOptions={getEdgeStyle(edge)}
              >
                <Tooltip sticky className="custom-tooltip">
                  <div className="text-xs font-sans">
                    <div className="font-bold text-slate-100">{edge.name} ({edge.road_id})</div>
                    <div className="text-[11px] text-slate-300">
                      Status: <span className="uppercase font-semibold">{edge.is_blocked ? 'BLOCKED' : edge.current_congestion_level}</span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Length: {edge.length_meters}m | Speed: {edge.speed_limit_kmph} km/h
                    </div>
                  </div>
                </Tooltip>
              </Polyline>
            );
          })}

        {/* 2. Primary Emergency Route (Cyan Glow Polyline) */}
        {showRoutes && emergencyRoute && emergencyRoute.coordinates && (
          <Polyline
            positions={emergencyRoute.coordinates.map((c) => [c.latitude, c.longitude])}
            pathOptions={{
              color: '#06b6d4',
              weight: 6,
              opacity: 0.95,
              lineCap: 'round',
              lineJoin: 'round',
            }}
          >
            <Popup>
              <div className="p-1 text-xs">
                <div className="font-bold text-cyan-400">🚑 Optimized Emergency Route (A*)</div>
                <div>ETA: <strong>{emergencyRoute.estimated_travel_time_minutes} min</strong> ({emergencyRoute.estimated_travel_time_seconds}s)</div>
                <div>Distance: {emergencyRoute.total_distance_meters}m</div>
                <div className="text-[10px] text-slate-400 mt-1">{emergencyRoute.explanation}</div>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* 3. General Traffic Diversion Route (Purple Dashed) */}
        {showRoutes && diversionRoute && diversionRoute.coordinates && (
          <Polyline
            positions={diversionRoute.coordinates.map((c) => [c.latitude, c.longitude])}
            pathOptions={{
              color: '#a855f7',
              weight: 4,
              dashArray: '6, 6',
              opacity: 0.85,
            }}
          >
            <Tooltip sticky>
              <span className="text-xs font-semibold text-purple-300">Traffic Diversion Bypass</span>
            </Tooltip>
          </Polyline>
        )}

        {/* 4. Intersection Nodes & Traffic Signals */}
        {showSignals &&
          cityGraph.nodes.map((node) => {
            const isCorridor = activeCorridorNodes.includes(node.node_id);
            const fillColor = isCorridor
              ? '#22c55e'
              : node.signal_state === 'caution_flashing'
                ? '#f59e0b'
                : '#10b981';

            return (
              <CircleMarker
                key={node.node_id}
                center={[node.latitude, node.longitude]}
                radius={isCorridor ? 8 : 4.5}
                pathOptions={{
                  fillColor: fillColor,
                  color: isCorridor ? '#ffffff' : '#0f172a',
                  weight: isCorridor ? 2.5 : 1.5,
                  fillOpacity: 0.9,
                }}
              >
                <Tooltip direction="top" offset={[0, -5]}>
                  <div className="text-xs">
                    <div className="font-bold">{node.name} ({node.node_id})</div>
                    <div className="text-[10px]">
                      Signal: <span className="font-semibold uppercase">{isCorridor ? 'PRIORITY GREEN (CORRIDOR)' : node.signal_state}</span>
                    </div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

        {/* 5. Active Incident Pin */}
        {activeIncident && (
          <Marker
            position={[activeIncident.latitude, activeIncident.longitude]}
            icon={incidentIcon}
          >
            <Popup autoPan={false}>
              <div className="p-1 max-w-[220px]">
                <div className="flex items-center space-x-1.5 text-rose-500 font-bold text-xs uppercase">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{activeIncident.incident_type}</span>
                </div>
                <div className="text-xs font-semibold text-slate-200 mt-1">{activeIncident.title}</div>
                <div className="text-[11px] text-slate-300 mt-1">
                  Status: <span className="font-bold text-amber-400 uppercase">{activeIncident.status}</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Heuristic Score: <strong>{activeIncident.heuristic_score}</strong> (Capped)
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* 6. Emergency Units (Ambulance, Fire, Police) */}
        {showUnits &&
          emergencyUnits.map((unit) => (
            <Marker
              key={unit.unit_id}
              position={[unit.latitude, unit.longitude]}
              icon={createUnitIcon(unit.unit_type, unit.status)}
            >
              <Tooltip direction="bottom" offset={[0, 10]}>
                <div className="text-xs">
                  <div className="font-bold">{unit.call_sign} ({unit.unit_id})</div>
                  <div>Status: <span className="uppercase font-semibold">{unit.status}</span></div>
                  {unit.eta_seconds && (
                    <div className="text-cyan-400 font-semibold">ETA: ~{Math.round(unit.eta_seconds / 60)} min</div>
                  )}
                </div>
              </Tooltip>
            </Marker>
          ))}
      </MapContainer>

      {/* Layer Toggles Floating Control */}
      <div className="absolute top-4 right-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-lg p-3 shadow-2xl text-xs space-y-2">
        <div className="flex items-center space-x-1.5 text-slate-300 font-bold border-b border-slate-800 pb-1.5 uppercase tracking-wider text-[11px]">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Map Layers</span>
        </div>
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showCongestion}
            onChange={(e) => setShowCongestion(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
          />
          <span>Road Congestion</span>
        </label>
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showRoutes}
            onChange={(e) => setShowRoutes(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
          />
          <span>Corridors & Diversions</span>
        </label>
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showUnits}
            onChange={(e) => setShowUnits(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
          />
          <span>Emergency Units</span>
        </label>
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showSignals}
            onChange={(e) => setShowSignals(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
          />
          <span>Traffic Signals</span>
        </label>
      </div>

      {/* Map Legend Floating Control */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-lg px-3 py-2.5 shadow-2xl text-[11px] flex items-center space-x-4">
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#10b981] rounded-full"></div>
          <span className="text-slate-300">Free Flow</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#f59e0b] rounded-full"></div>
          <span className="text-slate-300">Moderate</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#ef4444] rounded-full"></div>
          <span className="text-slate-300">Severe / Jam</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#06b6d4] rounded-full shadow-[0_0_6px_#06b6d4]"></div>
          <span className="text-cyan-300 font-semibold">Emergency Route</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#a855f7] border-dashed rounded-full"></div>
          <span className="text-purple-300 font-semibold">Diversion</span>
        </div>
      </div>
    </div>
  );
};
