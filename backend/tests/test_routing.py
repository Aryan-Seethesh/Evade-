from __future__ import annotations

from app.agent.routing import build_graph, enumerate_candidates, hard_constraint_reason
from app.models.schema import PopulationGroup
from app.simulation.engine import SimulationEngine


def test_valid_route():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="r", scenario_id="basic_fire")
    group = state.groups["students_a"]
    accepted, _ = enumerate_candidates(state, group)
    assert accepted
    assert accepted[0].path[0] == group.current_node


def test_blocked_edge_removed():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="r", scenario_id="basic_fire")
    state.edges["e_jn_en"].open = False
    group = state.groups["students_a"]
    reason = hard_constraint_reason(state, state.edges["e_jn_en"], group)
    assert reason
    graph = build_graph(state, group)
    assert not graph.has_edge("j_north", "exit_north")


def test_dynamic_weights_change_cost():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="r", scenario_id="basic_fire")
    group = state.groups["students_a"]
    a1, _ = enumerate_candidates(state, group)
    state.weights.hazard = 80.0
    for edge in state.edges.values():
        edge.hazard_score = 0.6
    a2, _ = enumerate_candidates(state, group)
    assert a1 and a2
    assert a2[0].cost != a1[0].cost or a2[0].destination != a1[0].destination or a2[0].utility != a1[0].utility


def test_alternative_route_when_exit_closed():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="r", scenario_id="basic_fire")
    group = state.groups["students_a"]
    accepted, _ = enumerate_candidates(state, group)
    first = accepted[0].destination
    state.nodes[first].open = False
    from app.models.schema import RiskLevel

    state.nodes[first].hazard_level = RiskLevel.CRITICAL
    accepted2, rejected = enumerate_candidates(state, group)
    assert any(r.destination == first for r in rejected)
    if accepted2:
        assert accepted2[0].destination != first


def test_inaccessible_route():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="r", scenario_id="basic_fire")
    group = PopulationGroup(
        id="access",
        label="Accessible group",
        size=10,
        current_node="j_west",
        accessibility_requirement=True,
    )
    accepted, rejected = enumerate_candidates(state, group)
    assert any(r.destination == "exit_west" and not r.feasible for r in rejected)
    assert all(c.destination != "exit_west" for c in accepted)
