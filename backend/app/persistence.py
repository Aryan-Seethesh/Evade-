from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("evade.db")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "evade.db"


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT NOT NULL,
                    sim_time REAL NOT NULL,
                    type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    simulation_id TEXT NOT NULL,
                    sim_time REAL NOT NULL,
                    group_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT NOT NULL,
                    sim_time REAL NOT NULL,
                    tick INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT NOT NULL,
                    sim_time REAL NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hazards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT NOT NULL,
                    hazard_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS responders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT NOT NULL,
                    responder_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    destination TEXT,
                    route TEXT NOT NULL,
                    sim_time REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    seed INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )

    def upsert_simulation(self, sim_id: str, scenario_id: str, mode: str, seed: int, created_at: float, status: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO simulations(id, scenario_id, mode, seed, created_at, status)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status, mode=excluded.mode
                """,
                (sim_id, scenario_id, mode, seed, created_at, status),
            )

    def insert_event(self, simulation_id: str, sim_time: float, typ: str, message: str, payload: dict) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO events(simulation_id, sim_time, type, message, payload) VALUES(?,?,?,?,?)",
                (simulation_id, sim_time, typ, message, json.dumps(payload)),
            )

    def insert_decision(self, simulation_id: str, decision_id: str, sim_time: float, group_id: str, payload: dict) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO decisions(id, simulation_id, sim_time, group_id, payload) VALUES(?,?,?,?,?)",
                (decision_id, simulation_id, sim_time, group_id, json.dumps(payload)),
            )

    def insert_snapshot(self, simulation_id: str, sim_time: float, tick: int, payload: dict) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO snapshots(simulation_id, sim_time, tick, payload) VALUES(?,?,?,?)",
                (simulation_id, sim_time, tick, json.dumps(payload)),
            )
            conn.execute(
                """
                DELETE FROM snapshots WHERE simulation_id=? AND id NOT IN (
                    SELECT id FROM snapshots WHERE simulation_id=? ORDER BY id DESC LIMIT 40
                )
                """,
                (simulation_id, simulation_id),
            )

    def insert_metrics(self, simulation_id: str, sim_time: float, payload: dict) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO metrics(simulation_id, sim_time, payload) VALUES(?,?,?)",
                (simulation_id, sim_time, json.dumps(payload)),
            )

    def insert_benchmark(self, created_at: float, seed: int, payload: dict) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO benchmarks(created_at, seed, payload) VALUES(?,?,?)",
                (created_at, seed, json.dumps(payload)),
            )
            return int(cur.lastrowid)

    def latest_benchmark(self) -> Optional[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM benchmarks ORDER BY id DESC LIMIT 1").fetchone()
            return json.loads(row["payload"]) if row else None
