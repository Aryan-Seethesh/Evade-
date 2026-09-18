import { useEffect, useState } from 'react';
import { getScenarios, postSim } from '../lib/api';
import { useSim } from '../hooks/simContext';
import type { ScenarioInfo } from '../types/world';

const PRESETS = [
  ['basic_fire', 'Basic Fire'],
  ['blocked_exit', 'Fire + Blocked Exit'],
  ['fire_congestion', 'Fire + Crowd Surge'],
  ['fire_responder', 'Fire + Emergency Vehicle'],
  ['multi_failure', 'Multi-Hazard'],
  ['flood', 'Flood'],
  ['campus_fire', 'Campus Fire (full demo)'],
];

export default function ScenariosPage() {
  const { setState } = useSim();
  const [items, setItems] = useState<ScenarioInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getScenarios().then(setItems).catch((err: Error) => setError(err.message));
  }, []);

  const load = async (id: string, demo = false) => {
    try {
      const state = await postSim('/api/simulations/default/load', { scenario_id: id, seed: 42, demo, mode: demo ? 'DEMO' : 'EVADE_AI' });
      setState(state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scenario');
    }
  };

  return (
    <main className="content">
      <div className="eyebrow">SCENARIO LIBRARY</div>
      <h1>Select a disaster sequence</h1>
      {error && <div className="banner-error">{error}</div>}
      <div className="scenario-grid">
        {PRESETS.map(([id, title]) => {
          const spec = items.find((s) => s.id === id);
          return (
            <article key={id} className="panel pad">
              <h2>{title}</h2>
              <p>{spec?.description ?? id}</p>
              <p className="muted">Events: {spec?.event_count ?? '—'}</p>
              <div className="control-row">
                <button className="btn primary" onClick={() => load(id)}>Load</button>
                <button className="btn accent" onClick={() => load(id, true)}>Load + Demo</button>
              </div>
            </article>
          );
        })}
      </div>
    </main>
  );
}
