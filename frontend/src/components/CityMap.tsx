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
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import {
  CityGraph,
  EmergencyUnit,
  IncidentRecord,
  RouteResult,
  IntersectionNode,
  AppMode,
  FindPathResult,
} from '../types';
import {
  Layers,
  AlertTriangle,
  RotateCcw,
  Zap,
  Info,
  Clock,
  Compass,
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

// Endpoint Pin Icons for Find Path Mode (FROM = A / Green, TO = B / Rose)
const createEndpointIcon = (label: string, bg: string, ringColor: string) => {
  return L.divIcon({
    className: 'custom-endpoint-pin',
    html: `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full shadow-2xl font-black text-white text-[11px] border-2 border-white animate-bounce" style="background-color: ${bg}; box-shadow: 0 0 14px ${ringColor};">
        <span>${label}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};
const fromPinIcon = createEndpointIcon('A', '#10b981', '#34d399');
const toPinIcon = createEndpointIcon('B', '#f43f5e', '#fb7185');

// Auto-recenter / fit bounds hook component with robust resize invalidation
const MapBoundsController: React.FC<{ nodes: IntersectionNode[] }> = ({ nodes }) => {
  const map = useMap();

  useEffect(() => {
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
      const validNodes = nodes.filter(
        (n) => typeof n.latitude === 'number' && typeof n.longitude === 'number'
      );
      if (validNodes.length > 0) {
        const bounds = L.latLngBounds(validNodes.map((n) => [n.latitude, n.longitude]));
        map.fitBounds(bounds, { padding: [35, 35], maxZoom: 15 });
      }
    }
  }, [nodes, map]);
  return null;
};

// Map click listener hook component for snapping clicks to nearest node
const MapClickHandler: React.FC<{
  onMapClick?: (lat: number, lng: number) => void;
}> = ({ onMapClick }) => {
  useMapEvents({
    click(e) {
      if (onMapClick) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
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
  // Find Path Mode props
  appMode?: AppMode;
  fromNode?: string | null;
  toNode?: string | null;
  selectionTarget?: 'from' | 'to' | null;
  onSelectNode?: (nodeId: string) => void;
  findPathOptimisedRoute?: FindPathResult | null;
  findPathBaselineRoute?: FindPathResult | null;
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
  appMode = 'scenario',
  fromNode,
  toNode,
  selectionTarget,
  onSelectNode,
  findPathOptimisedRoute,
  findPathBaselineRoute,
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

  // Map click handler that snaps to the nearest node
  const handleMapClick = (lat: number, lng: number) => {
    if (appMode !== 'find_path' || !onSelectNode) return;
    let closestNodeId: string | null = null;
    let minDistanceSq = Infinity;

    for (const node of cityGraph.nodes) {
      const dLat = node.latitude - lat;
      const dLng = node.longitude - lng;
      const distSq = dLat * dLat + dLng * dLng;
      if (distSq < minDistanceSq) {
        minDistanceSq = distSq;
        closestNodeId = node.node_id;
      }
    }

    if (closestNodeId) {
      onSelectNode(closestNodeId);
    }
  };

  // Emergency scenario routes
  const primaryPositions = getRoutePositions(emergencyRoute);
  const diversionPositions = getRoutePositions(diversionRoute);
  const altRoutes =
    emergencyRoute?.alternative_routes && emergencyRoute.alternative_routes.length > 0
      ? emergencyRoute.alternative_routes
      : [];

  // Find Path Mode routes
  const optPositions = getRoutePositions(findPathOptimisedRoute);
  const basePositions = getRoutePositions(findPathBaselineRoute);

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
      {/* Background Cyber City Vector Grid Fallback Pattern */}
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
        <MapClickHandler onMapClick={handleMapClick} />

        {/* Dark Matter Base Tiles */}
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
          className="dark-tiles"
        />

        {/* 1. Road Network Congestion & Blockage Layer */}
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
                          ? '⛔ BLOCKED / CLOSED'
                          : edge.is_diverted
                          ? '🔀 DIVERTED'
                          : edge.current_congestion_level}
                      </span>
                    </div>
                    <div>Length: {edge.length_meters}m</div>
                    <div>Speed Limit: {edge.speed_limit_kmph} km/h</div>
                    <div>Congestion Multiplier: x{edge.congestion_weight_multiplier}</div>
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
                      {edge.is_blocked
                        ? '⛔ BLOCKED'
                        : `${edge.current_congestion_level.toUpperCase()} (x${edge.congestion_weight_multiplier})`}
                    </span>
                  </div>
                </Tooltip>
              </Polyline>
            );
          })}

        {/* ----------------------------------------------------------------- */}
        {/* FIND PATH MODE LAYERS                                             */}
        {/* ----------------------------------------------------------------- */}
        {appMode === 'find_path' && (
          <>
            {/* Optimised Route (Thick Cyan #06b6d4) */}
            {optPositions.length > 0 && (
              <Polyline
                positions={optPositions}
                pathOptions={{
                  color: '#06b6d4',
                  weight: 6.5,
                  opacity: 0.95,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
              >
                <Popup>
                  <div className="p-1.5 text-xs text-slate-900 font-sans">
                    <div className="font-bold text-cyan-700 flex items-center space-x-1">
                      <Zap className="w-3.5 h-3.5 fill-current" />
                      <span>Optimised Path ({findPathOptimisedRoute?.algorithm?.toUpperCase() || 'A*'})</span>
                    </div>
                    {findPathOptimisedRoute && (
                      <div className="mt-1 space-y-0.5">
                        <div>
                          ETA: <strong>{findPathOptimisedRoute.estimated_travel_time_minutes} min</strong> (
                          {findPathOptimisedRoute.estimated_travel_time_seconds}s)
                        </div>
                        <div>Distance: {findPathOptimisedRoute.total_distance_km} km</div>
                        <div>Explored: {findPathOptimisedRoute.nodes_explored} nodes ({findPathOptimisedRoute.compute_ms} ms)</div>
                        <div className="text-[10px] text-slate-600 italic mt-1">
                          {findPathOptimisedRoute.summary}
                        </div>
                      </div>
                    )}
                  </div>
                </Popup>
                <Tooltip sticky>
                  <span className="text-xs font-bold text-cyan-400">
                    ⚡ Optimised Route ({findPathOptimisedRoute?.estimated_travel_time_minutes} min)
                  </span>
                </Tooltip>
              </Polyline>
            )}

            {/* Baseline Route (Amber Dashed #f59e0b) */}
            {basePositions.length > 0 && (
              <Polyline
                positions={basePositions}
                pathOptions={{
                  color: '#f59e0b',
                  weight: 4.5,
                  dashArray: '7, 7',
                  opacity: 0.9,
                }}
              >
                <Popup>
                  <div className="p-1.5 text-xs text-slate-900 font-sans">
                    <div className="font-bold text-amber-700 flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>Baseline Route (Shortest Distance Only)</span>
                    </div>
                    {findPathBaselineRoute && (
                      <div className="mt-1 space-y-0.5">
                        <div>
                          Estimated Time: <strong>{findPathBaselineRoute.estimated_travel_time_minutes} min</strong> (
                          {findPathBaselineRoute.estimated_travel_time_seconds}s)
                        </div>
                        <div>Distance: {findPathBaselineRoute.total_distance_km} km</div>
                        {findPathBaselineRoute.blocked_roads_hit > 0 && (
                          <div className="text-rose-600 font-bold">
                            ⚠️ Hits {findPathBaselineRoute.blocked_roads_hit} blocked road(s) (+
                            {Math.round(findPathBaselineRoute.detour_penalty_seconds / 60)} min penalty)
                          </div>
                        )}
                        <div className="text-[10px] text-slate-600 italic mt-1">
                          {findPathBaselineRoute.summary}
                        </div>
                      </div>
                    )}
                  </div>
                </Popup>
                <Tooltip sticky>
                  <span className="text-xs font-bold text-amber-400">
                    ⏱️ Baseline Route ({findPathBaselineRoute?.estimated_travel_time_minutes} min)
                  </span>
                </Tooltip>
              </Polyline>
            )}

            {/* Blocked Segments on Baseline Path (Highlighted in Red Dashed) */}
            {findPathBaselineRoute?.segments?.map((seg, idx) => {
              if (!seg.is_blocked) return null;
              const p1 = getNodeCoord(seg.from_node);
              const p2 = getNodeCoord(seg.to_node);
              if (!p1 || !p2) return null;
              return (
                <Polyline
                  key={`blocked-seg-${idx}`}
                  positions={[p1, p2]}
                  pathOptions={{
                    color: '#ef4444',
                    weight: 6,
                    dashArray: '4, 4',
                    opacity: 0.98,
                  }}
                >
                  <Tooltip sticky>
                    <span className="text-xs font-bold text-rose-500">
                      ⛔ BLOCKED ROAD HIT ON BASELINE (+5m detour penalty)
                    </span>
                  </Tooltip>
                </Polyline>
              );
            })}

            {/* Origin (FROM) Marker Pin */}
            {fromNode && getNodeCoord(fromNode) && (
              <Marker position={getNodeCoord(fromNode)!} icon={fromPinIcon}>
                <Popup>
                  <div className="p-1 text-xs text-slate-900 font-sans font-bold">
                    🟢 Origin (FROM): {fromNode}
                  </div>
                </Popup>
              </Marker>
            )}

            {/* Destination (TO) Marker Pin */}
            {toNode && getNodeCoord(toNode) && (
              <Marker position={getNodeCoord(toNode)!} icon={toPinIcon}>
                <Popup>
                  <div className="p-1 text-xs text-slate-900 font-sans font-bold">
                    🔴 Destination (TO): {toNode}
                  </div>
                </Popup>
              </Marker>
            )}
          </>
        )}

        {/* ----------------------------------------------------------------- */}
        {/* SCENARIO MODE LAYERS                                              */}
        {/* ----------------------------------------------------------------- */}
        {appMode === 'scenario' && (
          <>
            {/* Primary Emergency Route (Cyan Glow Polyline) */}
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

            {/* Alternative Route (Amber Dashed) */}
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

            {/* Civilian Detour Diversion Route (Purple Dashed) */}
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

            {/* Active Incident Marker */}
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
                        Status:{' '}
                        <span className="font-bold uppercase text-amber-600">
                          {activeIncident.status}
                        </span>
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

            {/* Emergency Fleet Units */}
            {showUnits &&
              emergencyUnits.map((unit) => {
                if (typeof unit.latitude !== 'number' || typeof unit.longitude !== 'number')
                  return null;
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
          </>
        )}

        {/* ----------------------------------------------------------------- */}
        {/* INTERSECTION NODES & SIGNALS (Shared by both modes)               */}
        {/* ----------------------------------------------------------------- */}
        {showSignals &&
          cityGraph.nodes.map((node) => {
            const isCorridor = activeCorridorNodes.includes(node.node_id);
            const isFrom = appMode === 'find_path' && fromNode === node.node_id;
            const isTo = appMode === 'find_path' && toNode === node.node_id;

            const fillColor = isFrom
              ? '#10b981'
              : isTo
              ? '#f43f5e'
              : isCorridor
              ? '#22c55e'
              : node.signal_state === 'caution_flashing'
              ? '#f59e0b'
              : '#10b981';

            const radius = isFrom || isTo ? 10 : isCorridor ? 8.5 : 5.5;

            return (
              <CircleMarker
                key={node.node_id}
                center={[node.latitude, node.longitude]}
                radius={radius}
                eventHandlers={{
                  click: () => {
                    if (appMode === 'find_path' && onSelectNode) {
                      onSelectNode(node.node_id);
                    }
                  },
                }}
                pathOptions={{
                  fillColor: fillColor,
                  color: isFrom ? '#34d399' : isTo ? '#fda4af' : isCorridor ? '#ffffff' : '#0f172a',
                  weight: isFrom || isTo ? 3.5 : isCorridor ? 2.5 : 1.5,
                  fillOpacity: 0.95,
                }}
              >
                <Popup>
                  <div className="p-1 text-xs text-slate-900 min-w-[170px] font-sans">
                    <div className="font-bold">{node.name}</div>
                    <div className="text-[11px] text-slate-600 font-mono">Node ID: {node.node_id}</div>
                    <div className="text-[11px] mt-1">
                      Signal:{' '}
                      <span className="font-semibold uppercase text-emerald-700">
                        {isCorridor ? 'PRIORITY GREEN WAVE' : node.signal_state}
                      </span>
                    </div>

                    {appMode === 'find_path' && onSelectNode ? (
                      <div className="mt-2 space-y-1">
                        <button
                          onClick={() => onSelectNode(node.node_id)}
                          className="w-full py-1 px-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[10px] uppercase tracking-wider"
                        >
                          Select as {selectionTarget === 'to' ? 'Destination (TO)' : 'Origin (FROM)'}
                        </button>
                      </div>
                    ) : (
                      onSimulateAtNode && (
                        <button
                          onClick={() => onSimulateAtNode(node.node_id)}
                          className="mt-2 w-full py-1 px-2 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-[10px] uppercase tracking-wider"
                        >
                          Simulate Incident Here
                        </button>
                      )
                    )}
                  </div>
                </Popup>
                <Tooltip direction="top" offset={[0, -5]}>
                  <div className="text-xs font-sans">
                    <span className="font-bold">{node.name}</span> ({node.node_id})
                    {isFrom && <div className="text-emerald-400 font-bold">🟢 ORIGIN (FROM)</div>}
                    {isTo && <div className="text-rose-400 font-bold">🔴 DESTINATION (TO)</div>}
                    {isCorridor && (
                      <div className="text-[10px] text-emerald-400">🟢 GREEN CORRIDOR</div>
                    )}
                  </div>
                </Tooltip>
              </CircleMarker>
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
          <span>Route Overlays</span>
        </label>
        {appMode === 'scenario' && (
          <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
            <input
              type="checkbox"
              checked={showUnits}
              onChange={(e) => setShowUnits(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
            />
            <span>Emergency Fleet</span>
          </label>
        )}
        <label className="flex items-center space-x-2 cursor-pointer text-slate-300 hover:text-white">
          <input
            type="checkbox"
            checked={showSignals}
            onChange={(e) => setShowSignals(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0"
          />
          <span>Intersections</span>
        </label>
      </div>

      {/* Map Legend Floating Control */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-lg px-3 py-2 shadow-2xl text-[11px] flex flex-wrap items-center gap-3">
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#10b981] rounded-full"></div>
          <span className="text-slate-300">Free Flow</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#f59e0b] rounded-full"></div>
          <span className="text-slate-300">Moderate/Heavy</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#ef4444] rounded-full"></div>
          <span className="text-slate-300">Severe / Blocked</span>
        </div>
        {appMode === 'find_path' ? (
          <>
            <div className="flex items-center space-x-1.5">
              <div className="w-3.5 h-1.5 bg-[#06b6d4] rounded-full shadow-[0_0_6px_#06b6d4]"></div>
              <span className="text-cyan-300 font-semibold">Optimised (A*)</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3.5 h-1.5 bg-[#f59e0b] border-dashed rounded-full"></div>
              <span className="text-amber-300 font-semibold">Baseline (Distance)</span>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#06b6d4] rounded-full shadow-[0_0_6px_#06b6d4]"></div>
              <span className="text-cyan-300 font-semibold">Primary Corridor</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#f59e0b] border-dashed rounded-full"></div>
              <span className="text-amber-300 font-semibold">Alternative Route</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
