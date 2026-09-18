import { ShieldAlert } from 'lucide-react';
import { Outlet } from 'react-router-dom';
import Nav from '../components/Nav';
import { useSimulation } from '../hooks/useSimulation';
import { SimContext } from '../hooks/simContext';

function fmt(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function Layout() {
  const sim = useSimulation('default');
  const { state, connected, error } = sim;
  return (
    <SimContext.Provider value={sim}>
      <div className="app-shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark"><ShieldAlert size={22} /></div>
            <div>
              <div className="brand-name">EVADE-AI</div>
              <div className="brand-subtitle">EMERGENCY OPERATIONS CENTER</div>
            </div>
          </div>
          <Nav />
          <div className="topbar-right">
            <span className="system-status">
              <span className={`status-dot ${connected ? 'on' : ''}`} />
              {connected ? 'CONNECTED' : 'RECONNECTING'}
            </span>
            <span className="sim-badge">T {fmt(state.sim_time)}</span>
            <span className={`sim-badge ${state.incident.severity.toLowerCase()}`}>{state.incident.severity}</span>
            <span className="sim-badge">{state.running ? 'RUNNING' : 'IDLE'}</span>
          </div>
        </header>
        {error && <div className="banner-error">{error}</div>}
        <Outlet />
        <footer className="footer">
          EVADE-AI is a simulation and decision-support prototype for educational and research purposes.
          It is not certified life-safety infrastructure and must not replace approved emergency procedures,
          trained emergency personnel, safety engineering, or validated emergency-management systems.
        </footer>
      </div>
    </SimContext.Provider>
  );
}
