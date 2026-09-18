import { Activity, Bot, Focus, ShieldAlert, TimerReset } from 'lucide-react';
import CampusMap from '../components/CampusMap';
import Controls from '../components/Controls';
import DecisionPanel from '../components/DecisionPanel';
import EventLog from '../components/EventLog';
import ExitStatus from '../components/ExitStatus';
import IncidentPanel from '../components/IncidentPanel';
import MetricCard from '../components/MetricCard';
import WorldInspector from '../components/WorldInspector';
import { useSim } from '../hooks/simContext';

function fmtClock(seconds: number): string {
  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

export default function Dashboard() {
  const { state, run } = useSim();
  const m = state.metrics;

  return (
    <main className="content command-shell">
      <div className="hero-row">
        <div>
          <div className="eyebrow">LIVE SITUATIONAL AWARENESS</div>
          <h1>{state.incident.name === 'NONE' ? 'Campus status — stable' : state.incident.name}</h1>
          <p>Observe the world, assess the risk, evaluate the utility, and replan the evacuation in real time.</p>
        </div>
        <div className="hero-right">
          <div className="hero-agent"><Bot size={18} /> {state.mode.replaceAll('_', ' ')}</div>
          <div className="status-chips">
            <span className="chip"><Activity size={12} /> {state.running ? 'LIVE' : 'PAUSED'}</span>
            <span className="chip"><Focus size={12} /> {state.no_safe_route ? 'ROUTE CRITICAL' : 'ROUTE STABLE'}</span>
            <span className="chip"><TimerReset size={12} /> T {fmtClock(state.sim_time)}</span>
          </div>
        </div>
      </div>

      <IncidentPanel state={state} />

      <div className="metrics-grid">
        <MetricCard label="Total people" value={`${Math.round(m.total_people ?? 0)}`} />
        <MetricCard label="Evacuated" value={`${Math.round(m.evacuated ?? 0)}`} accent="green" />
        <MetricCard label="At risk" value={`${Math.round(m.at_risk ?? 0)}`} accent="red" />
        <MetricCard label="In transit" value={`${Math.round(m.in_transit ?? 0)}`} accent="blue" />
        <MetricCard label="Peak congestion" value={`${Math.round((m.peak_congestion ?? 0) * 100)}%`} accent="amber" />
        <MetricCard label="Predicted congestion" value={`${Math.round((m.predicted_peak_congestion ?? 0) * 100)}%`} accent="amber" />
        <MetricCard label="Hazard exposure" value={`${m.hazard_exposure.toFixed(1)}`} accent="red" />
        <MetricCard label="Responders" value={`${Math.round(m.active_responders ?? 0)}`} />
        <MetricCard label="Reroutes" value={`${Math.round(m.reroutes ?? 0)}`} accent="red" />
        <MetricCard label="Decision latency" value={`${(m.avg_decision_latency_ms ?? 0).toFixed(1)} ms`} accent="blue" />
        <MetricCard label="Tick time" value={`${(m.avg_tick_time_ms ?? 0).toFixed(1)} ms`} />
        <MetricCard label="Completion" value={`${Math.round((m.completion_rate ?? 0) * 100)}%`} accent="green" />
      </div>

      <div className="main-grid">
        <section className="panel map-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">ENVIRONMENT / WORLD MODEL</div>
              <h2>Campus Emergency Map</h2>
            </div>
            <div className="map-live"><Activity size={16} /> LIVE STATE</div>
          </div>
          <CampusMap state={state} />
        </section>
        <DecisionPanel state={state} />
      </div>

      <div className="lower-grid">
        <Controls state={state} run={run} />
        <EventLog state={state} />
      </div>
      <div className="lower-grid">
        <ExitStatus state={state} />
        <WorldInspector state={state} />
      </div>
    </main>
  );
}
