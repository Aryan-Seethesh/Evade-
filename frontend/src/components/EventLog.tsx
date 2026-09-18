import type { WorldState } from '../types/world';

function fmt(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function EventLog({ state }: { state: WorldState }) {
  const items = [...state.timeline].slice(-18).reverse();
  return (
    <section className="panel log-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">EVENT TIMELINE</div>
          <h2>Operational log</h2>
        </div>
      </div>
      <div className="event-log">
        {items.map((ev) => (
          <div className="log-item" key={ev.id}>
            <div className="log-time">{fmt(ev.sim_time)}</div>
            <div className="log-content">
              <b>{ev.type.replaceAll('_', ' ')}</b>
              <span>{ev.message}</span>
            </div>
          </div>
        ))}
        {!items.length && <div className="empty-state">No events yet.</div>}
      </div>
    </section>
  );
}
