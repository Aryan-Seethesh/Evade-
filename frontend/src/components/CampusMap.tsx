import type { WorldState } from '../types/world';

interface Props {
  state: WorldState;
}

type Point = { x: number; y: number };

function positionOnCurrentEdge(
  state: WorldState,
  currentEdge: string | null | undefined,
  progress: number,
  fallbackNode: string,
): Point | null {
  const edge = currentEdge ? state.edges[currentEdge] : undefined;
  const origin = edge ? state.nodes[edge.source] : state.nodes[fallbackNode];
  const target = edge ? state.nodes[edge.target] : undefined;
  if (!origin) return null;
  if (!target) return { x: origin.x, y: origin.y };
  const p = Math.max(0, Math.min(1, progress));
  return { x: origin.x + (target.x - origin.x) * p, y: origin.y + (target.y - origin.y) * p };
}

const riskClass = (level: string, open: boolean) =>
  `node risk-${level.toLowerCase()} ${open ? '' : 'node-closed'}`;

export default function CampusMap({ state }: Props) {
  const width = 900;
  const height = 540;
  const px = (x: number) => (x / 100) * width;
  const py = (y: number) => (y / 100) * height;

  const activeRoutes = Object.values(state.groups)
    .filter((g) => g.assigned_route.length > 1 && g.status === 'IN_TRANSIT')
    .map((g) => g.assigned_route);

  const corridorEdges = new Set(
    Object.values(state.corridors).filter((c) => c.active).flatMap((c) => c.edge_ids),
  );

  return (
    <div className="map-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} className="campus-map" role="img" aria-label="Campus evacuation map">
        <defs>
          <pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse">
            <path d="M 36 0 L 0 0 0 36" fill="none" stroke="rgba(255,255,255,.04)" strokeWidth="1" />
          </pattern>
          <radialGradient id="hazardGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255,80,70,.35)" />
            <stop offset="100%" stopColor="rgba(255,80,70,0)" />
          </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        {Object.values(state.edges).map((edge) => {
          const a = state.nodes[edge.source];
          const b = state.nodes[edge.target];
          if (!a || !b) return null;
          const blocked = !edge.open;
          const hot = edge.crowd_density > 0.55;
          const corridor = corridorEdges.has(edge.id) || edge.emergency_restricted;
          return (
            <line
              key={edge.id}
              x1={px(a.x)}
              y1={py(a.y)}
              x2={px(b.x)}
              y2={py(b.y)}
              className={`route ${blocked ? 'route-blocked' : ''} ${hot ? 'route-hot' : ''} ${corridor ? 'route-corridor' : ''}`}
              strokeWidth={5 + edge.crowd_density * 6}
            />
          );
        })}

        {activeRoutes.map((route, idx) => (
          <polyline
            key={`r-${idx}`}
            fill="none"
            className="assigned-route"
            points={route.map((id) => {
              const n = state.nodes[id];
              return n ? `${px(n.x)},${py(n.y)}` : '';
            }).join(' ')}
          />
        ))}

        {Object.values(state.hazards).filter((h) => h.active).map((hazard) => {
          const node = state.nodes[hazard.location];
          if (!node) return null;
          return <circle key={hazard.id} cx={px(node.x)} cy={py(node.y)} r={38 + hazard.severity * 24} fill="url(#hazardGlow)" />;
        })}

        {Object.values(state.groups).map((group) => {
          const location = positionOnCurrentEdge(state, group.current_edge, group.progress, group.current_node);
          if (!location) return null;
          return (
            <g key={group.id} transform={`translate(${px(location.x)}, ${py(location.y)})`}>
              <circle r={8 + Math.min(10, group.size / 80)} className={`people-marker ${group.status.toLowerCase()}`} />
              <text y="26" textAnchor="middle" className="group-label">{group.size}</text>
            </g>
          );
        })}

        {Object.values(state.nodes).map((node) => (
          <g key={node.id} transform={`translate(${px(node.x)}, ${py(node.y)})`}>
            <circle r={node.type === 'EXIT' ? 18 : node.type === 'BUILDING' ? 16 : 12} className={riskClass(node.hazard_level, node.open)} />
            <text textAnchor="middle" dy="4" className="node-icon">
              {node.type === 'EXIT' ? '↗' : node.type === 'SHELTER' || node.type === 'ASSEMBLY' ? '⌂' : node.type === 'BUILDING' ? '▦' : '•'}
            </text>
            <text y="28" textAnchor="middle" className="node-name">{node.name}</text>
          </g>
        ))}

        {Object.values(state.responders).map((responder) => {
          const location = positionOnCurrentEdge(state, responder.current_edge, responder.progress, responder.current_location);
          if (!location) return null;
          return (
            <g key={responder.id} transform={`translate(${px(location.x)}, ${py(location.y)})`}>
              <circle r="26" className="responder-ring" />
              <text textAnchor="middle" dy="5" className="responder-icon">{responder.type === 'AMBULANCE' ? '🚑' : '🚒'}</text>
            </g>
          );
        })}
      </svg>
      <div className="map-legend">
        <span><i className="legend-dot safe" /> Safe</span>
        <span><i className="legend-dot warning" /> Congestion</span>
        <span><i className="legend-dot danger" /> Hazard</span>
        <span><i className="legend-dot blocked" /> Blocked</span>
        <span><i className="legend-dot corridor" /> Corridor</span>
      </div>
    </div>
  );
}
