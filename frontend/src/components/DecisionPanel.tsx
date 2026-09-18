import type { WorldState } from '../types/world';

export default function DecisionPanel({ state }: { state: WorldState }) {
  const latest = state.decisions[state.decisions.length - 1];
  const group = latest ? state.groups[latest.group_id] : undefined;
  const destination = latest?.selected_destination ? state.nodes[latest.selected_destination] : undefined;
  const change = latest?.route_change;
  const rejected = latest?.rejected_routes?.[0];

  const decisionTitle = latest
    ? `${latest.decision_type.replaceAll('_', ' ')} ${group?.label ?? latest.group_id}${destination ? ` → ${destination.name}` : ''}`
    : 'Awaiting decision';

  const selectedScore = latest && latest.utility_scores && Object.keys(latest.utility_scores).length
    ? Math.max(...Object.values(latest.utility_scores))
    : 0;

  return (
    <section className="panel decision-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">LIVE AI DECISION</div>
          <h2>Utility agent</h2>
        </div>
        <span className="live-pill">{state.no_safe_route ? 'NO SAFE ROUTE' : 'LIVE'}</span>
      </div>

      {state.operator_intervention_required && (
        <div className="failsafe">NO SAFE ROUTE AVAILABLE — OPERATOR INTERVENTION REQUIRED</div>
      )}

      {latest ? (
        <>
          <div className="decision-headline">{decisionTitle}</div>

          <div className="decision-main">
            <div><span className="muted">Trigger</span><strong>{latest.trigger.replaceAll('_', ' ')}</strong></div>
            <div><span className="muted">Utility</span><strong>{selectedScore.toFixed(2)}</strong></div>
            <div><span className="muted">Safety</span><strong>{(latest.candidate_routes[0]?.components.hazard_exposure ?? 0) < 0.4 ? 'LOW RISK' : 'ELEVATED'}</strong></div>
            <div><span className="muted">Congestion</span><strong>{Math.round((latest.candidate_routes[0]?.predicted_congestion ?? 0) * 100)}%</strong></div>
          </div>

          <div className="reason-box">
            <div className="reason-title">WHY</div>
            <p>{latest.reason || 'No additional rationale was supplied by the planner.'}</p>
            <div className="reason-title">SITUATION</div>
            <p>{latest.situation || latest.trigger}</p>
            {rejected && (
              <>
                <div className="reason-title">REJECTED OPTION</div>
                <p>{state.nodes[rejected.destination]?.name ?? rejected.destination} — {rejected.rejection_reason ?? 'Not feasible for the current world state.'}</p>
              </>
            )}
          </div>

          <div className="factor-grid">
            <div className="factor"><span>Selected destination</span><b>{destination?.name ?? '—'}</b></div>
            <div className="factor"><span>Decision result</span><b>{latest.result}</b></div>
            <div className="factor"><span>Latency</span><b>{latest.latency_ms.toFixed(0)} ms</b></div>
          </div>

          {change && change.previous_destination && change.new_destination !== change.previous_destination && (
            <div className="route-change">
              <div className="reason-title">ROUTE CHANGE DETECTED</div>
              <p>Previous {state.nodes[change.previous_destination]?.name ?? change.previous_destination} → New {state.nodes[change.new_destination ?? '']?.name ?? change.new_destination}</p>
              <p>{change.why}</p>
              <p>Expected delay delta: {change.delay_delta_seconds.toFixed(0)}s</p>
            </div>
          )}
        </>
      ) : (
        <div className="empty-state">No agent decision yet. Start or inject an event to prime the planner.</div>
      )}
    </section>
  );
}
