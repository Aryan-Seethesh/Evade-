from __future__ import annotations

import logging
import time
import uuid
from typing import List, Optional

from app.agent.routing import (
    destination_constraint,
    enumerate_candidates,
    get_edge,
    hard_constraint_reason,
    path_components,
    path_edges,
    shortest_unconstrained,
    utility_from_components,
)
from app.models.schema import (
    AgentDecision,
    CandidateRoute,
    GroupStatus,
    NodeType,
    PopulationGroup,
    Responder,
    RouteChange,
    WorldState,
)
from app.simulation.campus import STATIC_PLAN

log = logging.getLogger("evade.agent")

# Prevent oscillation between safe, nearly-equivalent paths as crowd estimates
# update every tick. Hard constraints always bypass this threshold.
REROUTE_UTILITY_MARGIN = 4.0


def _id() -> str:
    return uuid.uuid4().hex[:10]


def _exit_util(state: WorldState) -> dict:
    out = {}
    for node in state.nodes.values():
        if node.type == NodeType.EXIT:
            out[node.id] = round(node.occupancy / max(node.capacity, 1), 3)
    return out


class EvacuationAgent:
    """Utility-based agent with hard safety constraints and explainable decisions."""

    def plan_group(
        self,
        state: WorldState,
        group: PopulationGroup,
        trigger: str,
        situation: str,
    ) -> AgentDecision:
        started = time.perf_counter()
        previous_dest = group.destination
        previous_route = list(group.assigned_route)

        accepted, rejected = enumerate_candidates(state, group)
        latency = (time.perf_counter() - started) * 1000.0

        if not accepted:
            group.status = GroupStatus.BLOCKED
            group.assigned_route = []
            group.destination = None
            reason = "NO SAFE ROUTE AVAILABLE — OPERATOR INTERVENTION REQUIRED"
            return AgentDecision(
                decision_id=_id(),
                timestamp=state.sim_time,
                sim_time=state.sim_time,
                group_id=group.id,
                origin=group.current_node,
                selected_destination=None,
                selected_route=[],
                candidate_routes=[],
                rejected_routes=rejected,
                utility_scores={},
                reason=reason,
                trigger=trigger,
                situation=situation,
                decision_type="NO_SAFE_ROUTE",
                result="OPERATOR_REQUIRED",
                latency_ms=round(latency, 3),
            )

        best = accepted[0]
        changed = best.path != previous_route or best.destination != previous_dest

        if changed and previous_route and previous_dest:
            current_route = self._remaining_route(group.current_node, previous_route)
            current_safe = self._route_is_safe(state, group, current_route, previous_dest)
            if current_safe:
                current_utility = utility_from_components(state, path_components(state, current_route, group))
                if best.utility - current_utility < REROUTE_UTILITY_MARGIN:
                    return AgentDecision(
                        decision_id=_id(),
                        timestamp=state.sim_time,
                        sim_time=state.sim_time,
                        group_id=group.id,
                        origin=group.current_node,
                        selected_destination=previous_dest,
                        selected_route=current_route,
                        candidate_routes=accepted[:6],
                        rejected_routes=rejected[:8],
                        utility_scores={c.destination: c.utility for c in accepted},
                        reason=(
                            "Existing route remains feasible. Candidate improvement was below "
                            f"the {REROUTE_UTILITY_MARGIN:.0f}-point reroute threshold."
                        ),
                        trigger=trigger,
                        situation=situation,
                        decision_type="HOLD_ROUTE",
                        result="UNCHANGED",
                        latency_ms=round(latency, 3),
                    )
        route_change = None
        if changed and previous_dest:
            delay = 0.0
            if previous_route:
                prev_time = sum(
                    (state.edges[eid].base_travel_time if eid in state.edges else 0.0)
                    for eid in []  # filled below
                )
            prev_time = 0.0
            new_time = best.components.get("travel_time", 0.0)
            for a, b in zip(previous_route, previous_route[1:]):
                for edge in state.edges.values():
                    if {edge.source, edge.target} == {a, b}:
                        prev_time += edge.base_travel_time
            route_change = RouteChange(
                previous_destination=previous_dest,
                new_destination=best.destination,
                previous_route=previous_route,
                new_route=best.path,
                why=self._why(best, rejected, trigger),
                utilization_before=_exit_util(state),
                utilization_after=_exit_util(state),
                delay_delta_seconds=round(new_time - prev_time, 2),
            )

        group.assigned_route = best.path
        group.destination = best.destination
        if group.status != GroupStatus.EVACUATED:
            group.status = GroupStatus.IN_TRANSIT
        dest_node = state.nodes[best.destination]
        dest_name = dest_node.name
        scores = {c.destination: c.utility for c in accepted}

        decision_type = "REROUTE" if changed and previous_dest else "ASSIGN"
        reason = (
            f"Selected {dest_name} ({best.destination}) with utility {best.utility:.1f}. "
            f"Lowest feasible dynamic cost after hard safety filters. "
            f"Travel {best.components.get('travel_time')}s, "
            f"hazard {best.components.get('hazard_exposure')}, "
            f"predicted congestion {best.components.get('predicted_congestion')}."
        )
        return AgentDecision(
            decision_id=_id(),
            timestamp=state.sim_time,
            sim_time=state.sim_time,
            group_id=group.id,
            origin=group.current_node,
            selected_destination=best.destination,
            selected_route=best.path,
            candidate_routes=accepted[:6],
            rejected_routes=rejected[:8],
            utility_scores=scores,
            reason=reason,
            trigger=trigger,
            situation=situation,
            decision_type=decision_type,
            result="APPLIED" if changed or not previous_dest else "UNCHANGED",
            latency_ms=round(latency, 3),
            route_change=route_change,
        )

    @staticmethod
    def _remaining_route(current_node: str, route: List[str]) -> List[str]:
        try:
            return route[route.index(current_node):]
        except ValueError:
            return route

    @staticmethod
    def _route_is_safe(
        state: WorldState,
        group: PopulationGroup,
        route: List[str],
        destination: str,
    ) -> bool:
        if len(route) < 2 or route[-1] != destination:
            return False
        if destination_constraint(state, destination, group):
            return False
        for source, target in zip(route, route[1:]):
            edge = get_edge(state, source, target)
            if not edge or hard_constraint_reason(state, edge, group):
                return False
        return True

    def _why(self, best: CandidateRoute, rejected: List[CandidateRoute], trigger: str) -> str:
        rej = rejected[0].rejection_reason if rejected else "other feasible exits had lower utility"
        return (
            f"Trigger: {trigger}. Selected {best.destination} because it maximized utility "
            f"({best.utility:.1f}) under safety constraints. Rejected alternatives: {rej}."
        )

    def replan(
        self,
        state: WorldState,
        trigger: str,
        situation: str,
        group_ids: Optional[List[str]] = None,
    ) -> List[AgentDecision]:
        decisions: List[AgentDecision] = []
        groups = [
            g
            for g in state.groups.values()
            if g.status not in {GroupStatus.EVACUATED, GroupStatus.SHELTERED}
            and (group_ids is None or g.id in group_ids)
        ]
        try:
            for group in groups:
                # A route assignment is an action in the environment, not a
                # visual suggestion. Do not teleport/restart a group while it
                # is partway through a safe edge; evaluate it at the next
                # junction. An unsafe/blocked active route remains eligible
                # for immediate recovery planning.
                if group.progress > 0 and group.assigned_route:
                    tail = self._remaining_route(group.current_node, group.assigned_route)
                    if group.destination and self._route_is_safe(state, group, tail, group.destination):
                        continue
                previous_route = list(group.assigned_route)
                decision = self.plan_group(state, group, trigger, situation)
                if decision.result != "UNCHANGED":
                    if decision.result == "APPLIED" and decision.selected_route != previous_route:
                        # Replanning from a blocked edge is modeled as a return
                        # to the current graph node before taking the new path.
                        group.progress = 0.0
                        group.remaining_distance = 0.0
                        group.current_edge = None
                    decisions.append(decision)
                    if decision.decision_type == "REROUTE":
                        state.metrics.reroutes += 1
                    if decision.decision_type == "NO_SAFE_ROUTE":
                        state.no_safe_route = True
                        state.operator_intervention_required = True
                    else:
                        state.no_safe_route = False
                    state.metrics.decision_latency_ms = decision.latency_ms
                    n = state.metrics.decisions_count
                    state.metrics.avg_decision_latency_ms = (
                        (state.metrics.avg_decision_latency_ms * n + decision.latency_ms) / (n + 1)
                    )
                    state.metrics.decisions_count = n + 1
        except Exception:
            log.exception("Agent failure — applying fallback emergency procedure")
            decisions.extend(self.fallback(state, trigger, situation, groups))
        if decisions:
            state.decisions.extend(decisions)
            state.decisions = state.decisions[-120:]
        if not any(d.decision_type == "NO_SAFE_ROUTE" for d in decisions):
            if all(
                g.status in {GroupStatus.EVACUATED, GroupStatus.SHELTERED} or g.assigned_route
                for g in state.groups.values()
            ):
                state.operator_intervention_required = False
                state.no_safe_route = False
        return decisions

    def fallback(
        self,
        state: WorldState,
        trigger: str,
        situation: str,
        groups: List[PopulationGroup],
    ) -> List[AgentDecision]:
        decisions: List[AgentDecision] = []
        for group in groups:
            dest = STATIC_PLAN.get(group.origin_building or group.current_node, "exit_south")
            path = shortest_unconstrained(state, group.current_node, dest)
            if path:
                group.assigned_route = path
                group.destination = dest
                group.status = GroupStatus.IN_TRANSIT
                reason = "Fallback emergency procedure: static nearest planned exit using open edges only."
                dtype = "FALLBACK"
                result = "APPLIED"
            else:
                group.status = GroupStatus.BLOCKED
                reason = "NO SAFE ROUTE AVAILABLE — OPERATOR INTERVENTION REQUIRED"
                dtype = "NO_SAFE_ROUTE"
                result = "OPERATOR_REQUIRED"
                state.operator_intervention_required = True
                state.no_safe_route = True
                path = []
                dest = None
            decisions.append(
                AgentDecision(
                    decision_id=_id(),
                    timestamp=state.sim_time,
                    sim_time=state.sim_time,
                    group_id=group.id,
                    origin=group.current_node,
                    selected_destination=dest,
                    selected_route=path or [],
                    reason=reason,
                    trigger=trigger,
                    situation=situation,
                    decision_type=dtype,
                    result=result,
                    fallback=True,
                )
            )
        return decisions

    def plan_responder(self, state: WorldState, responder: Responder) -> List[str]:
        dummy = PopulationGroup(
            id=responder.id,
            label=responder.type,
            size=1,
            current_node=responder.current_location,
            type="RESPONDER",
        )
        dests = [responder.destination]
        accepted, _ = enumerate_candidates(state, dummy, for_responder=True, destinations=dests)
        if accepted:
            return accepted[0].path
        path = shortest_unconstrained(state, responder.current_location, responder.destination)
        return path or [responder.current_location]

    def corridor_edges(self, state: WorldState, responder: Responder) -> List[str]:
        return path_edges(state, responder.assigned_route)
