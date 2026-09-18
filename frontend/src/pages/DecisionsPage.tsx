import { useMemo, useState } from 'react';
import { useSim } from '../hooks/simContext';

export default function DecisionsPage() {
  const { state } = useSim();
  const [group, setGroup] = useState('');
  const [dtype, setDtype] = useState('');
  const [q, setQ] = useState('');

  const filtered = useMemo(() => {
    return [...state.decisions].reverse().filter((d) => {
      if (group && d.group_id !== group) return false;
      if (dtype && d.decision_type !== dtype) return false;
      if (q && !`${d.trigger} ${d.reason} ${d.situation}`.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [state.decisions, group, dtype, q]);

  return (
    <main className="content">
      <div className="eyebrow">AGENT DECISION HISTORY</div>
      <h1>Explainable routing decisions</h1>
      <div className="filter-row">
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">All groups</option>
          {Object.values(state.groups).map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
        </select>
        <select value={dtype} onChange={(e) => setDtype(e.target.value)}>
          <option value="">All types</option>
          {['ASSIGN', 'REROUTE', 'HOLD_ROUTE', 'NO_SAFE_ROUTE', 'FALLBACK'].map((t) => <option key={t}>{t}</option>)}
        </select>
        <input placeholder="Filter trigger / reason" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="decision-list">
        {filtered.map((d) => (
          <article key={d.decision_id} className="panel decision-card">
            <header>
              <b>DECISION {d.decision_id}</b>
              <span>t={d.sim_time.toFixed(1)}s · {d.decision_type} · {d.latency_ms.toFixed(2)} ms</span>
            </header>
            <p><b>Group:</b> {state.groups[d.group_id]?.label ?? d.group_id}</p>
            <p><b>Trigger:</b> {d.trigger}</p>
            <p><b>Situation:</b> {d.situation}</p>
            <p><b>Selected:</b> {d.selected_destination ? (state.nodes[d.selected_destination]?.name ?? d.selected_destination) : 'NONE'}</p>
            <p><b>Route:</b> {d.selected_route.join(' → ') || '—'}</p>
            <p><b>Reason:</b> {d.reason}</p>
            <p><b>Result:</b> {d.result}</p>
            {!!d.rejected_routes.length && (
              <p><b>Rejected:</b> {d.rejected_routes.map((r) => `${r.destination} (${r.rejection_reason})`).join('; ')}</p>
            )}
            {!!Object.keys(d.utility_scores).length && (
              <p><b>Utility:</b> {Object.entries(d.utility_scores).map(([k, v]) => `${k}: ${v.toFixed(1)}`).join(' · ')}</p>
            )}
          </article>
        ))}
        {!filtered.length && <div className="empty-state">No matching decisions.</div>}
      </div>
    </main>
  );
}
