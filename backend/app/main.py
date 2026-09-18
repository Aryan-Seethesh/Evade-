from __future__ import annotations

from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.logging_config import configure_logging
from app.manager import manager
from app.models.schema import CreateSimulationPayload, EventPayload, SpeedPayload, WsMessage

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.ensure_default()
    manager.start_loop()
    yield
    await manager.stop_loop()


app = FastAPI(
    title="EVADE-AI API",
    version="2.0.0",
    description="Intelligent Dynamic Evacuation & Disaster Response Platform",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.websocket("/ws/simulations/{simulation_id}")
async def ws_simulation(websocket: WebSocket, simulation_id: str):
    try:
        session = manager.get(simulation_id)
    except KeyError:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    session.sockets.append(websocket)
    try:
        await websocket.send_json(
            WsMessage(
                type="STATE_UPDATE",
                timestamp=time.time(),
                sim_time=session.state.sim_time,
                state=session.state,
            ).model_dump(mode="json")
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in session.sockets:
            session.sockets.remove(websocket)


@app.websocket("/ws")
async def ws_default(websocket: WebSocket):
    await ws_simulation(websocket, "default")


@app.get("/")
async def root():
    return {"status": "online", "system": "EVADE-AI", "version": "2.0.0"}


@app.get("/api/state")
async def legacy_state():
    return manager.ensure_default().model_dump(mode="json")


@app.post("/api/simulation/start")
async def legacy_start():
    session = manager.get("default")
    if not session.state.running:
        manager.engine.start(session.state)
        await manager.after_change(session, session.state.decisions[-8:])
    return session.state.model_dump(mode="json")


@app.post("/api/simulation/stop")
async def legacy_stop():
    session = manager.get("default")
    manager.engine.pause(session.state)
    await manager.after_change(session)
    return session.state.model_dump(mode="json")


@app.post("/api/simulation/reset")
async def legacy_reset():
    state = manager.reset("default")
    await manager.after_change(manager.get("default"))
    return state.model_dump(mode="json")


@app.post("/api/simulation/speed")
async def legacy_speed(payload: SpeedPayload):
    session = manager.get("default")
    session.state.simulation_speed = payload.speed
    await manager.after_change(session)
    return session.state.model_dump(mode="json")


@app.post("/api/simulation/event")
async def legacy_event(event: EventPayload):
    session = manager.get("default")
    try:
        decisions = manager.engine.apply_event(session.state, event.event_type, event.target_id, event.value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await manager.after_change(session, decisions)
    return session.state.model_dump(mode="json")


@app.post("/api/simulations/default/load")
async def load_into_default(payload: CreateSimulationPayload):
    session = manager.get("default")
    state = manager.engine.build_state(
        simulation_id="default",
        scenario_id=payload.scenario_id,
        mode=payload.mode,
        seed=payload.seed,
        demo=payload.demo,
    )
    session.state = state
    await manager.after_change(session)
    return state.model_dump(mode="json")
