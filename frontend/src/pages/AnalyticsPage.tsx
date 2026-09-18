import { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar } from 'recharts';
import { getLatestBenchmark, runBenchmark } from '../lib/api';
import { useSim } from '../hooks/simContext';
import type { BenchmarkResult } from '../types/world';
import MetricCard from '../components/MetricCard';

export default function AnalyticsPage() {
  const { state } = useSim();
  const [bench, setBench] = useState<BenchmarkResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getLatestBenchmark().then(setBench).catch(() => undefined);
  }, []);

  const history = state.metrics_history.map((p) => ({
    t: p.sim_time,
    evacuated: p.evacuated,
    congestion: Math.round(p.congestion * 100),
    predicted: Math.round(p.predicted_congestion * 100),
    risk: Math.round(p.risk * 100),
  }));

  const exits = Object.values(state.nodes).filter((n) => n.type === 'EXIT').map((n) => ({
    name: n.name.replace('Exit ', ''),
    util: Math.round((n.occupancy / Math.max(n.capacity, 1)) * 100),
  }));

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setBench(await runBenchmark(state.seed));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Benchmark failed');
    } finally {
      setBusy(false);
    }
  };

  const m = state.metrics;
  return (
    <main className="content">
      <div className="eyebrow">EXPERIMENT / ANALYTICS</div>
      <h1>Measured performance</h1>
      <p className="lede">Values come from the live simulation and from paired baseline vs EVADE-AI runs on the same seed. Incomplete runs report the horizon time, not a fabricated 100% success rate.</p>

      <div className="metrics-grid">
        <MetricCard label="Evacuation time" value={`${m.evacuation_time.toFixed(0)}s`} />
        <MetricCard label="Completion" value={`${Math.round(m.completion_rate * 100)}%`} accent="green" />
        <MetricCard label="Peak congestion" value={`${Math.round(m.peak_congestion * 100)}%`} accent="amber" />
        <MetricCard label="Hazard exposure" value={m.hazard_exposure.toFixed(1)} accent="red" />
        <MetricCard label="Responder delay" value={`${m.responder_delay.toFixed(0)}s`} />
        <MetricCard label="Reroutes" value={`${m.reroutes}`} />
        <MetricCard label="Avg decision latency" value={`${m.avg_decision_latency_ms.toFixed(2)} ms`} accent="blue" />
        <MetricCard label="Avg tick time" value={`${m.avg_tick_time_ms.toFixed(2)} ms`} />
      </div>

      <div className="chart-grid">
        <section className="panel pad">
          <h2>Evacuation progress</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={history}>
              <CartesianGrid stroke="rgba(255,255,255,.08)" />
              <XAxis dataKey="t" stroke="#7a8ea3" />
              <YAxis stroke="#7a8ea3" />
              <Tooltip />
              <Line type="monotone" dataKey="evacuated" stroke="#57d58e" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
        <section className="panel pad">
          <h2>Congestion vs predicted</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={history}>
              <CartesianGrid stroke="rgba(255,255,255,.08)" />
              <XAxis dataKey="t" stroke="#7a8ea3" />
              <YAxis stroke="#7a8ea3" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="congestion" stroke="#f0ad55" dot={false} />
              <Line type="monotone" dataKey="predicted" stroke="#5ca3e8" dot={false} />
              <Line type="monotone" dataKey="risk" stroke="#ff6672" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
        <section className="panel pad">
          <h2>Exit utilization</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={exits}>
              <CartesianGrid stroke="rgba(255,255,255,.08)" />
              <XAxis dataKey="name" stroke="#7a8ea3" />
              <YAxis stroke="#7a8ea3" />
              <Tooltip />
              <Bar dataKey="util" fill="#5ca3e8" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="panel pad">
        <div className="panel-heading">
          <h2>Static baseline vs EVADE-AI</h2>
          <button className="btn primary" disabled={busy} onClick={run}>{busy ? 'Running…' : 'Run benchmark'}</button>
        </div>
        {error && <div className="banner-error">{error}</div>}
        {bench && (
          <>
            <p className="lede">{bench.note} Wall time {bench.wall_time_ms} ms · seed {bench.seed}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Policy</th>
                    <th>Evac time</th>
                    <th>Complete</th>
                    <th>Peak cong.</th>
                    <th>Exposure</th>
                    <th>Reroutes</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {bench.scenarios.flatMap((s) => (
                    [
                      <tr key={`${s.scenario_id}-b`}>
                        <td rowSpan={2}>{s.name}</td>
                        <td>Static</td>
                        <td>{s.static_baseline.evacuation_time}</td>
                        <td>{Math.round(s.static_baseline.completion_rate * 100)}%</td>
                        <td>{Math.round(s.static_baseline.peak_congestion * 100)}%</td>
                        <td>{s.static_baseline.hazard_exposure}</td>
                        <td>{s.static_baseline.reroute_count}</td>
                        <td>{s.static_baseline.decision_latency_ms}</td>
                      </tr>,
                      <tr key={`${s.scenario_id}-a`}>
                        <td>EVADE-AI</td>
                        <td>{s.evade_ai.evacuation_time}</td>
                        <td>{Math.round(s.evade_ai.completion_rate * 100)}%</td>
                        <td>{Math.round(s.evade_ai.peak_congestion * 100)}%</td>
                        <td>{s.evade_ai.hazard_exposure}</td>
                        <td>{s.evade_ai.reroute_count}</td>
                        <td>{s.evade_ai.decision_latency_ms}</td>
                      </tr>,
                    ]
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
