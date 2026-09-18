import type { WorldState } from '../types/world';

export default function ExitStatus({ state }: { state: WorldState }) {
  const exits = Object.values(state.nodes).filter((n) => n.type === 'EXIT');
  return (
    <section className="panel exit-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">EXIT STATUS</div>
          <h2>Capacity & availability</h2>
        </div>
      </div>
      <div className="exit-list">
        {exits.map((exit) => {
          const pct = Math.min(100, Math.round((exit.occupancy / Math.max(exit.capacity, 1)) * 100));
          const closed = !exit.open || exit.hazard_level === 'CRITICAL';
          return (
            <div key={exit.id} className="exit-row">
              <div className="exit-meta">
                <b>{exit.name}</b>
                <span className={closed ? 'tag danger' : pct > 70 ? 'tag warn' : 'tag ok'}>
                  {closed ? 'CLOSED' : `${pct}%`}
                </span>
              </div>
              <div className="bar">
                <i style={{ width: `${closed ? 100 : pct}%` }} className={closed ? 'danger' : pct > 70 ? 'warn' : ''} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
