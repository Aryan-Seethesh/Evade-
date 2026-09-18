import type { WorldState } from '../types/world';

export default function WorldInspector({ state }: { state: WorldState }) {
  const snippet = {
    hazards: Object.values(state.hazards).map((h) => ({ id: h.id, type: h.type, location: h.location, severity: h.severity, active: h.active })),
    exits: Object.values(state.nodes).filter((n) => n.type === 'EXIT').map((n) => ({ id: n.id, open: n.open, occupancy: n.occupancy, hazard: n.hazard_level })),
    groups: Object.values(state.groups).map((g) => ({ id: g.id, node: g.current_node, dest: g.destination, status: g.status, route: g.assigned_route })),
    responders: Object.values(state.responders).map((r) => ({ id: r.id, loc: r.current_location, dest: r.destination, avail: r.availability, route: r.assigned_route })),
    routes: Object.values(state.edges).map((e) => ({ id: e.id, open: e.open, density: e.crowd_density, predicted: e.predicted_density, hazard: e.hazard_score, corridor: e.emergency_restricted })),
  };
  return (
    <section className="panel inspector-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">WORLD-STATE INSPECTOR</div>
          <h2>Canonical backend state</h2>
        </div>
      </div>
      <pre className="inspector">{JSON.stringify(snippet, null, 2)}</pre>
    </section>
  );
}
