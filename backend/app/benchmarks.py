from __future__ import annotations

import time
from typing import List

from app.models.schema import CreateSimulationPayload, Metrics, SimulationMode, WorldState
from app.simulation.engine import SimulationEngine
from app.simulation.scenarios import SCENARIOS

BENCHMARK_SCENARIOS = [
    "scenario_a",
    "scenario_b",
    "scenario_c",
    "scenario_d",
    "scenario_e",
    "scenario_f",
]

MAX_TICKS = 140


def run_until(engine: SimulationEngine, state: WorldState, max_ticks: int = MAX_TICKS) -> WorldState:
    engine.start(state)
    for _ in range(max_ticks):
        engine.tick(state)
        if state.metrics.completion_rate >= 0.999:
            break
        if not state.running:
            break
    state.running = False
    if state.metrics.evacuation_time == 0 and state.metrics.completion_rate >= 0.999:
        state.metrics.evacuation_time = state.sim_time
    if state.metrics.completion_rate < 0.999:
        # incomplete: evacuation_time is horizon
        state.metrics.evacuation_time = state.sim_time
    return state


def summarize(metrics: Metrics) -> dict:
    return {
        "evacuation_time": round(metrics.evacuation_time, 2),
        "completion_rate": round(metrics.completion_rate, 4),
        "peak_congestion": round(metrics.peak_congestion, 4),
        "predicted_peak_congestion": round(metrics.predicted_peak_congestion, 4),
        "hazard_exposure": round(metrics.hazard_exposure, 4),
        "responder_delay": round(metrics.responder_delay, 2),
        "reroute_count": int(metrics.reroutes),
        "decision_latency_ms": round(metrics.avg_decision_latency_ms, 4),
        "avg_tick_time_ms": round(metrics.avg_tick_time_ms, 4),
        "decisions": int(metrics.decisions_count),
        "evacuated": int(metrics.evacuated),
        "total_people": int(metrics.total_people),
    }


def run_pair(scenario_id: str, seed: int) -> dict:
    engine = SimulationEngine()
    baseline = engine.build_state(
        simulation_id=f"bench-base-{scenario_id}-{seed}",
        scenario_id=scenario_id,
        mode=SimulationMode.STATIC_BASELINE,
        seed=seed,
    )
    evade = engine.build_state(
        simulation_id=f"bench-ai-{scenario_id}-{seed}",
        scenario_id=scenario_id,
        mode=SimulationMode.EVADE_AI,
        seed=seed,
    )
    run_until(engine, baseline)
    run_until(engine, evade)
    spec = SCENARIOS[scenario_id]
    return {
        "scenario_id": scenario_id,
        "name": spec.name,
        "seed": seed,
        "static_baseline": summarize(baseline.metrics),
        "evade_ai": summarize(evade.metrics),
        "history": {
            "baseline": [p.model_dump() for p in baseline.metrics_history[-40:]],
            "evade_ai": [p.model_dump() for p in evade.metrics_history[-40:]],
        },
    }


def run_benchmarks(seed: int = 42, scenario_ids: List[str] | None = None) -> dict:
    started = time.perf_counter()
    ids = scenario_ids or BENCHMARK_SCENARIOS
    results = [run_pair(sid, seed) for sid in ids]
    elapsed = (time.perf_counter() - started) * 1000.0
    return {
        "seed": seed,
        "note": "All figures are produced by executing both policies on identical campus graphs, seeds, and scripted events. Incomplete evacuations report the simulation horizon as evacuation_time.",
        "wall_time_ms": round(elapsed, 2),
        "scenarios": results,
    }
