from __future__ import annotations

import logging
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.benchmarks import run_benchmarks
from app.manager import manager
from app.models.schema import (
    CreateSimulationPayload,
    EventPayload,
    EventType,
    OverridePayload,
    SimulationMode,
    SpeedPayload,
)
from app.simulation.scenarios import list_scenarios

log = logging.getLogger("evade.api")
router = APIRouter()


class BenchmarkRequest(BaseModel):
    seed: int = 42
    scenario_ids: Optional[List[str]] = None


class DemoRequest(BaseModel):
    scenario_id: str = "campus_fire"
    seed: int = Field(default=42)


def _session(simulation_id: str):
    try:
        return manager.get(simulation_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")


@router.get("/scenarios")
async def scenarios():
    return list_scenarios()


@router.post("/scenarios")
async def create_scenario_label(payload: dict):
    name = str(payload.get("name") or "").strip()[:80]
    if not name:
        raise HTTPException(status_code=400, detail="Scenario name is required")
    # Scenarios are code-defined; custom labels attach to a new simulation of campus_fire.
    state = manager.create(CreateSimulationPayload(scenario_id="campus_fire", demo=False))
    return {"id": state.id, "label": name, "scenario_id": "campus_fire"}


@router.post("/simulations")
async def create_simulation(payload: CreateSimulationPayload):
    try:
        state = manager.create(payload)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{payload.scenario_id}'")
    return state.model_dump(mode="json")


@router.get("/simulations/{simulation_id}")
async def get_simulation(simulation_id: str):
    return _session(simulation_id).state.model_dump(mode="json")


@router.get("/simulations/{simulation_id}/state")
async def get_state(simulation_id: str):
    return _session(simulation_id).state.model_dump(mode="json")


@router.get("/simulations/{simulation_id}/decisions")
async def get_decisions(simulation_id: str, group: Optional[str] = None, decision_type: Optional[str] = None):
    decisions = _session(simulation_id).state.decisions
    if group:
        decisions = [d for d in decisions if d.group_id == group]
    if decision_type:
        decisions = [d for d in decisions if d.decision_type == decision_type]
    return [d.model_dump(mode="json") for d in decisions]


@router.get("/simulations/{simulation_id}/metrics")
async def get_metrics(simulation_id: str):
    state = _session(simulation_id).state
    return {"metrics": state.metrics.model_dump(mode="json"), "history": [p.model_dump() for p in state.metrics_history]}


@router.post("/simulations/{simulation_id}/start")
async def start_sim(simulation_id: str):
    session = _session(simulation_id)
    if session.state.running:
        return session.state.model_dump(mode="json")
    manager.engine.start(session.state)
    manager.db.upsert_simulation(
        simulation_id, session.state.scenario_id, session.state.mode.value, session.state.seed, time.time(), "running"
    )
    await manager.after_change(session, session.state.decisions[-8:] if session.state.decisions else [])
    return session.state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/pause")
async def pause_sim(simulation_id: str):
    session = _session(simulation_id)
    manager.engine.pause(session.state)
    await manager.after_change(session)
    return session.state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/resume")
async def resume_sim(simulation_id: str):
    session = _session(simulation_id)
    manager.engine.resume(session.state)
    await manager.after_change(session)
    return session.state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/reset")
async def reset_sim(simulation_id: str):
    state = manager.reset(simulation_id)
    session = manager.get(simulation_id)
    await manager.after_change(session)
    return state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/speed")
async def speed_sim(simulation_id: str, payload: SpeedPayload):
    session = _session(simulation_id)
    session.state.simulation_speed = payload.speed
    await manager.after_change(session)
    # Controls share the same state contract as every other simulation mutation.
    # Returning only {speed} previously allowed clients to replace a WorldState with
    # a partial payload after a speed change.
    return session.state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/events")
async def inject_event(simulation_id: str, payload: EventPayload):
    session = _session(simulation_id)
    aliases = {
        "TRIGGER_FIRE": "FIRE_DETECTED",
        "SPREAD_SMOKE": "HAZARD_SPREAD",
        "BLOCK_EXIT": "EXIT_BLOCKED",
        "BLOCK_ROUTE": "ROUTE_BLOCKED",
        "FLOOD_ROAD": "FLOOD_DETECTED",
        "EMERGENCY_VEHICLE": "EMERGENCY_VEHICLE_APPROACHING",
        "OPEN_EXIT": "EXIT_REOPENED",
        "RESOLVE_HAZARD": "HAZARD_RESOLVED",
        "SEND_AMBULANCE": "EMERGENCY_VEHICLE_APPROACHING",
        "SEND_FIRE_TRUCK": "EMERGENCY_VEHICLE_APPROACHING",
    }
    raw = aliases.get(payload.event_type, payload.event_type)
    try:
        et = EventType(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event type")
    payload.event_type = et.value
    if et in {
        EventType.FIRE_DETECTED,
        EventType.HAZARD_SPREAD,
        EventType.EXIT_BLOCKED,
        EventType.EXIT_REOPENED,
        EventType.HAZARD_RESOLVED,
        EventType.HAZARD_INCREASED,
    }:
        if payload.target_id not in session.state.nodes:
            raise HTTPException(status_code=400, detail=f"Unknown node '{payload.target_id}'")
    if et in {EventType.ROUTE_BLOCKED, EventType.ROUTE_REOPENED, EventType.FLOOD_DETECTED}:
        if payload.target_id not in session.state.edges:
            raise HTTPException(status_code=400, detail=f"Unknown edge '{payload.target_id}'")
    if et == EventType.SENSOR_FAILURE and payload.target_id not in session.state.sensors:
        raise HTTPException(status_code=400, detail=f"Unknown sensor '{payload.target_id}'")
    try:
        decisions = manager.engine.apply_event(session.state, et, payload.target_id, payload.value)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown target {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await manager.after_change(session, decisions)
    return session.state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/override")
async def override(simulation_id: str, payload: OverridePayload):
    session = _session(simulation_id)
    try:
        manager.engine.override(session.state, payload.group_id, payload.destination, payload.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown group")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await manager.after_change(session)
    return session.state.model_dump(mode="json")


@router.post("/simulations/{simulation_id}/demo")
async def start_demo(simulation_id: str):
    session = _session(simulation_id)
    fresh = manager.engine.build_state(
        simulation_id=simulation_id,
        scenario_id="campus_fire",
        mode=SimulationMode.DEMO,
        seed=session.state.seed,
        demo=True,
    )
    session.state = fresh
    manager.engine.start(session.state)
    await manager.after_change(session, session.state.decisions[-8:])
    return session.state.model_dump(mode="json")


@router.post("/benchmarks/run")
async def benchmarks_run(payload: BenchmarkRequest | None = None):
    payload = payload or BenchmarkRequest()
    try:
        result = run_benchmarks(seed=payload.seed, scenario_ids=payload.scenario_ids)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown scenario {exc}")
    manager.db.insert_benchmark(time.time(), payload.seed, result)
    return result


@router.get("/benchmarks/latest")
async def benchmarks_latest():
    row = manager.db.latest_benchmark()
    if not row:
        raise HTTPException(status_code=404, detail="No benchmark has been run yet")
    return row

