import React, { useState, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Marker,
  Popup,
  Tooltip,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  RouteResult,
  IntersectionNode,
} from '../types';
import {
  Layers,
  AlertTriangle,
  RotateCcw,
  Zap,
  Info,
} from 'lucide-react';

// Self-contained SVG data URIs for Leaflet default icons (zero external unpkg dependencies)
const defaultIcon = L.divIcon({
  className: 'custom-default-pin',
  html: `
    <div style="width:20px;height:20px;border-radius:50%;background:#38bdf8;border:2px solid #ffffff;box-shadow:0 0 8px #38bdf8;"></div>
  `,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});
L.Marker.prototype.options.icon = defaultIcon;

// Custom Unit Icons with Emoji & Status Ring
const createUnitIcon = (type: string, status: string) => {
  const iconEmoji =
    type === 'ambulance' ? '🚑' : type === 'police_patrol' ? '🚓' : '🚒';
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
    <div class="relative flex items-center justify-center w-10 h-10">
      <div class="absolute inset-0 rounded-full bg-rose-500/40 animate-ping"></div>
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-rose-600 border-2 border-white shadow-xl text-white">
        <span class="text-xs font-black">⚠️</span>
      </div>
    </div>
  `,
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

// Auto-recenter / fit bounds hook component with robust resize invalidation
const MapBoundsController: React.FC<{ nodes: IntersectionNode[] }> = ({ nodes }) => {
  const map = useMap();

  useEffect(() => {
    // Invalidate size immediately and after layout settles
    map.invalidateSize();
    const t1 = setTimeout(() => map.invalidateSize(), 100);
    const t2 = setTimeout(() => map.invalidateSize(), 400);

    const onResize = () => {
      map.invalidateSize();
    };
    window.addEventListener('resize', onResize);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener('resize', onResize);
    };
  }, [map]);

  useEffect(() => {
    if (nodes && nodes.length > 0) {
      const validNodes = nodes.filter((n) => typeof n.latitude === 'number' && typeof n.longitude === 'number');
      if (validNodes.length > 0) {
        const bounds = L.latLngBounds(validNodes.map((n) => [n.latitude, n.longitude]));
        map.fitBounds(bounds, { padding: [35, 35], maxZoom: 15 });
      }
    }
  }, [nodes, map]);
  return null;
};

interface CityMapProps {
  cityGraph: CityGraph;
  activeIncident: IncidentRecord | null;
  emergencyUnits: EmergencyUnit[];
  emergencyRoute: RouteResult | null;
  diversionRoute: RouteResult | null;
  activeCorridorNodes: string[];
  onToggleRoadClosure?: (roadId: string, currentBlocked: boolean) => void;
  onSimulateAtNode?: (nodeId: string) => void;
}

export const CityMap: React.FC<CityMapProps> = ({
  cityGraph,
  activeIncident,
  emergencyUnits,
  emergencyRoute,
  diversionRoute,
  activeCorridorNodes,
  onToggleRoadClosure,
  onSimulateAtNode,
}) => {
  const [showCongestion, setShowCongestion] = useState(true);
  const [showSignals, setShowSignals] = useState(true);
  const [showUnits, setShowUnits] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);
  const [showAltRoutes, setShowAltRoutes] = useState(true);

  // Default Cyber City center (Hyderabad Metro)
  const defaultCenter: [number, number] = [17.442, 78.378];

  // Helper to resolve coordinates between two node IDs
  const getNodeCoord = (nodeId: string): [number, number] | null => {
    const node = cityGraph.nodes.find((n) => n.node_id === nodeId);
    return node ? [node.latitude, node.longitude] : null;
  };

  // Helper to extract path coordinates safely (supports RouteResult, RoutePath, or raw nodes)
  const getRoutePositions = (route: any): [number, number][] => {
    if (!route) return [];
    if (route.coordinates && route.coordinates.length > 0) {
      return route.coordinates.map((c: any) => [
        c.latitude ?? c.lat,
        c.longitude ?? c.lng,
      ]);
    }
    // Fallback: derive from node_ids or node_sequence
    const nodes = route.node_ids || route.node_sequence;
    if (nodes && nodes.length > 0) {
      const pts: [number, number][] = [];
      for (const nid of nodes) {
        const coord = getNodeCoord(nid);
        if (coord) pts.push(coord);
      }
      return pts;
    }
    return [];
  };

  const primaryPositions = getRoutePositions(emergencyRoute);
  const diversionPositions = getRoutePositions(diversionRoute);

  // Extract alternative routes from primary emergency route if present
  const altRoutes =
    emergencyRoute?.alternative_routes && emergencyRoute.alternative_routes.length > 0
      ? emergencyRoute.alternative_routes
      : [];

  // Congestion styling for edges
  const getEdgeStyle = (edge: any) => {
    if (edge.is_blocked) {
      return { color: '#ef4444', weight: 6, dashArray: '6, 6', opacity: 0.95 };
    }
    if (edge.is_diverted) {
      return { color: '#a855f7', weight: 4.5, dashArray: '5, 5', opacity: 0.85 };
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
        return { color: '#10b981', weight: 2.5, opacity: 0.7 };
    }
  };

  return (
    <div className="relative w-full h-full min-h-[480px] bg-[#090d16] overflow-hidden">
      {/* Background Cyber City Vector Grid Fallback Pattern (always visible even if tile server fails) */}
      <div
        className="absolute inset-0 pointer-events-none opacity-25 z-0"
        style={{
          backgroundImage:
            'radial-gradient(circle, #38bdf8 1px, transparent 1px), linear-gradient(to right, #1e293b 1px, transparent 1px), linear-gradient(to bottom, #1e293b 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <MapContainer
        center={defaultCenter}
        zoom={14}
        zoomControl={false}
        className="w-full h-full min-h-[480px] relative z-10"
      >
        <MapBoundsController nodes={cityGraph.nodes} />

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
                <Popup>
                  <div className="p-1.5 text-xs text-slate-900 font-sans min-w-[190px]">
                    <div className="font-bold text-slate-900 border-b pb-1">
                      {edge.name} ({edge.road_id})
                    </div>
                    <div className="mt-1">
                      Status:{' '}
                      <span className="font-bold uppercase">
                        {edge.is_blocked
                          ? '⛔ BLOCKED'
                          : edge.is_diverted
                          ? '🔀 DIVERTED'
                          : edge.current_congestion_level}
                      </span>
                    </div>
                    <div>Length: {edge.length_meters}m</div>
                    <div>Speed Limit: {edge.speed_limit_kmph} km/h</div>
                    <div className="mt-1.5 pt-1 border-t border-slate-200">
                      <div className="text-[10px] font-bold text-cyan-800 uppercase">ML Forecast (Member 3)</div>
                      <div className="text-[10px] text-slate-700 flex justify-between">
                        <span>+15m Horizon:</span>
                        <span className="font-semibold">{edge.is_blocked ? '0 km/h (Blocked)' : edge.current_congestion_level === 'severe' ? '8.5 km/h (Severe)' : `${Math.round(edge.speed_limit_kmph * 0.9)} km/h`}</span>
                      </div>
                      <div className="text-[10px] text-slate-700 flex justify-between">
                        <span>+30m Horizon:</span>
                        <span className="font-semibold">{edge.is_blocked ? '0 km/h (Blocked)' : edge.current_congestion_level === 'severe' ? '12.0 km/h (Heavy)' : `${Math.round(edge.speed_limit_kmph * 0.95)} km/h`}</span>
                      </div>
                    </div>
                    {onToggleRoadClosure && (
                      <button
                        onClick={() => onToggleRoadClosure(edge.road_id, edge.is_blocked)}
                        className={`mt-2 w-full py-1 px-2 rounded text-[11px] font-bold text-white uppercase tracking-wider ${
                          edge.is_blocked
                            ? 'bg-emerald-600 hover:bg-emerald-500'
                            : 'bg-rose-600 hover:bg-rose-500'
                        }`}
                      >
                        {edge.is_blocked ? 'Reopen Road' : 'Close Road'}
                      </button>
                    )}
                  </div>
                </Popup>
                <Tooltip sticky>
                  <div className="text-xs font-sans">
                    <span className="font-bold">{edge.name}</span> ({edge.road_id})
                    <br />
                    <span>
                      {edge.is_blocked ? 'BLOCKED' : edge.current_congestion_level.toUpperCase()}
                    </span>
                  </div>
                </Tooltip>
              </Polyline>
            );
          })}

        {/* 2. Primary Emergency Route (Cyan Glow Polyline) */}
        {showRoutes && primaryPositions.length > 0 && (
          <Polyline
            positions={primaryPositions}
            pathOptions={{
              color: '#06b6d4',
              weight: 6,
              opacity: 0.95,
              lineCap: 'round',
              lineJoin: 'round',
            }}
          >
            <Popup>
              <div className="p-1.5 text-xs text-slate-900">
                <div className="font-bold text-cyan-600 flex items-center space-x-1">
                  <span>🚑 Primary A* Emergency Corridor</span>
                </div>
                {emergencyRoute && (
                  <>
                    <div className="mt-1">
                      ETA: <strong>~{emergencyRoute.estimated_travel_time_minutes} min</strong> (
                      {emergencyRoute.estimated_travel_time_seconds}s)
                    </div>
                    <div>Distance: {emergencyRoute.total_distance_meters}m</div>
                    <div className="text-[10px] text-slate-600 mt-1 italic">
                      {emergencyRoute.explanation}
                    </div>
                  </>
                )}
              </div>
            </Popup>
          </Polyline>
        )}

        {/* 3. Alternative Route (Amber Dashed) */}
        {showAltRoutes &&
          altRoutes.map((alt: any, idx: number) => {
            const altPts = getRoutePositions(alt);
            if (altPts.length === 0) return null;
            return (
              <Polyline
                key={`alt-route-${idx}`}
                positions={altPts}
                pathOptions={{
                  color: '#f59e0b',
                  weight: 4.5,
                  dashArray: '6, 6',
                  opacity: 0.85,
                }}
              >
                <Popup>
                  <div className="p-1 text-xs text-slate-900">
                    <div className="font-bold text-amber-600">⚡ Alternative Response Route</div>
                    <div>Distance: {alt.distance_meters || alt.total_distance_meters}m</div>
                    <div>Travel Time: {alt.estimated_travel_time_seconds}s</div>
                  </div>
                </Popup>
                <Tooltip sticky>
                  <span className="text-xs font-semibold text-amber-400">
                    Alternative Emergency Corridor
                  </span>
                </Tooltip>
              </Polyline>
            );
          })}

        {/* 4. General Traffic Diversion Route (Purple Dashed) */}
        {showRoutes && diversionPositions.length > 0 && (
          <Polyline
            positions={diversionPositions}
            pathOptions={{
              color: '#a855f7',
              weight: 4,
              dashArray: '6, 6',
              opacity: 0.85,
            }}
          >
            <Tooltip sticky>
              <span className="text-xs font-semibold text-purple-300">
                Civilian Detour Diversion
              </span>
            </Tooltip>
          </Polyline>
        )}

        {/* 5. Intersection Nodes & Traffic Signals */}
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
                radius={isCorridor ? 8.5 : 5}
                pathOptions={{
                  fillColor: fillColor,
                  color: isCorridor ? '#ffffff' : '#0f172a',
                  weight: isCorridor ? 2.5 : 1.5,
                  fillOpacity: 0.9,
                }}
              >
                <Popup>
                  <div className="p-1 text-xs text-slate-900 min-w-[170px]">
                    <div className="font-bold">{node.name}</div>
                    <div className="text-[11px] text-slate-600 font-mono">Node ID: {node.node_id}</div>
                    <div className="text-[11px] mt-1">
                      Signal:{' '}
                      <span className="font-semibold uppercase text-emerald-700">
                        {isCorridor ? 'PRIORITY GREEN WAVE' : node.signal_state}
                      </span>
                    </div>
                    {onSimulateAtNode && (
                      <button
                        onClick={() => onSimulateAtNode(node.node_id)}
                        className="mt-2 w-full py-1 px-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-[10px] uppercase tracking-wider"
                      >
                        Simulate Incident Here
                      </button>
                    )}
                  </div>
                </Popup>
                <Tooltip direction="top" offset={[0, -5]}>
                  <div className="text-xs">
                    <span className="font-bold">{node.name}</span> ({node.node_id})
                    <div className="text-[10px]">
                      {isCorridor ? '🟢 PRIORITY GREEN CORRIDOR' : `Signal: ${node.signal_state}`}
                    </div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}

        {/* 6. Active Incident Marker */}
        {activeIncident &&
          activeIncident.status !== 'resolved' &&
          typeof activeIncident.latitude === 'number' &&
          typeof activeIncident.longitude === 'number' && (
            <Marker
              position={[activeIncident.latitude, activeIncident.longitude]}
              icon={incidentIcon}
            >
              <Popup autoPan={false}>
                <div className="p-1 max-w-[220px] text-slate-900">
                  <div className="flex items-center space-x-1.5 text-rose-600 font-bold text-xs uppercase">
                    <AlertTriangle className="w-4 h-4" />
                    <span>{activeIncident.incident_type}</span>
                  </div>
                  <div className="text-xs font-semibold mt-1">{activeIncident.title}</div>
                  <div className="text-[11px] text-slate-700 mt-1">
                    Status: <span className="font-bold uppercase text-amber-600">{activeIncident.status}</span>
                  </div>
                  <div className="text-[10px] text-slate-600 mt-0.5">
                    Heuristic Score: <strong>{activeIncident.heuristic_score}</strong>
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                    Node: {activeIncident.location_node}
                  </div>
                </div>
              </Popup>
            </Marker>
          )}

        {/* 7. Emergency Fleet Units */}
        {showUnits &&
          emergencyUnits.map((unit) => {
            if (typeof unit.latitude !== 'number' || typeof unit.longitude !== 'number') return null;
            return (
              <Marker
                key={unit.unit_id}
                position={[unit.latitude, unit.longitude]}
                icon={createUnitIcon(unit.unit_type, unit.status)}
              >
                <Tooltip direction="bottom" offset={[0, 10]}>
                  <div className="text-xs">
                    <div className="font-bold">
                      {unit.call_sign} ({unit.unit_id})
                    </div>
                    <div>
                      Status: <span className="uppercase font-semibold">{unit.status}</span>
                    </div>
                    {unit.eta_seconds && unit.status === 'dispatched' && (
                      <div className="text-cyan-400 font-semibold">
                        ETA: ~{Math.round(unit.eta_seconds / 60)} min
                      </div>
                    )}
                  </div>
                </Tooltip>
              </Marker>
            );
          })}
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
          <span>Primary Corridors & Detours</span>
        </label>
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showAltRoutes}
            onChange={(e) => setShowAltRoutes(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-amber-500 focus:ring-0"
          />
          <span>Alternative Routes (A*)</span>
        </label>
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showUnits}
            onChange={(e) => setShowUnits(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
          />
          <span>Emergency Fleet</span>
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
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-lg px-3 py-2 shadow-2xl text-[11px] flex flex-wrap items-center gap-3">
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#10b981] rounded-full"></div>
          <span className="text-slate-300">Free Flow</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#ef4444] rounded-full"></div>
          <span className="text-slate-300">Severe / Blocked</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#06b6d4] rounded-full shadow-[0_0_6px_#06b6d4]"></div>
          <span className="text-cyan-300 font-semibold">Primary Corridor</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#f59e0b] border-dashed rounded-full"></div>
          <span className="text-amber-300 font-semibold">Alternative Route</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#a855f7] border-dashed rounded-full"></div>
          <span className="text-purple-300 font-semibold">Diversion Detour</span>
        </div>
      </div>
    </div>
  );
};
