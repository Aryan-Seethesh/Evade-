# EVADE-AI

## Problem

Emergency evacuation planning is difficult under changing conditions: fires spread, exits become unsafe, crowd density shifts, and responders need priority access. Traditional static plans often fail when the environment changes, creating avoidable congestion and safety risk.

## Solution

EVADE-AI is an intelligent dynamic evacuation and disaster-response platform that models a campus as a live graph, evaluates hazard, congestion, and accessibility constraints in real time, and reassigns evacuees using a utility-based agent. The system combines perception, world-state tracking, risk assessment, dynamic routing, responder coordination, explainable decisions, and benchmark evaluation in one integrated simulation.

## Key Features

- Utility-based evacuation agent with hard safety constraints
- Real-time world model for nodes, edges, hazards, groups, sensors, and responders
- Dynamic graph routing with congestion and hazard penalties
- Replanning when exits, routes, hazards, or crowd conditions change
- Responders with emergency-corridor creation and release
- Explainable routing decisions and a live decision history
- Live dashboard with operational metrics and event timeline
- Scenario-based simulation engine and baseline comparison benchmark
- WebSocket-backed streaming updates to the frontend

## Architecture

```text
Scenario / Simulator
  ↓
Event Ingestion
  ↓
Perception
  ↓
World Model
  ↓
Risk Engine
  ↓
Utility Decision Engine
  ↓
Dynamic Planner
  ↓
Action / Actuation
  ↓
Environment
  ↑
Feedback
```

## AI Agent Design

The system uses a utility-based agent that:

1. Reads the current world model.
2. Identifies feasible destinations.
3. Generates candidate routes.
4. Rejects unsafe or inaccessible paths with hard constraints.
5. Scores each route using travel time, congestion, hazard exposure, and emergency conflicts.
6. Selects the highest-utility valid option.
7. Records an explainable decision and re-evaluates when the environment changes.

## PEAS Model

### Performance Measure

- evacuation time
- hazard exposure
- congestion and predicted congestion
- successful evacuation rate
- emergency access effectiveness
- decision latency and tick latency

### Environment

- campus buildings and zones
- roads and intersections
- exits, shelters, and assembly areas
- people groups and accessibility requirements
- dynamic hazards and route restrictions
- responders and emergency corridors

### Actuators

- route assignments
- exit and route blocking changes
- emergency corridor creation
- operator override
- simulated alerts and signage decisions

### Sensors

- smoke and temperature events
- crowd occupancy
- CCTV-like zone perception
- infrastructure conditions
- responder and group state

## Simulation

The simulation runs as a deterministic tick-driven system. Each tick advances time, updates hazards, moves groups, updates congestion, updates sensor state, resolves responder movement, and triggers replanning when the world signature changes. A seed can be supplied for reproducible runs.

## Dynamic Routing

Routing is built on a weighted graph and uses a configurable cost model that combines:

- travel time weight
- congestion penalty
- hazard penalty
- emergency conflict penalty
- accessibility and capacity constraints

Routes are never accepted if a hard safety rule blocks them. Critical hazards, closed exits, inaccessible paths, emergency-only corridors, and blocked routes are treated as hard constraints before optimization occurs.

## Explainable AI

Every important decision records:

- trigger and situation
- candidate routes
- rejected routes with reasons
- selected destination and route
- utility scores
- route-change explanation where relevant

This allows the dashboard and decision-history pages to explain why the agent changed course.

## Demo

The demo scenario follows a staged campus fire progression:

- normal operations
- fire detected in Building B
- smoke spreads toward the north exit
- exit becomes unsafe
- crowd surge occurs
- alternative route is blocked
- emergency vehicle arrives
- emergency corridor is created
- hazards decrease and routes recover

## Benchmarks

The benchmark engine runs paired baseline and EVADE-AI simulations on the same scenario and seed. It records actual evacuation metrics instead of fabricated results and compares:

- evacuation time
- completion rate
- peak congestion
- hazard exposure
- responder delay
- reroute count
- decision latency

## Results

Benchmark results are generated from the real simulation engine and returned to the frontend for charting and comparison. Incomplete evacuations are reported honestly using the simulation horizon rather than pretending to have reached 100% completion.

## Tech Stack

- Backend: Python, FastAPI, Pydantic, NetworkX
- Frontend: React, TypeScript, Vite, Recharts, Lucide
- Communication: REST and WebSockets
- Persistence: SQLite-backed simulation metadata and state snapshots

## Project Structure

```text
backend/
  app/
    agent/
    api/
    models/
    simulation/
    main.py
    manager.py
    persistence.py
    benchmarks.py
  tests/
  requirements.txt
frontend/
  src/
  package.json
README.md
```

## Installation

### Backend

```bash
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Running Locally

### Backend

```bash
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Open http://localhost:5173

## Testing

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Limitations

- This is a research and educational simulation, not certified life-safety infrastructure.
- The campus graph is simplified and intentionally modeled for demonstration.
- Real-world emergency planning requires validated institutional policies, domain experts, and field-tested operational systems.

## Safety Disclaimer

> EVADE-AI is a simulation and decision-support prototype for educational and research purposes. It is not certified life-safety infrastructure and must not replace approved emergency procedures, trained emergency personnel, safety engineering, or validated emergency-management systems.

## Future Scope

- richer sensor fusion and confidence scoring
- more advanced multi-agent responder coordination
- database-backed historical simulation archives
- richer scenario authoring and data export
- operator console and policy overrides for field use

## License

This project is provided for educational and research use.

---

## Resume-Ready Project Summary

EVADE-AI is an intelligent dynamic evacuation and disaster-response platform that combines a live campus world model, real-time hazard simulation, dynamic graph routing, and utility-based decision making to adapt evacuation plans under changing emergency conditions. The system includes a real-time operations dashboard, explainable decision logging, responder coordination, and benchmark evaluation against a static baseline.
