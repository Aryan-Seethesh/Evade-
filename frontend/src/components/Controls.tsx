import type { WorldState } from '../types/world';

const EVENTS = [
  { label: 'Trigger Fire', type: 'FIRE_DETECTED', target: 'building_b', cls: 'danger' },
  { label: 'Spread Smoke', type: 'HAZARD_SPREAD', target: 'j_north', cls: 'warning' },
  { label: 'Block Exit A', type: 'EXIT_BLOCKED', target: 'exit_north', cls: 'danger' },
  { label: 'Block Route', type: 'ROUTE_BLOCKED', target: 'e_js_je', cls: 'warning' },
  { label: 'Increase Crowd', type: 'CROWD_SURGE', target: 'exit_south', value: 220, cls: 'warning' },
  { label: 'Flood Route', type: 'FLOOD_DETECTED', target: 'e_js_quad', cls: 'warning' },
  { label: 'Send Fire Truck', type: 'EMERGENCY_VEHICLE_APPROACHING', target: 'fire-truck-1', cls: 'accent' },
  { label: 'Send Ambulance', type: 'EMERGENCY_VEHICLE_APPROACHING', target: 'ambulance-1', cls: 'accent' },
  { label: 'Create Corridor', type: 'EMERGENCY_CORRIDOR_CREATED', target: 'fire-truck-1', cls: 'accent' },
  { label: 'Open Exit A', type: 'EXIT_REOPENED', target: 'exit_north', cls: '' },
  { label: 'Resolve Hazard', type: 'HAZARD_RESOLVED', target: 'building_b', cls: '' },
];

const SPEEDS = [0.5, 1, 2, 5, 10];

export default function Controls({
  state,
  run,
}: {
  state: WorldState;
  run: (path: string, body?: unknown) => Promise<void>;
}) {
  const id = state.id || 'default';
  const groups = Object.values(state.groups);
  const exits = Object.values(state.nodes).filter((n) => n.type === 'EXIT');

  return (
    <section className="panel controls-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">SCENARIO CONTROL CENTER</div>
          <h2>Simulation Controls</h2>
        </div>
      </div>

      <div className="control-row main-controls">
        <button className="btn primary" onClick={() => run(`/api/simulations/${id}/start`)}>Start</button>
        <button className="btn" onClick={() => run(`/api/simulations/${id}/pause`)}>Pause</button>
        <button className="btn" onClick={() => run(`/api/simulations/${id}/resume`)}>Resume</button>
        <button className="btn" onClick={() => run(`/api/simulations/${id}/reset`)}>Reset</button>
        <button className="btn accent" onClick={() => run(`/api/simulations/${id}/demo`)}>Demo Mode</button>
      </div>

      <div className="speed-pills">
        <span>Speed</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            className={`btn ${state.simulation_speed === s ? 'primary' : ''}`}
            onClick={() => run(`/api/simulations/${id}/speed`, { speed: s })}
          >
            {s}×
          </button>
        ))}
      </div>

      <div className="control-grid">
        {EVENTS.map((ev) => (
          <button
            key={ev.label}
            className={`btn ${ev.cls}`}
            onClick={() => run(`/api/simulations/${id}/events`, { event_type: ev.type, target_id: ev.target, value: ev.value })}
          >
            {ev.label}
          </button>
        ))}
      </div>

      {groups.length > 0 && (
        <form
          className="override-row"
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const group = (form.elements.namedItem('group') as HTMLSelectElement).value;
            const destination = (form.elements.namedItem('dest') as HTMLSelectElement).value;
            run(`/api/simulations/${id}/override`, { group_id: group, destination, reason: 'Operator override from dashboard' });
          }}
        >
          <span>Operator override</span>
          <select name="group">{groups.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}</select>
          <select name="dest">{exits.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}</select>
          <button className="btn" type="submit">Assign</button>
        </form>
      )}
    </section>
  );
}
