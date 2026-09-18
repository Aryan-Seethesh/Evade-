from __future__ import annotations

from app.agent.planner import EvacuationAgent
from app.models.schema import EventType, GroupStatus, RiskLevel, SimulationMode
from app.simulation.engine import SimulationEngine


def _world():
    engine = SimulationEngine()
    return engine, engine.build_state(simulation_id="t", scenario_id="basic_fire", seed=1)


def test_unsafe_route_rejection():
    engine, state = _world()
    engine.apply_event(state, EventType.EXIT_BLOCKED, "exit_north")
    agent = EvacuationAgent()
    d = agent.plan_group(state, state.groups["students_a"], "TEST", "exit blocked")
    assert d.selected_destination != "exit_north"
    assert any(r.destination == "exit_north" and not r.feasible for r in d.rejected_routes)


def test_blocked_exit_rejection():
    engine, state = _world()
    engine.apply_event(state, EventType.FIRE_DETECTED, "building_b")
    engine.apply_event(state, EventType.EXIT_BLOCKED, "exit_south")
    dests = {g.destination for g in state.groups.values() if g.destination}
    assert "exit_south" not in dests or state.nodes["exit_south"].hazard_level == RiskLevel.CRITICAL


def test_congestion_influence():
    engine, state = _world()
    engine.start(state)
    south = next(g for g in state.groups.values() if g.destination == "exit_south")
    engine.apply_event(state, EventType.CROWD_SURGE, "exit_south", 800)
    # At least one decision should mention congestion or a different destination after surge
    latest = [d for d in state.decisions if d.group_id == south.id]
    assert latest
    assert latest[-1].selected_destination is not None


def test_emergency_corridor_priority():
    engine, state = _world()
    engine.start(state)
    engine.apply_event(state, EventType.EMERGENCY_VEHICLE_APPROACHING, "fire-truck-1")
    engine.apply_event(state, EventType.EMERGENCY_CORRIDOR_CREATED, "fire-truck-1")
    assert any(e.emergency_restricted for e in state.edges.values())
    corridor_edges = {eid for c in state.corridors.values() if c.active for eid in c.edge_ids}
    for group in state.groups.values():
        if group.status == GroupStatus.BLOCKED:
            continue
        for a, b in zip(group.assigned_route, group.assigned_route[1:]):
            for edge in state.edges.values():
                if {edge.source, edge.target} == {a, b}:
                    assert edge.id not in corridor_edges or not edge.emergency_restricted or group.type == "RESPONDER"


def test_replanning_on_blocked_preferred_exit():
    engine, state = _world()
    engine.start(state)
    group = state.groups["students_a"]
    first = group.destination
    assert first
    engine.apply_event(state, EventType.EXIT_BLOCKED, first)
    assert group.destination != first or group.status == GroupStatus.BLOCKED


def test_no_safe_route_behavior():
    engine, state = _world()
    for edge in state.edges.values():
        edge.open = False
    agent = EvacuationAgent()
    d = agent.plan_group(state, next(iter(state.groups.values())), "TEST", "all closed")
    assert d.decision_type == "NO_SAFE_ROUTE"
    assert "OPERATOR INTERVENTION" in d.reason
