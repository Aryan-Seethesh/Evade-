from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.models.schema import (
    AgentDecision,
    CreateSimulationPayload,
    EventType,
    SimulationMode,
    WorldState,
    WsMessage,
)
from app.persistence import Database
from app.simulation.engine import SimulationEngine
from app.simulation.scenarios import get_scenario

log = logging.getLogger("evade.manager")


class SimulationSession:
    def __init__(self, state: WorldState) -> None:
        self.state = state
        self.sockets: List[WebSocket] = []
        self._last_persist = 0.0


class SimulationManager:
    def __init__(self) -> None:
        self.engine = SimulationEngine()
        self.db = Database()
        self.sessions: Dict[str, SimulationSession] = {}
        self._task: Optional[asyncio.Task] = None

    def create(self, payload: CreateSimulationPayload | None = None, simulation_id: Optional[str] = None) -> WorldState:
        payload = payload or CreateSimulationPayload()
        if not get_scenario(payload.scenario_id) and payload.scenario_id != "campus_fire":
            raise KeyError(payload.scenario_id)
        sid = simulation_id or uuid.uuid4().hex[:12]
        state = self.engine.build_state(
            simulation_id=sid,
            scenario_id=payload.scenario_id,
            mode=payload.mode,
            seed=payload.seed,
            demo=payload.demo,
        )
        self.sessions[sid] = SimulationSession(state)
        self.db.upsert_simulation(sid, payload.scenario_id, payload.mode.value, payload.seed, time.time(), "created")
        log.info("Created simulation %s scenario=%s mode=%s seed=%s", sid, payload.scenario_id, payload.mode, payload.seed)
        return state

    def ensure_default(self) -> WorldState:
        if "default" not in self.sessions:
            self.create(CreateSimulationPayload(demo=False), simulation_id="default")
        return self.sessions["default"].state

    def get(self, simulation_id: str) -> SimulationSession:
        if simulation_id not in self.sessions:
            raise KeyError(simulation_id)
        return self.sessions[simulation_id]

    def reset(self, simulation_id: str) -> WorldState:
        session = self.get(simulation_id)
        prev = session.state
        state = self.engine.build_state(
            simulation_id=simulation_id,
            scenario_id=prev.scenario_id,
            mode=prev.mode,
            seed=prev.seed,
            demo=prev.demo_active,
        )
        session.state = state
        self.db.upsert_simulation(simulation_id, state.scenario_id, state.mode.value, state.seed, time.time(), "reset")
        return state

    def persist_decision(self, state: WorldState, decision: AgentDecision) -> None:
        self.db.insert_decision(state.id, decision.decision_id, decision.sim_time, decision.group_id, decision.model_dump(mode="json"))
        try:
            with self.db._lock, self.db._connect() as conn:
                conn.execute(
                    "INSERT INTO assignments(simulation_id, group_id, destination, route, sim_time) VALUES(?,?,?,?,?)",
                    (state.id, decision.group_id, decision.selected_destination, ",".join(decision.selected_route), decision.sim_time),
                )
        except Exception:
            log.exception("Failed to persist assignment")

    async def broadcast(self, session: SimulationSession, extra: Optional[WsMessage] = None) -> None:
        messages = [
            WsMessage(
                type="STATE_UPDATE",
                timestamp=time.time(),
                sim_time=session.state.sim_time,
                state=session.state,
            )
        ]
        if extra:
            messages.append(extra)
        stale: List[WebSocket] = []
        for ws in list(session.sockets):
            try:
                for msg in messages:
                    await ws.send_json(msg.model_dump(mode="json"))
            except Exception:
                stale.append(ws)
        for ws in stale:
            if ws in session.sockets:
                session.sockets.remove(ws)
                log.info("Dropped stale websocket for %s", session.state.id)

    async def after_change(self, session: SimulationSession, decisions: Optional[list] = None) -> None:
        await self.broadcast(session)
        if decisions:
            for d in decisions:
                self.persist_decision(session.state, d)
                await self.broadcast(
                    session,
                    WsMessage(
                        type="AGENT_DECISION",
                        timestamp=time.time(),
                        sim_time=session.state.sim_time,
                        decision=d,
                    ),
                )
        if session.state.timeline:
            last = session.state.timeline[-1]
            if last.type in {e.value for e in EventType}:
                await self.broadcast(
                    session,
                    WsMessage(
                        type="INCIDENT",
                        timestamp=time.time(),
                        sim_time=session.state.sim_time,
                        incident=session.state.incident,
                        message=last.message,
                    ),
                )
        now = time.time()
        if now - session._last_persist > 2.0:
            session._last_persist = now
            self.db.insert_snapshot(session.state.id, session.state.sim_time, session.state.tick, session.state.model_dump(mode="json"))
            self.db.insert_metrics(session.state.id, session.state.sim_time, session.state.metrics.model_dump(mode="json"))
            if session.state.timeline:
                ev = session.state.timeline[-1]
                self.db.insert_event(session.state.id, ev.sim_time, ev.type, ev.message, ev.payload)

    async def loop(self) -> None:
        log.info("Simulation loop started")
        while True:
            try:
                running = [s for s in self.sessions.values() if s.state.running]
                if not running:
                    await asyncio.sleep(0.15)
                    continue
                fastest = max(s.state.simulation_speed for s in running)
                delay = max(0.05, 1.0 / fastest)
                for session in running:
                    # speed: number of ticks per wall-second
                    ticks = max(1, int(round(session.state.simulation_speed / fastest)))
                    if session.state.simulation_speed < fastest:
                        # fractional: tick only some loops
                        if int(time.time() / delay) % max(1, int(fastest / max(session.state.simulation_speed, 0.25))) != 0:
                            continue
                        ticks = 1
                    for _ in range(min(ticks, 4)):
                        if not session.state.running:
                            break
                        decisions = self.engine.tick(session.state)
                        await self.after_change(session, decisions)
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Simulation loop error")
                await asyncio.sleep(0.5)

    def start_loop(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.loop())

    async def stop_loop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


manager = SimulationManager()
