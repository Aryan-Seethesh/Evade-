from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.models.schema import EventType, ScriptedEvent, SimulationMode
from app.simulation.campus import STATIC_PLAN


@dataclass(frozen=True)
class ScenarioSpec:
    id: str
    name: str
    description: str
    events: List[ScriptedEvent]
    notes: str = ""


CAMPUS_FIRE_STAGES: List[ScriptedEvent] = [
    ScriptedEvent(at_time=8, event_type=EventType.FIRE_DETECTED, target_id="building_b", message="Fire detected in Building B"),
    ScriptedEvent(at_time=16, event_type=EventType.HAZARD_SPREAD, target_id="j_north", message="Smoke spreads toward North Exit"),
    ScriptedEvent(at_time=24, event_type=EventType.EXIT_BLOCKED, target_id="exit_north", message="Exit A (North) becomes unsafe"),
    ScriptedEvent(at_time=32, event_type=EventType.CROWD_SURGE, target_id="exit_south", value=220, message="Crowd surge at South Exit"),
    ScriptedEvent(at_time=42, event_type=EventType.ROUTE_BLOCKED, target_id="e_js_je", message="Alternative east-south route blocked"),
    ScriptedEvent(at_time=52, event_type=EventType.EMERGENCY_VEHICLE_APPROACHING, target_id="fire-truck-1", message="Fire truck approaching Building B"),
    ScriptedEvent(at_time=56, event_type=EventType.EMERGENCY_CORRIDOR_CREATED, target_id="fire-truck-1", message="Emergency corridor created"),
    ScriptedEvent(at_time=78, event_type=EventType.HAZARD_RESOLVED, target_id="building_b", message="Hazard decreases at Building B"),
    ScriptedEvent(at_time=86, event_type=EventType.ROUTE_REOPENED, target_id="e_js_je", message="Blocked route recovers"),
    ScriptedEvent(at_time=90, event_type=EventType.EXIT_REOPENED, target_id="exit_north", message="North Exit recovering"),
    ScriptedEvent(at_time=96, event_type=EventType.EMERGENCY_CORRIDOR_RELEASED, target_id="fire-truck-1", message="Emergency corridor released"),
]


SCENARIOS: Dict[str, ScenarioSpec] = {
    "campus_fire": ScenarioSpec(
        id="campus_fire",
        name="Campus Fire — Dynamic Multi-Stage Evacuation",
        description="Primary T0–T9 campus fire with smoke, blocked exit, surge, responder corridor, and recovery.",
        events=CAMPUS_FIRE_STAGES,
    ),
    "basic_fire": ScenarioSpec(
        id="basic_fire",
        name="Basic Fire",
        description="Single fire at Building B with no secondary failures.",
        events=[
            ScriptedEvent(at_time=6, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
        ],
    ),
    "blocked_exit": ScenarioSpec(
        id="blocked_exit",
        name="Fire + Blocked Exit",
        description="Fire followed by North Exit becoming critical.",
        events=[
            ScriptedEvent(at_time=6, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=14, event_type=EventType.EXIT_BLOCKED, target_id="exit_north"),
        ],
    ),
    "fire_congestion": ScenarioSpec(
        id="fire_congestion",
        name="Fire + Congestion",
        description="Fire plus crowd surge at the remaining high-capacity exit.",
        events=[
            ScriptedEvent(at_time=6, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=12, event_type=EventType.EXIT_BLOCKED, target_id="exit_north"),
            ScriptedEvent(at_time=18, event_type=EventType.CROWD_SURGE, target_id="exit_south", value=280),
        ],
    ),
    "fire_responder": ScenarioSpec(
        id="fire_responder",
        name="Fire + Responder",
        description="Fire with fire-truck corridor that forces civilian reroutes.",
        events=[
            ScriptedEvent(at_time=6, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=16, event_type=EventType.EMERGENCY_VEHICLE_APPROACHING, target_id="fire-truck-1"),
            ScriptedEvent(at_time=18, event_type=EventType.EMERGENCY_CORRIDOR_CREATED, target_id="fire-truck-1"),
        ],
    ),
    "multi_failure": ScenarioSpec(
        id="multi_failure",
        name="Multi-Failure",
        description="Fire, blocked exit, blocked route, crowd surge, and sensor failure.",
        events=[
            ScriptedEvent(at_time=5, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=10, event_type=EventType.EXIT_BLOCKED, target_id="exit_north"),
            ScriptedEvent(at_time=14, event_type=EventType.ROUTE_BLOCKED, target_id="e_js_es"),
            ScriptedEvent(at_time=18, event_type=EventType.CROWD_SURGE, target_id="exit_east", value=200),
            ScriptedEvent(at_time=20, event_type=EventType.SENSOR_FAILURE, target_id="sensor-exit_south"),
        ],
    ),
    "flood": ScenarioSpec(
        id="flood",
        name="Flood + Road Blockage",
        description="Flooded central corridor plus a blocked south exit approach.",
        events=[
            ScriptedEvent(at_time=8, event_type=EventType.FLOOD_DETECTED, target_id="e_js_quad"),
            ScriptedEvent(at_time=12, event_type=EventType.ROUTE_BLOCKED, target_id="e_js_es"),
            ScriptedEvent(at_time=16, event_type=EventType.FIRE_DETECTED, target_id="building_c"),
        ],
    ),
    "scenario_a": ScenarioSpec(
        id="scenario_a",
        name="Scenario A — Single Fire",
        description="Benchmark: isolated Building B fire.",
        events=[ScriptedEvent(at_time=4, event_type=EventType.FIRE_DETECTED, target_id="building_b")],
    ),
    "scenario_b": ScenarioSpec(
        id="scenario_b",
        name="Scenario B — Fire + Blocked Exit",
        description="Benchmark: fire then North Exit failure.",
        events=[
            ScriptedEvent(at_time=4, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=10, event_type=EventType.EXIT_BLOCKED, target_id="exit_north"),
        ],
    ),
    "scenario_c": ScenarioSpec(
        id="scenario_c",
        name="Scenario C — Fire + Crowd Surge",
        description="Benchmark: fire plus south-exit surge.",
        events=[
            ScriptedEvent(at_time=4, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=12, event_type=EventType.CROWD_SURGE, target_id="exit_south", value=260),
        ],
    ),
    "scenario_d": ScenarioSpec(
        id="scenario_d",
        name="Scenario D — Fire + Crowd + Responder",
        description="Benchmark: fire, surge, and corridor.",
        events=[
            ScriptedEvent(at_time=4, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=10, event_type=EventType.CROWD_SURGE, target_id="exit_south", value=200),
            ScriptedEvent(at_time=16, event_type=EventType.EMERGENCY_VEHICLE_APPROACHING, target_id="fire-truck-1"),
            ScriptedEvent(at_time=18, event_type=EventType.EMERGENCY_CORRIDOR_CREATED, target_id="fire-truck-1"),
        ],
    ),
    "scenario_e": ScenarioSpec(
        id="scenario_e",
        name="Scenario E — Fire + Multiple Route Failures",
        description="Benchmark: successive infrastructure failures.",
        events=[
            ScriptedEvent(at_time=4, event_type=EventType.FIRE_DETECTED, target_id="building_b"),
            ScriptedEvent(at_time=8, event_type=EventType.EXIT_BLOCKED, target_id="exit_north"),
            ScriptedEvent(at_time=12, event_type=EventType.ROUTE_BLOCKED, target_id="e_js_je"),
            ScriptedEvent(at_time=16, event_type=EventType.ROUTE_BLOCKED, target_id="e_jw_ew"),
        ],
    ),
    "scenario_f": ScenarioSpec(
        id="scenario_f",
        name="Scenario F — Flood + Road Blockage",
        description="Benchmark: flood plus blocked south approach.",
        events=[
            ScriptedEvent(at_time=6, event_type=EventType.FLOOD_DETECTED, target_id="e_js_quad"),
            ScriptedEvent(at_time=10, event_type=EventType.ROUTE_BLOCKED, target_id="e_js_es"),
        ],
    ),
}


def get_scenario(scenario_id: str) -> Optional[ScenarioSpec]:
    return SCENARIOS.get(scenario_id)


def list_scenarios() -> List[dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "event_count": len(s.events),
            "static_plan": STATIC_PLAN,
            "modes": [SimulationMode.EVADE_AI.value, SimulationMode.STATIC_BASELINE.value, SimulationMode.DEMO.value],
        }
        for s in SCENARIOS.values()
    ]
