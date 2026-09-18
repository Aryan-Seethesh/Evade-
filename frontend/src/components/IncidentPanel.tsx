import type { WorldState } from '../types/world';

export default function IncidentPanel({ state }: { state: WorldState }) {
  const loc = state.incident.location ? state.nodes[state.incident.location]?.name : '—';
  // This is instantaneous incident severity, not cumulative person-exposure.
  // The latter remains available as its own metric in the dashboard.
  const activeHazards = Object.values(state.hazards).filter((hazard) => hazard.active);
  const riskValue = activeHazards.length
    ? Math.round((activeHazards.reduce((sum, hazard) => sum + hazard.severity, 0) / activeHazards.length) * 100)
    : 0;

  return (
    <section className="panel incident-panel">
      <div className="panel-heading compact-head">
        <div>
          <div className="eyebrow">ACTIVE INCIDENT</div>
          <h2>{state.incident.name === 'NONE' ? 'System clear' : state.incident.name}</h2>
        </div>
        <div className={`risk-badge ${state.incident.severity.toLowerCase()}`}>{state.incident.severity}</div>
      </div>

      <div className="incident-summary">
        <div>
          <p className="summary-label">Current status</p>
          <p className="summary-value">{state.incident.message || 'No active incident in the campus model.'}</p>
        </div>
        <div className="risk-meter">
          <div className="risk-meter-header">
            <span>Active hazard severity</span>
            <strong>{riskValue}%</strong>
          </div>
          <div className="risk-track">
            <div className={`risk-fill ${state.incident.severity.toLowerCase()}`} style={{ width: `${riskValue}%` }} />
          </div>
        </div>
      </div>

      <div className="incident-bars">
        <div><span>Location</span><b>{loc}</b></div>
        <div><span>Affected zones</span><b>{state.incident.affected_zones}</b></div>
        <div><span>Evacuation</span><b>{state.incident.evacuation}</b></div>
        <div><span>Data quality</span><b>{state.data_quality}</b></div>
      </div>
    </section>
  );
}
