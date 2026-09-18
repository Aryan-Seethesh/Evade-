import type { BenchmarkResult, ScenarioInfo, WorldState } from '../types/world';

export const API_BASE = '';

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function getState(id = 'default'): Promise<WorldState> {
  return parse(await fetch(`${API_BASE}/api/simulations/${id}/state`));
}

export async function postSim(path: string, body?: unknown): Promise<WorldState> {
  return parse(await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }));
}

export async function getScenarios(): Promise<ScenarioInfo[]> {
  return parse(await fetch(`${API_BASE}/api/scenarios`));
}

export async function runBenchmark(seed = 42): Promise<BenchmarkResult> {
  return parse(await fetch(`${API_BASE}/api/benchmarks/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seed }),
  }));
}

export async function getLatestBenchmark(): Promise<BenchmarkResult | null> {
  const response = await fetch(`${API_BASE}/api/benchmarks/latest`);
  if (response.status === 404) return null;
  return parse(response);
}

export function wsUrl(simulationId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/simulations/${simulationId}`;
}
