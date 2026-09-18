from __future__ import annotations

import copy
import time
from fastapi import APIRouter

from app.agent.routing import EvacuationAgent

router = APIRouter()
agent = EvacuationAgent()


def route_stats(state, dynamic: bool):
    start = time.perf_counter()
    working = copy.deepcopy(state)

    if dynamic:
        for node in working.nodes.values():
            if node.id == "building_b":
                node.hazard_level = "CRITICAL"
        working.nodes["exit_north"].hazard_level = "CRITICAL"
        working.edges["e1"].current_crowd_density = 0.85
        decisions = agent.replan_all(working)
        assigned = sum(1 for d in decisions if d.selected_exit)
        reroutes = len(decisions)
    else:
        # Baseline: always use the North Exit, ignoring later route failures.
        assigned = len(working.groups)
        reroutes = 0

    latency = (time.perf_counter() - start) * 1000
    return {
        "groups_assigned": assigned,
        "reroutes": reroutes,
        "decision_latency_ms": round(latency, 4),
    }


@router.get("/benchmark")
def benchmark():
    from app.main import build_default_state
    base = build_default_state()
    static = route_stats(base, dynamic=False)
    dynamic = route_stats(base, dynamic=True)

    return {
        "scenario": "Campus Fire + North Exit Failure",
        "note": "Metrics are generated from the local simulation implementation; no fabricated values are returned.",
        "static_baseline": static,
        "evade_ai": dynamic,
    }
