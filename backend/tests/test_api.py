from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.manager import manager


def test_scenario_and_simulation_lifecycle():
    with TestClient(app) as client:
        listed = client.get("/api/scenarios")
        assert listed.status_code == 200
        assert any(s["id"] == "campus_fire" for s in listed.json())

        created = client.post("/api/simulations", json={"scenario_id": "basic_fire", "seed": 7})
        assert created.status_code == 200
        sid = created.json()["id"]

        started = client.post(f"/api/simulations/{sid}/start")
        assert started.status_code == 200
        assert started.json()["running"] is True

        event = client.post(
            f"/api/simulations/{sid}/events",
            json={"event_type": "FIRE_DETECTED", "target_id": "building_b"},
        )
        assert event.status_code == 200
        body = event.json()
        assert "fire-building_b" in body["hazards"]

        state = client.get(f"/api/simulations/{sid}/state")
        assert state.status_code == 200
        assert state.json()["id"] == sid

        bad = client.post(
            f"/api/simulations/{sid}/events",
            json={"event_type": "NOT_A_REAL_EVENT", "target_id": "building_b"},
        )
        assert bad.status_code == 400

        missing = client.get("/api/simulations/does-not-exist")
        assert missing.status_code == 404


def test_duplicate_start_is_idempotent():
    with TestClient(app) as client:
        manager.ensure_default()
        a = client.post("/api/simulations/default/start")
        b = client.post("/api/simulations/default/start")
        assert a.status_code == 200
        assert b.status_code == 200
        assert b.json()["running"] is True
