from __future__ import annotations

import copy
import logging
import random
import time
import uuid
from typing import Any, List, Optional

from app.agent.planner import EvacuationAgent
from app.agent.routing import get_edge, predicted_edge_density, predicted_occupancy, signature
from app.models.schema import (
    DataQuality,
    EmergencyCorridor,
    EventPayload,
    EventType,
    GroupStatus,
    Hazard,
    Incident,
    Metrics,
    MetricsPoint,
    NodeType,
    RiskLevel,
    SensorStatus,
    SimulationMode,
    TimelineEvent,
    WorldState,
)
from app.simulation.campus import (
    STATIC_PLAN,
    campus_graph,
    default_groups,
    default_responders,
    default_sensors,
)
from app.simulation.scenarios import CAMPUS_FIRE_STAGES, get_scenario

log = logging.getLogger("evade.sim")

TICK_DT = 1.0
HISTORY_CAP = 180
TIMELINE_CAP = 160


class SimulationEngine:
    def __init__(self) -> None:
        self.agent = EvacuationAgent()

    def build_state(
        self,
        *,
        simulation_id: str,
        scenario_id: str = "campus_fire",
        mode: SimulationMode = SimulationMode.EVADE_AI,
        seed: int = 42,
        demo: bool = False,
    ) -> WorldState:
        rng = random.Random(seed)
        nodes, edges = campus_graph()
        groups = default_groups()
        if seed != 42:
            for g in groups.values():
                jitter = rng.randint(-12, 12)
                g.size = max(20, g.size + jitter)
        spec = get_scenario(scenario_id)
        scripted = list(spec.events) if spec else []
        if demo and not scripted:
            scripted = list(CAMPUS_FIRE_STAGES)
        if demo and scenario_id == "campus_fire":
            scripted = list(CAMPUS_FIRE_STAGES)
        state = WorldState(
            id=simulation_id,
            scenario_id=scenario_id,
            mode=SimulationMode.DEMO if demo else mode,
            seed=seed,
            nodes=nodes,
            edges=edges,
            groups=groups,
            responders=default_responders(),
            sensors=default_sensors(),
            demo_active=demo,
            scripted_events=scripted,
            incident=Incident(message="Normal campus operations — no active hazard"),
        )
        self._update_crowd(state)
        self._update_sensors(state)
        self._update_metrics(state)
        self._log(state, "SYSTEM", "Simulation initialized")
        return state

    def start(self, state: WorldState) -> None:
        state.running = True
        if state.incident.status == "NORMAL":
            state.incident.status = "MONITORING"
            state.incident.message = "Simulation active — monitoring environment"
            state.incident.evacuation = "STANDBY"
        self._log(state, "SYSTEM", "Simulation started")
        if state.mode == SimulationMode.STATIC_BASELINE:
            self._apply_static(state)
        else:
            self.agent.replan(state, "SIMULATION_START", "Evacuation planning initiated")

    def pause(self, state: WorldState) -> None:
        state.running = False
        self._log(state, "SYSTEM", "Simulation paused")

    def resume(self, state: WorldState) -> None:
        state.running = True
        self._log(state, "SYSTEM", "Simulation resumed")

    def tick(self, state: WorldState) -> List:
        if not state.running:
            return []
        t0 = time.perf_counter()
        state.tick += 1
        state.sim_time = round(state.sim_time + TICK_DT, 3)
        new_decisions = []

        self._fire_scripted(state)
        self._update_hazards(state)
        self._move_groups(state)
        self._move_responders(state)
        self._update_crowd(state)
        self._update_predicted(state)
        self._update_sensors(state)
        self._update_incident(state)

        sig = signature(state)
        should = sig != state.world_signature and state.mode != SimulationMode.STATIC_BASELINE
        if should and state.tick > 1:
            new_decisions = self.agent.replan(
                state,
                "WORLD_STATE_CHANGE",
                "Environment signature changed — evaluating routes",
            )
        state.world_signature = sig
        self._update_metrics(state)
        elapsed = (time.perf_counter() - t0) * 1000.0
        state.metrics.tick_time_ms = round(elapsed, 3)
        n = max(state.tick, 1)
        state.metrics.avg_tick_time_ms = round(
            (state.metrics.avg_tick_time_ms * (n - 1) + elapsed) / n, 3
        )
        if state.tick % 2 == 0:
            self._push_history(state)
        return new_decisions

    def apply_event(self, state: WorldState, event_type: EventType | str, target_id: str = "", value: Any = None) -> List:
        if isinstance(event_type, str):
            aliases = {
                "TRIGGER_FIRE": EventType.FIRE_DETECTED,
                "SPREAD_SMOKE": EventType.HAZARD_SPREAD,
                "BLOCK_EXIT": EventType.EXIT_BLOCKED,
                "BLOCK_ROUTE": EventType.ROUTE_BLOCKED,
                "CROWD_SURGE": EventType.CROWD_SURGE,
                "FLOOD_ROAD": EventType.FLOOD_DETECTED,
                "EMERGENCY_VEHICLE": EventType.EMERGENCY_VEHICLE_APPROACHING,
                "OPEN_EXIT": EventType.EXIT_REOPENED,
                "RESOLVE_HAZARD": EventType.HAZARD_RESOLVED,
                "SEND_AMBULANCE": EventType.EMERGENCY_VEHICLE_APPROACHING,
                "SEND_FIRE_TRUCK": EventType.EMERGENCY_VEHICLE_APPROACHING,
            }
            event_type = aliases.get(event_type, EventType(event_type))
        handler = {
            EventType.FIRE_DETECTED: self._fire_detected,
            EventType.HAZARD_INCREASED: self._hazard_increased,
            EventType.HAZARD_SPREAD: self._hazard_spread,
            EventType.EXIT_BLOCKED: self._exit_blocked,
            EventType.EXIT_REOPENED: self._exit_reopened,
            EventType.ROUTE_BLOCKED: self._route_blocked,
            EventType.ROUTE_REOPENED: self._route_reopened,
            EventType.CROWD_SURGE: self._crowd_surge,
            EventType.CROWD_NORMALIZED: self._crowd_normalized,
            EventType.FLOOD_DETECTED: self._flood,
            EventType.EMERGENCY_VEHICLE_APPROACHING: self._vehicle,
            EventType.EMERGENCY_CORRIDOR_CREATED: self._corridor_create,
            EventType.EMERGENCY_CORRIDOR_RELEASED: self._corridor_release,
            EventType.HAZARD_RESOLVED: self._hazard_resolved,
            EventType.SENSOR_FAILURE: self._sensor_failure,
            EventType.OPERATOR_OVERRIDE: self._operator_override,
        }.get(event_type)
        if not handler:
            raise ValueError(f"Unsupported event type: {event_type}")
        handler(state, target_id, value)
        self._update_crowd(state)
        self._update_predicted(state)
        self._update_incident(state)
        decisions = []
        if state.mode != SimulationMode.STATIC_BASELINE:
            decisions = self.agent.replan(
                state,
                event_type.value,
                f"Event {event_type.value} applied to {target_id or 'system'}",
            )
        else:
            self._log(state, event_type.value, f"Baseline received {event_type.value} (no dynamic replan)")
        state.world_signature = signature(state)
        self._update_metrics(state)
        return decisions

    def override(self, state: WorldState, group_id: str, destination: str, reason: str) -> None:
        group = state.groups.get(group_id)
        if not group:
            raise KeyError(group_id)
        path = None
        from app.agent.routing import enumerate_candidates

        accepted, _ = enumerate_candidates(state, group, destinations=[destination])
        if accepted:
            path = accepted[0].path
        if not path:
            from app.agent.routing import shortest_unconstrained

            path = shortest_unconstrained(state, group.current_node, destination)
        if not path:
            raise ValueError("Override destination is not reachable")
        group.assigned_route = path
        group.destination = destination
        group.status = GroupStatus.IN_TRANSIT
        state.operator_intervention_required = False
        self._log(state, EventType.OPERATOR_OVERRIDE.value, f"Operator routed {group.label} → {destination}: {reason}")

    def _apply_static(self, state: WorldState) -> None:
        from app.agent.routing import shortest_unconstrained

        for group in state.groups.values():
            dest = STATIC_PLAN.get(group.origin_building or group.current_node, "exit_south")
            path = shortest_unconstrained(state, group.current_node, dest) or [group.current_node]
            group.destination = dest
            group.assigned_route = path
            group.status = GroupStatus.IN_TRANSIT
        self._log(state, "BASELINE", "Static evacuation plan assigned (no dynamic replanning)")

    def _fire_scripted(self, state: WorldState) -> None:
        if not state.scripted_events:
            return
        for idx, ev in enumerate(state.scripted_events):
            if idx in state.fired_script_indices:
                continue
            if state.sim_time + 1e-6 >= ev.at_time:
                state.fired_script_indices.append(idx)
                msg = ev.message or ev.event_type.value
                self._log(state, EventType.DEMO_STAGE.value, msg)
                try:
                    self.apply_event(state, ev.event_type, ev.target_id, ev.value)
                except Exception:
                    log.exception("Scripted event failed: %s", ev)

    def _fire_detected(self, state: WorldState, target_id: str, value: Any) -> None:
        node = state.nodes[target_id]
        hid = f"fire-{target_id}"
        state.hazards[hid] = Hazard(
            id=hid,
            type="FIRE",
            location=target_id,
            severity=float(value) if value else 0.92,
            spread_radius=1.0,
            active=True,
            timestamp=state.sim_time,
        )
        node.hazard_level = RiskLevel.HIGH
        for edge in state.edges.values():
            if edge.source == target_id or edge.target == target_id:
                edge.hazard_score = max(edge.hazard_score, 0.55)
        self._log(state, EventType.FIRE_DETECTED.value, f"Fire detected in {node.name}")

    def _hazard_increased(self, state: WorldState, target_id: str, value: Any) -> None:
        node = state.nodes[target_id]
        node.hazard_level = RiskLevel.HIGH if node.hazard_level != RiskLevel.CRITICAL else RiskLevel.CRITICAL
        for hid, h in state.hazards.items():
            if h.location == target_id:
                h.severity = min(1.0, h.severity + float(value or 0.1))
        self._log(state, EventType.HAZARD_INCREASED.value, f"{node.name} classified HIGH RISK")

    def _hazard_spread(self, state: WorldState, target_id: str, value: Any) -> None:
        node = state.nodes[target_id]
        if node.hazard_level == RiskLevel.LOW:
            node.hazard_level = RiskLevel.HIGH
        else:
            node.hazard_level = RiskLevel.HIGH
        for edge in state.edges.values():
            if edge.source == target_id or edge.target == target_id:
                edge.hazard_score = max(edge.hazard_score, 0.7)
        self._log(state, EventType.HAZARD_SPREAD.value, f"Smoke/hazard spread near {node.name}")

    def _exit_blocked(self, state: WorldState, target_id: str, value: Any) -> None:
        node = state.nodes[target_id]
        node.hazard_level = RiskLevel.CRITICAL
        node.open = False
        self._log(state, EventType.EXIT_BLOCKED.value, f"{node.name} marked unsafe / closed")

    def _exit_reopened(self, state: WorldState, target_id: str, value: Any) -> None:
        node = state.nodes[target_id]
        node.hazard_level = RiskLevel.LOW
        node.open = True
        self._log(state, EventType.EXIT_REOPENED.value, f"{node.name} reopened")

    def _route_blocked(self, state: WorldState, target_id: str, value: Any) -> None:
        edge = state.edges[target_id]
        edge.open = False
        self._log(state, EventType.ROUTE_BLOCKED.value, f"Route {edge.id} blocked ({edge.source}–{edge.target})")

    def _route_reopened(self, state: WorldState, target_id: str, value: Any) -> None:
        edge = state.edges[target_id]
        edge.open = True
        edge.hazard_score = min(edge.hazard_score, 0.2)
        self._log(state, EventType.ROUTE_REOPENED.value, f"Route {edge.id} reopened")

    def _crowd_surge(self, state: WorldState, target_id: str, value: Any) -> None:
        amount = int(value or 180)
        node = state.nodes[target_id]
        for edge in state.edges.values():
            if edge.source == target_id or edge.target == target_id:
                edge.external_crowd_load += amount
        self._log(state, EventType.CROWD_SURGE.value, f"Crowd surge at {node.name} (+{amount})")

    def _crowd_normalized(self, state: WorldState, target_id: str, value: Any) -> None:
        for edge in state.edges.values():
            if not target_id or edge.source == target_id or edge.target == target_id:
                edge.external_crowd_load *= 0.4
        self._log(state, EventType.CROWD_NORMALIZED.value, "Crowd density normalized")

    def _flood(self, state: WorldState, target_id: str, value: Any) -> None:
        edge = state.edges[target_id]
        edge.open = False
        edge.hazard_score = 1.0
        hid = f"flood-{target_id}"
        state.hazards[hid] = Hazard(
            id=hid,
            type="FLOOD",
            location=edge.source,
            severity=0.9,
            spread_radius=0.5,
            active=True,
            timestamp=state.sim_time,
        )
        self._log(state, EventType.FLOOD_DETECTED.value, f"Flood detected on {edge.id}")

    def _vehicle(self, state: WorldState, target_id: str, value: Any) -> None:
        rid = target_id or "fire-truck-1"
        if rid == "ambulance-1" or (isinstance(value, str) and value == "AMBULANCE"):
            rid = "ambulance-1"
        responder = state.responders.get(rid)
        if not responder:
            raise KeyError(rid)
        responder.availability = "EN_ROUTE"
        responder.assigned_route = self.agent.plan_responder(state, responder)
        if responder.assigned_route and len(responder.assigned_route) > 1:
            responder.current_edge = None
            responder.progress = 0.0
        self._log(
            state,
            EventType.EMERGENCY_VEHICLE_APPROACHING.value,
            f"{responder.type} approaching {responder.destination} via {len(responder.assigned_route)} hops",
        )

    def _corridor_create(self, state: WorldState, target_id: str, value: Any) -> None:
        rid = target_id or "fire-truck-1"
        responder = state.responders[rid]
        if not responder.assigned_route:
            responder.assigned_route = self.agent.plan_responder(state, responder)
        edges = self.agent.corridor_edges(state, responder)
        for eid in edges:
            state.edges[eid].emergency_restricted = True
        cid = f"corridor-{rid}"
        state.corridors[cid] = EmergencyCorridor(
            id=cid,
            responder_id=rid,
            edge_ids=edges,
            node_ids=list(responder.assigned_route),
            active=True,
        )
        responder.availability = "CORRIDOR_ACTIVE"
        self._log(state, EventType.EMERGENCY_CORRIDOR_CREATED.value, f"Emergency corridor created for {responder.type}")

    def _corridor_release(self, state: WorldState, target_id: str, value: Any) -> None:
        rid = target_id or "fire-truck-1"
        cid = f"corridor-{rid}"
        corridor = state.corridors.get(cid)
        if corridor:
            for eid in corridor.edge_ids:
                if eid in state.edges:
                    state.edges[eid].emergency_restricted = False
            corridor.active = False
        responder = state.responders.get(rid)
        if responder:
            responder.availability = "ON_SCENE" if responder.current_location == responder.destination else "AVAILABLE"
        self._log(state, EventType.EMERGENCY_CORRIDOR_RELEASED.value, "Emergency corridor released")

    def _hazard_resolved(self, state: WorldState, target_id: str, value: Any) -> None:
        node = state.nodes[target_id]
        node.hazard_level = RiskLevel.LOW
        node.open = True
        for h in state.hazards.values():
            if h.location == target_id:
                h.active = False
                h.severity = max(0.0, h.severity - 0.7)
        for edge in state.edges.values():
            if edge.source == target_id or edge.target == target_id:
                edge.hazard_score = max(0.0, edge.hazard_score - 0.55)
                if edge.hazard_score < 0.3 and not any(
                    c.active and edge.id in c.edge_ids for c in state.corridors.values()
                ):
                    pass
        self._log(state, EventType.HAZARD_RESOLVED.value, f"Hazard decreasing at {node.name}")

    def _sensor_failure(self, state: WorldState, target_id: str, value: Any) -> None:
        sensor = state.sensors.get(target_id)
        if not sensor:
            raise KeyError(target_id)
        sensor.status = SensorStatus.FAILED
        state.data_quality = DataQuality.DEGRADED
        siblings = [s for s in state.sensors.values() if s.location == sensor.location and s.id != sensor.id]
        if siblings:
            for s in siblings:
                s.status = SensorStatus.CONFLICT
            state.data_quality = DataQuality.DEGRADED
        self._log(state, EventType.SENSOR_FAILURE.value, f"Sensor {sensor.id} failed at {sensor.location}")

    def _operator_override(self, state: WorldState, target_id: str, value: Any) -> None:
        dest = str(value or "")
        self.override(state, target_id, dest, "Operator override event")

    def _update_hazards(self, state: WorldState) -> None:
        active = [h for h in state.hazards.values() if h.active]
        if not active:
            return
        for hazard in active:
            loc = hazard.location
            if loc in state.nodes and state.nodes[loc].hazard_level == RiskLevel.LOW:
                state.nodes[loc].hazard_level = RiskLevel.HIGH
            for edge in state.edges.values():
                if edge.source == loc or edge.target == loc:
                    edge.hazard_score = min(1.0, max(edge.hazard_score, hazard.severity * 0.5))
                    neighbor = edge.target if edge.source == loc else edge.source
                    if state.tick % 7 == 0 and state.nodes[neighbor].hazard_level == RiskLevel.LOW:
                        state.nodes[neighbor].hazard_level = RiskLevel.MODERATE
                        edge.hazard_score = min(1.0, edge.hazard_score + 0.08)

    def _advance_along_route(self, state: WorldState, route: List[str], current: str, speed: float, remaining: float, progress: float):
        if not route or current == route[-1]:
            return current, remaining, progress, True
        budget = TICK_DT * speed
        loc = current
        prog = progress
        while budget > 0:
            if loc == route[-1]:
                return loc, 0.0, 0.0, True
            try:
                idx = route.index(loc)
            except ValueError:
                return loc, remaining, prog, False
            if idx + 1 >= len(route):
                return loc, 0.0, 0.0, True
            nxt = route[idx + 1]
            edge = get_edge(state, loc, nxt)
            if not edge or not edge.open:
                return loc, remaining, prog, False
            travel = max(edge.base_travel_time * (1.0 + edge.crowd_density), 1.0)
            need = travel * (1.0 - prog)
            if budget >= need:
                budget -= need
                loc = nxt
                prog = 0.0
            else:
                prog += budget / travel
                budget = 0.0
        return loc, max(0.0, 1.0 - prog), prog, loc == route[-1]

    def _move_groups(self, state: WorldState) -> None:
        for group in state.groups.values():
            if group.status in {GroupStatus.EVACUATED, GroupStatus.SHELTERED}:
                continue
            if not group.assigned_route:
                continue
            dest = group.destination
            if group.current_node == dest:
                node = state.nodes[group.current_node]
                group.evacuated = group.size
                group.status = GroupStatus.SHELTERED if node.type in {NodeType.SHELTER, NodeType.ASSEMBLY} else GroupStatus.EVACUATED
                continue
            current, remaining, progress, _ = self._advance_along_route(
                state,
                group.assigned_route,
                group.current_node,
                group.speed,
                group.remaining_distance,
                group.progress,
            )
            if current != group.current_node:
                edge = get_edge(state, group.current_node, current)
                if edge:
                    group.hazard_exposure += edge.hazard_score * group.size * 0.01
            group.current_node = current
            group.remaining_distance = remaining
            group.progress = progress
            group.current_edge = self._next_edge_id(state, group.assigned_route, group.current_node, progress)
            if dest and group.current_node == dest:
                node = state.nodes[group.current_node]
                group.evacuated = group.size
                group.status = GroupStatus.SHELTERED if node.type in {NodeType.SHELTER, NodeType.ASSEMBLY} else GroupStatus.EVACUATED
                group.current_edge = None

    def _move_responders(self, state: WorldState) -> None:
        for responder in state.responders.values():
            if responder.availability not in {"EN_ROUTE", "CORRIDOR_ACTIVE"}:
                continue
            if not responder.assigned_route:
                continue
            current, remaining, progress, done = self._advance_along_route(
                state,
                responder.assigned_route,
                responder.current_location,
                1.35,
                responder.remaining_distance,
                responder.progress,
            )
            responder.current_location = current
            responder.remaining_distance = remaining
            responder.progress = progress
            responder.current_edge = self._next_edge_id(state, responder.assigned_route, responder.current_location, progress)
            if current == responder.destination:
                responder.availability = "ON_SCENE"
                responder.current_edge = None
                state.metrics.responder_delay = state.sim_time

    def _next_edge_id(self, state: WorldState, route: List[str], current: str, progress: float) -> Optional[str]:
        """Return the edge an entity currently occupies; None when it is at a node."""
        if progress <= 0.0:
            return None
        try:
            index = route.index(current)
        except ValueError:
            return None
        if index + 1 >= len(route):
            return None
        edge = get_edge(state, current, route[index + 1])
        return edge.id if edge else None

    def _update_crowd(self, state: WorldState) -> None:
        counts = {nid: 0 for nid in state.nodes}
        for group in state.groups.values():
            if group.status not in {GroupStatus.EVACUATED, GroupStatus.SHELTERED}:
                counts[group.current_node] = counts.get(group.current_node, 0) + group.size
            elif group.destination:
                counts[group.destination] = counts.get(group.destination, 0) + group.evacuated
        for nid, node in state.nodes.items():
            # preserve surge occupancy floor on exits only as max of counted
            node.occupancy = counts.get(nid, 0)
        edge_loads = {edge_id: 0.0 for edge_id in state.edges}
        for group in state.groups.values():
            if group.status == GroupStatus.IN_TRANSIT and group.current_edge in edge_loads:
                edge_loads[group.current_edge] += group.size
        for edge in state.edges.values():
            # Incident-injected crowds disperse gradually. This model does not
            # treat people standing at adjacent buildings as edge congestion.
            edge.external_crowd_load *= 0.985
            reactive = (edge_loads[edge.id] + edge.external_crowd_load) / max(edge.capacity, 1)
            edge.crowd_density = round(min(1.0, reactive), 4)

    def _update_predicted(self, state: WorldState) -> None:
        peak = 0.0
        for edge in state.edges.values():
            edge.predicted_density = predicted_edge_density(state, edge)
            peak = max(peak, edge.predicted_density)
        state.metrics.predicted_peak_congestion = peak

    def _update_sensors(self, state: WorldState) -> None:
        stale_or_fail = 0
        locations = {}
        for sensor in state.sensors.values():
            if sensor.status == SensorStatus.FAILED:
                stale_or_fail += 1
                continue
            node = state.nodes[sensor.location]
            if sensor.type == "SMOKE":
                mapping = {RiskLevel.LOW: 0.05, RiskLevel.MODERATE: 0.4, RiskLevel.HIGH: 0.75, RiskLevel.CRITICAL: 0.98}
                sensor.value = mapping[node.hazard_level]
            elif sensor.type == "TEMPERATURE":
                mapping = {RiskLevel.LOW: 24.0, RiskLevel.MODERATE: 38.0, RiskLevel.HIGH: 62.0, RiskLevel.CRITICAL: 90.0}
                sensor.value = mapping[node.hazard_level]
            elif sensor.type == "CROWD":
                sensor.value = node.occupancy / max(node.capacity, 1)
            else:
                sensor.value = node.occupancy
            sensor.timestamp = state.sim_time
            if sensor.status != SensorStatus.CONFLICT:
                sensor.status = SensorStatus.OK
            locations.setdefault(sensor.location, []).append(sensor)
        conflicts = 0
        for loc, sensors in locations.items():
            if len(sensors) > 1:
                vals = [s.value for s in sensors if s.status != SensorStatus.FAILED]
                if len(vals) >= 2 and abs(vals[0] - vals[1]) > 0.5:
                    conflicts += 1
                    for s in sensors:
                        s.status = SensorStatus.CONFLICT
        if stale_or_fail or conflicts:
            state.data_quality = DataQuality.DEGRADED
        elif all(s.status == SensorStatus.FAILED for s in state.sensors.values()):
            state.data_quality = DataQuality.FAILED
        else:
            state.data_quality = DataQuality.OK

    def _update_incident(self, state: WorldState) -> None:
        levels = [n.hazard_level for n in state.nodes.values()]
        if RiskLevel.CRITICAL in levels:
            sev = RiskLevel.CRITICAL
        elif RiskLevel.HIGH in levels:
            sev = RiskLevel.HIGH
        elif RiskLevel.MODERATE in levels:
            sev = RiskLevel.MODERATE
        else:
            sev = RiskLevel.LOW
        affected = sum(1 for n in state.nodes.values() if n.hazard_level in {RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MODERATE})
        fires = [h for h in state.hazards.values() if h.active and h.type == "FIRE"]
        floods = [h for h in state.hazards.values() if h.active and h.type == "FLOOD"]
        name = "NONE"
        if fires:
            name = "CAMPUS FIRE"
        elif floods:
            name = "FLOOD"
        loc = fires[0].location if fires else (floods[0].location if floods else None)
        evac = "ACTIVE" if any(g.status == GroupStatus.IN_TRANSIT for g in state.groups.values()) else state.incident.evacuation
        if all(g.status in {GroupStatus.EVACUATED, GroupStatus.SHELTERED} for g in state.groups.values()):
            evac = "COMPLETE"
        status = "ACTIVE" if fires or floods or sev in {RiskLevel.HIGH, RiskLevel.CRITICAL} else state.incident.status
        if sev == RiskLevel.LOW and not fires and not floods:
            status = "MONITORING" if state.running else "NORMAL"
            name = "NONE" if status == "NORMAL" else state.incident.name
        msg = state.incident.message
        if fires:
            msg = f"Fire active at {state.nodes[loc].name}" if loc else msg
        state.incident = Incident(
            name=name,
            location=loc,
            severity=sev,
            affected_zones=affected,
            evacuation=evac,
            message=msg,
            status=status,
        )

    def _update_metrics(self, state: WorldState) -> None:
        total = sum(g.size for g in state.groups.values())
        evacuated = sum(g.evacuated for g in state.groups.values())
        in_transit = sum(g.size for g in state.groups.values() if g.status == GroupStatus.IN_TRANSIT)
        waiting = sum(g.size for g in state.groups.values() if g.status == GroupStatus.WAITING)
        at_risk = sum(
            g.size
            for g in state.groups.values()
            if g.status not in {GroupStatus.EVACUATED, GroupStatus.SHELTERED}
            and state.nodes[g.current_node].hazard_level in {RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MODERATE}
        )
        peak = max((e.crowd_density for e in state.edges.values()), default=0.0)
        exposure = sum(g.hazard_exposure for g in state.groups.values())
        if evacuated >= total and total > 0 and state.metrics.evacuation_time == 0:
            state.metrics.evacuation_time = state.sim_time
        state.metrics.total_people = float(total)
        state.metrics.evacuated = float(evacuated)
        state.metrics.at_risk = float(at_risk)
        state.metrics.in_transit = float(in_transit)
        state.metrics.waiting = float(waiting)
        state.metrics.peak_congestion = max(state.metrics.peak_congestion, peak)
        state.metrics.active_hazards = float(sum(1 for h in state.hazards.values() if h.active))
        state.metrics.active_responders = float(
            sum(1 for r in state.responders.values() if r.availability in {"EN_ROUTE", "CORRIDOR_ACTIVE", "ON_SCENE"})
        )
        state.metrics.hazard_exposure = float(exposure)
        state.metrics.completion_rate = float(evacuated / total) if total else 0.0

    def _push_history(self, state: WorldState) -> None:
        util = {}
        for node in state.nodes.values():
            if node.type == NodeType.EXIT:
                util[node.id] = round(node.occupancy / max(node.capacity, 1), 3)
        risk = {"LOW": 0.1, "MODERATE": 0.4, "HIGH": 0.75, "CRITICAL": 1.0}[state.incident.severity.value]
        state.metrics_history.append(
            MetricsPoint(
                sim_time=state.sim_time,
                evacuated=state.metrics.evacuated,
                congestion=max((e.crowd_density for e in state.edges.values()), default=0.0),
                predicted_congestion=state.metrics.predicted_peak_congestion,
                risk=risk,
                exit_utilization=util,
            )
        )
        state.metrics_history = state.metrics_history[-HISTORY_CAP:]

    def _log(self, state: WorldState, typ: str, message: str, payload: Optional[dict] = None) -> None:
        ev = TimelineEvent(
            id=uuid.uuid4().hex[:10],
            sim_time=state.sim_time,
            type=typ,
            message=message,
            payload=payload or {},
        )
        state.timeline.append(ev)
        state.timeline = state.timeline[-TIMELINE_CAP:]
        log.info("sim=%s t=%.1f %s %s", state.id, state.sim_time, typ, message)


def clone_state(state: WorldState) -> WorldState:
    return WorldState.model_validate(copy.deepcopy(state.model_dump()))
