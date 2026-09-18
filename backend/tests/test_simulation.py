from __future__ import annotations

from app.models.schema import EventType, GroupStatus, RiskLevel
from app.simulation.engine import SimulationEngine


def test_hazard_updates():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="s", scenario_id="basic_fire")
    engine.apply_event(state, EventType.FIRE_DETECTED, "building_b")
    assert "fire-building_b" in state.hazards
    assert state.nodes["building_b"].hazard_level == RiskLevel.HIGH
    engine.tick(state)  # not running yet
    state.running = True
    engine.tick(state)
    assert any(e.hazard_score > 0 for e in state.edges.values())


def test_crowd_movement_and_exit_occupancy():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="s", scenario_id="basic_fire")
    # Waiting occupants in buildings are not falsely counted as route density.
    assert max(edge.crowd_density for edge in state.edges.values()) == 0
    engine.start(state)
    start_nodes = {g.id: g.current_node for g in state.groups.values()}
    for _ in range(40):
        engine.tick(state)
    moved = any(state.groups[gid].current_node != node for gid, node in start_nodes.items())
    assert moved
    assert any(group.current_edge for group in state.groups.values() if group.status == GroupStatus.IN_TRANSIT)
    assert state.metrics.total_people > 0
    exits = [n for n in state.nodes.values() if n.type.value == "EXIT" or n.type == "EXIT"]
    assert exits


def test_responder_movement():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="s", scenario_id="basic_fire")
    engine.start(state)
    engine.apply_event(state, EventType.EMERGENCY_VEHICLE_APPROACHING, "fire-truck-1")
    start = state.responders["fire-truck-1"].current_location
    for _ in range(30):
        engine.tick(state)
    responder = state.responders["fire-truck-1"]
    assert responder.assigned_route
    assert responder.current_location != start or responder.availability == "ON_SCENE"


def test_metric_calculations():
    engine = SimulationEngine()
    state = engine.build_state(simulation_id="s", scenario_id="basic_fire")
    engine.start(state)
    engine.apply_event(state, EventType.FIRE_DETECTED, "building_b")
    for _ in range(10):
        engine.tick(state)
    m = state.metrics
    assert m.total_people == sum(g.size for g in state.groups.values())
    assert m.evacuated + m.in_transit + m.waiting + sum(
        g.size for g in state.groups.values() if g.status in {GroupStatus.BLOCKED, GroupStatus.SHELTERED} and g.evacuated == 0
    ) <= m.total_people + 1
    assert m.tick_time_ms >= 0
    assert m.active_hazards >= 1
