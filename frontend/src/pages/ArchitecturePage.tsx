const MODULES = [
  { id: 'sensors', title: 'Sensors', text: 'Smoke, temperature, crowd, CCTV, and infrastructure readings sampled from world state each tick. Failures mark sensors STALE/FAILED and degrade data quality.' },
  { id: 'perception', title: 'Perception', text: 'Normalizes sensor and event input into occupancy, hazard, and crowd features. Conflicting readings are flagged rather than silently trusted.' },
  { id: 'world', title: 'World Model', text: 'Canonical typed graph: nodes, edges, groups, hazards, responders, sensors, corridors, metrics. Frontend renders this object only.' },
  { id: 'risk', title: 'Risk Engine', text: 'Maps node/edge hazard, closures, and severity into RiskLevel. Critical hazard is a hard constraint, not a cost.' },
  { id: 'utility', title: 'Utility Decision Engine', text: 'UTILITY = safety + efficiency + accessibility − hazard − congestion − travel time − emergency conflict. Weights are configurable on WorldState.' },
  { id: 'planner', title: 'Dynamic Planner', text: 'NetworkX weighted shortest path under hard filters. Candidates compared by utility; infeasible options retained for explanation.' },
  { id: 'action', title: 'Actions', text: 'Route assignments, corridor reservation, operator override, alerts (NO SAFE ROUTE).' },
  { id: 'env', title: 'Environment', text: 'Tick advances time, movement, crowd density, sensors, scripted scenario events, then feedback into the world model.' },
];

export default function ArchitecturePage() {
  return (
    <main className="content">
      <div className="eyebrow">SYSTEM ARCHITECTURE</div>
      <h1>Utility-based intelligent agent</h1>
      <p className="lede">Type of agent: utility-based. Loop: Observe → Analyze → Decide → Act → Replan.</p>
      <div className="arch-flow">
        {MODULES.map((m, i) => (
          <div key={m.id} className="arch-node">
            <div className="arch-title">{m.title}</div>
            {i < MODULES.length - 1 && <div className="arch-arrow">↓</div>}
          </div>
        ))}
        <div className="arch-node"><div className="arch-title">Feedback</div></div>
      </div>
      <div className="scenario-grid">
        {MODULES.map((m) => (
          <article key={m.id} className="panel pad">
            <h2>{m.title}</h2>
            <p>{m.text}</p>
          </article>
        ))}
      </div>
      <section className="panel pad">
        <h2>PEAS</h2>
        <ul className="peas">
          <li><b>Performance:</b> evacuation time, hazard exposure, congestion, completion, emergency access, decision/tick latency.</li>
          <li><b>Environment:</b> campus buildings, paths, exits, shelters, people, hazards, responders, sensors.</li>
          <li><b>Actuators:</b> route assignments, corridor reservation, operator alerts, simulated gate/exit status.</li>
          <li><b>Sensors:</b> simulated smoke, temperature, crowd, CCTV, infrastructure, GPS-like group location.</li>
        </ul>
      </section>
    </main>
  );
}
