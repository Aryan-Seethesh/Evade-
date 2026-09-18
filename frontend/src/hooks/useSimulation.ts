import { useCallback, useEffect, useRef, useState } from 'react';
import { getState, postSim, wsUrl } from '../lib/api';
import { emptyState, type WorldState, type WsEnvelope } from '../types/world';

export function useSimulation(simulationId = 'default') {
  const [state, setState] = useState<WorldState>(emptyState);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seen = useRef<Set<string>>(new Set());
  const timer = useRef<number | null>(null);

  const applyEnvelope = useCallback((msg: WsEnvelope) => {
    const key = `${msg.type}:${msg.timestamp}:${msg.sim_time}`;
    if (seen.current.has(key)) return;
    seen.current.add(key);
    if (seen.current.size > 400) seen.current.clear();
    if (msg.state) setState(msg.state);
    else if (msg.type === 'AGENT_DECISION' && msg.decision) {
      setState((prev) => ({ ...prev, decisions: [...prev.decisions.slice(-119), msg.decision!] }));
    }
  }, []);

  useEffect(() => {
    let closed = false;
    let ws: WebSocket | null = null;
    let attempt = 0;

    getState(simulationId).then(setState).catch((err: Error) => setError(err.message));

    const connect = () => {
      if (closed) return;
      ws = new WebSocket(wsUrl(simulationId));
      ws.onopen = () => {
        attempt = 0;
        setConnected(true);
        setError(null);
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        attempt += 1;
        const wait = Math.min(8000, 400 * 2 ** Math.min(attempt, 4));
        timer.current = window.setTimeout(connect, wait);
      };
      ws.onerror = () => setConnected(false);
      ws.onmessage = (event) => {
        try {
          applyEnvelope(JSON.parse(event.data) as WsEnvelope);
        } catch (err) {
          setError('Malformed realtime payload');
        }
      };
    };
    connect();
    return () => {
      closed = true;
      if (timer.current) window.clearTimeout(timer.current);
      ws?.close();
    };
  }, [simulationId, applyEnvelope]);

  const run = useCallback(async (path: string, body?: unknown) => {
    try {
      setError(null);
      setState(await postSim(path, body));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    }
  }, []);

  return { state, connected, error, setError, run, setState };
}
