import React, { useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Marker,
  Popup,
  Tooltip,
  useMapEvents,
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
  IntersectionNode,
  FindPathResult,
} from '../types';
import { Layers, ShieldAlert, Navigation, Car, AlertTriangle, Compass, CheckCircle2 } from 'lucide-react';

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
  const isMoving = status === 'dispatched' || status === 'en_route' || status === 'transporting' || status === 'returning';
  const isStaged = status === 'loading' || status === 'at_hospital' || status === 'on_scene';
  const borderColor = 
    status === 'transporting' ? '#14b8a6' :
    status === 'returning' ? '#818cf8' :
    isMoving ? '#06b6d4' :
    isStaged ? '#f59e0b' : '#10b981';
  const pulseClass = (isMoving || isStaged) ? 'animate-pulse' : '';

  return L.divIcon({
    className: 'custom-unit-icon',
    html: `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-slate-900 border-2 ${pulseClass}" style="border-color: ${borderColor}; box-shadow: 0 0 14px ${borderColor}90;">
        <span class="text-sm select-none">${iconEmoji}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Dynamic Incident Pin Icon (Accident vs Fire)
const createIncidentIcon = (scenarioType?: string, incidentType?: string) => {
  const isFire = (scenarioType || '').toLowerCase() === 'fire' || (incidentType || '').toLowerCase().includes('fire');
  const pingColor = isFire ? 'bg-orange-500/50' : 'bg-rose-500/50';
  const bgColor = isFire ? 'bg-orange-600' : 'bg-rose-600';
  const emoji = isFire ? '🔥' : '⚠️';

  return L.divIcon({
    className: 'custom-incident-icon',
    html: `
      <div class="relative flex items-center justify-center w-10 h-10">
        <div class="absolute inset-0 rounded-full ${pingColor} animate-ping"></div>
        <div class="relative flex items-center justify-center w-8 h-8 rounded-full ${bgColor} border-2 border-white shadow-xl text-white">
          <span class="text-sm font-black select-none">${emoji}</span>
        </div>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
};

// Point Selection Marker Icons (FROM = A, TO = B)
const createPointMarkerIcon = (label: 'A' | 'B', color: string) => {
  return L.divIcon({
    className: 'custom-point-marker',
    html: `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full shadow-2xl border-2 border-white text-xs font-black text-white" style="background-color: ${color}; box-shadow: 0 0 15px ${color};">
        <span>${label}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Custom Animated Route Vehicle Icon (Cyan = Optimised, Amber = Baseline)
const createRouteVehicleIcon = (color: string, label: string) => {
  return L.divIcon({
    className: 'custom-route-vehicle',
    html: `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full shadow-2xl border-2 border-white text-xs font-bold text-white transition-transform" style="background-color: ${color}; box-shadow: 0 0 16px ${color};">
        <span class="text-sm select-none">${label}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

interface CityMapProps {
  cityGraph: CityGraph;
  activeIncident: IncidentRecord | null;
  emergencyUnits: EmergencyUnit[];
  activeRoutes?: RouteResult[];
  emergencyRoute?: RouteResult | null;
  diversionRoute?: RouteResult | null;
  activeCorridorNodes: string[];
  // Find Path Mode props
  isFindPathMode?: boolean;
  fromNode?: IntersectionNode | null;
  toNode?: IntersectionNode | null;
  onMapNodeClick?: (node: IntersectionNode) => void;
  findPathOptimised?: FindPathResult | null;
  findPathBaseline?: FindPathResult | null;
  // Route animation states
  animProgressOpt?: number; // 0.0 to 1.0
  animProgressBase?: number; // 0.0 to 1.0
  animPosOpt?: [number, number] | null;
  animPosBase?: [number, number] | null;
  baseBlockedPause?: boolean;
}

// Map Click Listener component that finds nearest node and tracks zoom
const MapEventsHandler: React.FC<{
  nodes: IntersectionNode[];
  onNodeSelect?: (node: IntersectionNode) => void;
  enabled: boolean;
  onZoomChange: (zoom: number) => void;
}> = ({ nodes, onNodeSelect, enabled, onZoomChange }) => {
  useMapEvents({
    click(e) {
      if (!enabled || !nodes.length || !onNodeSelect) return;
      const { lat, lng } = e.latlng;
      let nearest = nodes[0];
      let minSqDist = (nearest.latitude - lat) ** 2 + (nearest.longitude - lng) ** 2;

      for (let i = 1; i < nodes.length; i++) {
        const n = nodes[i];
        const sqDist = (n.latitude - lat) ** 2 + (n.longitude - lng) ** 2;
        if (sqDist < minSqDist) {
          minSqDist = sqDist;
          nearest = n;
        }
      }
      onNodeSelect(nearest);
    },
    zoomend(e) {
      onZoomChange(e.target.getZoom());
    },
  });
  return null;
};

export const CityMap: React.FC<CityMapProps> = ({
  cityGraph,
  activeIncident,
  emergencyUnits,
  activeRoutes,
  emergencyRoute,
  diversionRoute,
  activeCorridorNodes,
  isFindPathMode = false,
  fromNode = null,
  toNode = null,
  onMapNodeClick,
  findPathOptimised = null,
  findPathBaseline = null,
  animProgressOpt = 0.0,
  animProgressBase = 0.0,
  animPosOpt = null,
  animPosBase = null,
  baseBlockedPause = false,
}) => {
  const [showCongestion, setShowCongestion] = useState(true);
  const [showSignals, setShowSignals] = useState(true);
  const [showUnits, setShowUnits] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);
  const [currentZoom, setCurrentZoom] = useState<number>(14);

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

  // Distinct Route Styling per Unit Type
  const getRouteStyle = (route: RouteResult) => {
    const uType = (route.unit_type || '').toLowerCase();
    const kind = (route.route_kind || '').toLowerCase();

    if (kind === 'transport_hospital') {
      return {
        color: '#14b8a6', // Teal for hospital transport
        weight: 5.5,
        dashArray: '8, 4',
        opacity: 0.95,
        lineCap: 'round' as const,
        lineJoin: 'round' as const,
      };
    }
    if (uType === 'ambulance') {
      return {
        color: '#06b6d4', // Cyan for ambulance
        weight: 6,
        opacity: 0.95,
        lineCap: 'round' as const,
        lineJoin: 'round' as const,
      };
    }
    if (uType === 'fire_engine' || uType === 'fire_truck') {
      return {
        color: '#f97316', // Orange-red for fire engine
        weight: 6,
        opacity: 0.95,
        lineCap: 'round' as const,
        lineJoin: 'round' as const,
      };
    }
    if (uType === 'police_patrol') {
      return {
        color: '#3b82f6', // Royal blue for police
        weight: 4.5,
        dashArray: '8, 4',
        opacity: 0.95,
        lineCap: 'round' as const,
        lineJoin: 'round' as const,
      };
    }
    return {
      color: '#06b6d4',
      weight: 5,
      opacity: 0.95,
      lineCap: 'round' as const,
      lineJoin: 'round' as const,
    };
  };

  // Combined routes list
  const displayRoutes: RouteResult[] =
    activeRoutes && activeRoutes.length > 0
      ? activeRoutes
      : emergencyRoute
      ? [emergencyRoute]
      : [];

  return (
    <div className="relative w-full h-full bg-[#090d16] overflow-hidden">
      <MapContainer
        center={defaultCenter}
        zoom={14}
        zoomControl={true}
        className="w-full h-full"
      >
        {/* Dark Matter Base Tiles */}
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
          className="dark-tiles"
        />

        {/* Map Click & Zoom Handler */}
        <MapEventsHandler
          nodes={cityGraph.nodes}
          onNodeSelect={isFindPathMode ? onMapNodeClick : undefined}
          enabled={isFindPathMode}
          onZoomChange={(z) => setCurrentZoom(z)}
        />

        {/* 1. Road Network Congestion Layer */}
        {showCongestion &&
          cityGraph.edges.map((edge) => {
            const p1 = getNodeCoord(edge.source_node);
            const p2 = getNodeCoord(edge.target_node);
            const positions: [number, number][] =
              edge.geometry && edge.geometry.length > 0
                ? (edge.geometry as [number, number][])
                : p1 && p2
                ? [p1, p2]
                : [];
            if (positions.length === 0) return null;

            return (
              <Polyline
                key={edge.road_id}
                positions={positions}
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

        {/* 2. Dispatched Emergency Unit Routes (Distinct styles per unit type) */}
        {showRoutes &&
          displayRoutes.map((route) => {
            if (!route.coordinates || route.coordinates.length < 2) return null;
            const style = getRouteStyle(route);
            const isAmb = (route.unit_type || '').toLowerCase() === 'ambulance';
            const isFire = (route.unit_type || '').toLowerCase().includes('fire');
            const isPol = (route.unit_type || '').toLowerCase().includes('police');
            const isHosp = (route.route_kind || '').toLowerCase() === 'transport_hospital';
            const icon = isHosp ? '🏥' : isFire ? '🚒' : isPol ? '🚓' : '🚑';
            const title = isHosp
              ? 'Patient Transport to Hospital'
              : `${route.unit_id || 'Emergency'} A* Response Route`;

            return (
              <Polyline
                key={route.route_id}
                positions={route.coordinates.map((c) => [c.latitude, c.longitude])}
                pathOptions={style}
              >
                <Popup>
                  <div className="p-1 text-xs">
                    <div className="font-bold flex items-center space-x-1" style={{ color: style.color }}>
                      <span>{icon}</span>
                      <span>{title}</span>
                    </div>
                    <div>
                      ETA: <strong>{route.estimated_travel_time_minutes} min</strong> ({route.estimated_travel_time_seconds}s)
                    </div>
                    <div>Distance: {route.total_distance_meters}m</div>
                    <div className="text-[10px] text-slate-400 mt-1">{route.explanation}</div>
                  </div>
                </Popup>
              </Polyline>
            );
          })}

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
            // Render dots only for signalised / major intersections or when zoomed in (>= 15) to avoid clutter
            const isMajor = node.is_signalized || isCorridor || node.node_id in ['INT-01', 'INT-02', 'INT-03', 'INT-04', 'INT-05', 'INT-07', 'INT-11', 'INT-13'];
            if (!isCorridor && !isMajor && currentZoom < 15) {
              return null;
            }

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

        {/* 5. Active Incident Pin (Accident ⚠️ vs Fire 🔥) */}
        {activeIncident && (
          <Marker
            position={[activeIncident.latitude, activeIncident.longitude]}
            icon={createIncidentIcon(activeIncident.scenario_type, activeIncident.incident_type)}
          >
            <Popup autoPan={false}>
              <div className="p-1 max-w-[220px]">
                <div className="flex items-center space-x-1.5 text-rose-500 font-bold text-xs uppercase">
                  <span>{(activeIncident.scenario_type || '').toLowerCase() === 'fire' ? '🔥' : '⚠️'}</span>
                  <span>{activeIncident.scenario_type ? activeIncident.scenario_type.toUpperCase() : activeIncident.incident_type}</span>
                </div>
                <div className="text-xs font-semibold text-slate-200 mt-1">{activeIncident.title}</div>
                <div className="text-[11px] text-slate-300 mt-1">
                  Status: <span className="font-bold text-amber-400 uppercase">{activeIncident.status}</span>
                </div>
                {activeIncident.patient_count !== undefined && activeIncident.patient_count > 0 && (
                  <div className="text-[11px] text-rose-400 font-semibold mt-0.5">
                    Patients: <strong>{activeIncident.patient_count}</strong>
                  </div>
                )}
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Heuristic Score: <strong>{activeIncident.heuristic_score}</strong>
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* 6. Emergency Units (Ambulance, Fire, Police) */}
        {!isFindPathMode && showUnits &&
          emergencyUnits.map((unit) => (
            <Marker
              key={unit.unit_id}
              position={[unit.latitude, unit.longitude]}
              icon={createUnitIcon(unit.unit_type, unit.status)}
            >
              <Tooltip direction="bottom" offset={[0, 10]}>
                <div className="text-xs space-y-0.5">
                  <div className="font-bold text-slate-100">{unit.call_sign} ({unit.unit_id})</div>
                  <div>
                    State: <span className="uppercase font-semibold text-amber-300">{unit.status.replace('_', ' ')}</span>
                  </div>
                  {unit.patient_count !== undefined && unit.patient_count > 0 && (
                    <div className="text-rose-400 font-bold">
                      Patients: {unit.patient_count}
                    </div>
                  )}
                  {unit.status === 'on_scene' && (
                    <div className="text-emerald-400 font-semibold text-[10px]">
                      {(unit as any).subphase_name
                        ? (unit as any).subphase_name.replace(/_/g, ' ').toUpperCase()
                        : 'On Scene Operations'}
                    </div>
                  )}
                  {unit.status === 'loading' && (
                    <div className="text-amber-400 font-semibold text-[10px]">Loading patient(s)...</div>
                  )}
                  {unit.status === 'at_hospital' && (
                    <div className="text-teal-400 font-semibold text-[10px]">At hospital ER transfer</div>
                  )}
                  {unit.eta_seconds !== undefined && unit.eta_seconds !== null && (unit.status === 'en_route' || unit.status === 'transporting' || unit.status === 'returning') && (
                    <div className="text-cyan-400 font-semibold text-[10px]">
                      ETA: {unit.eta_seconds > 60 ? `~${Math.round(unit.eta_seconds / 60)} min` : `${Math.round(unit.eta_seconds)}s`}
                    </div>
                  )}
                  {unit.status === 'available' && (
                    <div className="text-slate-400 text-[10px]">Standby at {unit.station_node}</div>
                  )}
                </div>
              </Tooltip>
            </Marker>
          ))}

        {/* 7. Find Path Mode: FROM & TO Markers */}
        {isFindPathMode && fromNode && (
          <Marker
            position={[fromNode.latitude, fromNode.longitude]}
            icon={createPointMarkerIcon('A', '#10b981')}
          >
            <Tooltip direction="top" offset={[0, -12]} permanent>
              <div className="text-xs font-bold text-emerald-400 bg-slate-900 px-1 py-0.5 rounded border border-emerald-500/50">
                FROM: {fromNode.name}
              </div>
            </Tooltip>
          </Marker>
        )}

        {isFindPathMode && toNode && (
          <Marker
            position={[toNode.latitude, toNode.longitude]}
            icon={createPointMarkerIcon('B', '#6366f1')}
          >
            <Tooltip direction="top" offset={[0, -12]} permanent>
              <div className="text-xs font-bold text-indigo-400 bg-slate-900 px-1 py-0.5 rounded border border-indigo-500/50">
                TO: {toNode.name}
              </div>
            </Tooltip>
          </Marker>
        )}

        {/* 8. Find Path Mode: Baseline Route (Dashed amber/orange line with travelled part solid) */}
        {isFindPathMode && findPathBaseline && findPathBaseline.geometry && findPathBaseline.geometry.length > 1 && (
          <>
            {/* Background / Remaining Faded Route */}
            <Polyline
              positions={findPathBaseline.geometry}
              pathOptions={{
                color: '#f59e0b',
                weight: 5,
                dashArray: '8, 8',
                opacity: animProgressBase > 0 ? 0.35 : 0.9,
                lineCap: 'round',
              }}
            />
            {/* Solid Travelled Portion */}
            {animProgressBase > 0 && (
              <Polyline
                positions={findPathBaseline.geometry.slice(
                  0,
                  Math.max(2, Math.floor(findPathBaseline.geometry.length * animProgressBase) + 1)
                )}
                pathOptions={{
                  color: '#f59e0b',
                  weight: 5,
                  opacity: 0.95,
                  lineCap: 'round',
                }}
              />
            )}
          </>
        )}

        {/* 9. Find Path Mode: Optimised Route (Thick cyan line with travelled part solid) */}
        {isFindPathMode && findPathOptimised && findPathOptimised.geometry && findPathOptimised.geometry.length > 1 && (
          <>
            {/* Background / Remaining Faded Route */}
            <Polyline
              positions={findPathOptimised.geometry}
              pathOptions={{
                color: '#06b6d4',
                weight: 7,
                opacity: animProgressOpt > 0 ? 0.35 : 0.95,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
            {/* Solid Travelled Portion */}
            {animProgressOpt > 0 && (
              <Polyline
                positions={findPathOptimised.geometry.slice(
                  0,
                  Math.max(2, Math.floor(findPathOptimised.geometry.length * animProgressOpt) + 1)
                )}
                pathOptions={{
                  color: '#06b6d4',
                  weight: 7,
                  opacity: 1.0,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
              />
            )}
          </>
        )}

        {/* 10. Find Path Mode: Animated Vehicle Markers */}
        {isFindPathMode && animPosOpt && (
          <Marker
            position={animPosOpt}
            icon={createRouteVehicleIcon('#06b6d4', '⚡')}
          >
            <Tooltip direction="top" offset={[0, -10]} permanent>
              <div className="text-[10px] font-bold text-cyan-300 bg-slate-950 px-1 py-0.5 rounded border border-cyan-500/50">
                A* Optimised ({Math.round(animProgressOpt * 100)}%)
              </div>
            </Tooltip>
          </Marker>
        )}

        {isFindPathMode && animPosBase && (
          <Marker
            position={animPosBase}
            icon={createRouteVehicleIcon('#f59e0b', '🧭')}
          >
            <Tooltip direction="top" offset={[0, -10]} permanent>
              <div className={`text-[10px] font-bold bg-slate-950 px-1 py-0.5 rounded border ${
                baseBlockedPause ? 'text-rose-400 border-rose-500 animate-pulse' : 'text-amber-300 border-amber-500/50'
              }`}>
                {baseBlockedPause ? '⚠️ Blocked — Rerouting delay' : `Baseline (${Math.round(animProgressBase * 100)}%)`}
              </div>
            </Tooltip>
          </Marker>
        )}
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
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-lg px-3 py-2.5 shadow-2xl text-[11px] flex flex-wrap items-center gap-3">
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#10b981] rounded-full"></div>
          <span className="text-slate-300">Free Flow</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-3 h-1 bg-[#ef4444] rounded-full"></div>
          <span className="text-slate-300">Blocked / Jam</span>
        </div>
        {isFindPathMode ? (
          <>
            <div className="flex items-center space-x-1.5">
              <div className="w-3.5 h-1.5 bg-[#06b6d4] rounded-full shadow-[0_0_8px_#06b6d4]"></div>
              <span className="text-cyan-300 font-bold">⚡ Optimised (Cyan)</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3.5 h-1.5 bg-[#f59e0b] border border-dashed rounded-full"></div>
              <span className="text-amber-300 font-bold">🧭 Baseline (Dashed)</span>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#06b6d4] rounded-full shadow-[0_0_6px_#06b6d4]"></div>
              <span className="text-cyan-300 font-semibold">🚑 Ambulance</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#f97316] rounded-full shadow-[0_0_6px_#f97316]"></div>
              <span className="text-orange-300 font-semibold">🚒 Fire Truck</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#3b82f6] border-dashed rounded-full shadow-[0_0_6px_#3b82f6]"></div>
              <span className="text-blue-300 font-semibold">🚓 Police</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#14b8a6] border-dashed rounded-full"></div>
              <span className="text-teal-300 font-semibold">🏥 Transport</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-3 h-1 bg-[#a855f7] border-dashed rounded-full"></div>
              <span className="text-purple-300 font-semibold">Diversion</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
