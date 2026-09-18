from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

import networkx as nx

from app.models.schema import CandidateRoute, Edge, GroupStatus, NodeType, PopulationGroup, RiskLevel, WorldState


CRITICAL_HAZARD_THRESHOLD = 0.85


def edge_key(state: WorldState, a: str, b: str) -> Optional[str]:
    for edge in state.edges.values():
        if {edge.source, edge.target} == {a, b}:
            return edge.id
    return None


def get_edge(state: WorldState, a: str, b: str) -> Optional[Edge]:
    eid = edge_key(state, a, b)
    return state.edges.get(eid) if eid else None


def predicted_occupancy(state: WorldState, node_id: str) -> int:
    current = state.nodes[node_id].occupancy
    incoming = 0
    for group in state.groups.values():
        if group.status in {GroupStatus.EVACUATED, GroupStatus.SHELTERED}:
            continue
        if group.destination == node_id and group.current_node != node_id:
            incoming += group.size
        elif group.assigned_route and node_id in group.assigned_route[1:]:
            incoming += int(group.size * 0.5)
    return current + incoming


def predicted_edge_density(state: WorldState, edge: Edge) -> float:
    load = 0
    for group in state.groups.values():
        if not group.assigned_route or group.status not in {GroupStatus.IN_TRANSIT, GroupStatus.WAITING}:
            continue
        for a, b in zip(group.assigned_route, group.assigned_route[1:]):
            if {a, b} == {edge.source, edge.target}:
                load += group.size
                break
    return min(1.0, max(edge.crowd_density, load / max(edge.capacity, 1)))


def hard_constraint_reason(
    state: WorldState,
    edge: Edge,
    group: Optional[PopulationGroup],
    *,
    for_responder: bool = False,
) -> Optional[str]:
    if not edge.open:
        return "Blocked route — edge is closed"
    src = state.nodes[edge.source]
    dst = state.nodes[edge.target]
    if src.hazard_level == RiskLevel.CRITICAL or dst.hazard_level == RiskLevel.CRITICAL:
        return "Critical hazard — route impossible"
    if edge.hazard_score >= CRITICAL_HAZARD_THRESHOLD:
        return "Critical hazard on edge — route impossible"
    if not src.open or not dst.open:
        return "Closed node — unavailable"
    if not for_responder and edge.emergency_restricted:
        return "Emergency-only corridor — civilian route prohibited"
    if group and group.accessibility_requirement and (not edge.accessibility or not dst.accessibility):
        return "Inaccessible path — unavailable to restricted groups"
    return None


def destination_constraint(state: WorldState, dest_id: str, group: PopulationGroup) -> Optional[str]:
    node = state.nodes[dest_id]
    if not node.open:
        return "Closed exit — unavailable"
    if node.hazard_level == RiskLevel.CRITICAL:
        return "Closed/critical exit — unavailable"
    if group.accessibility_requirement and not node.accessibility:
        return "Destination is not accessibility-compliant"
    predicted = predicted_occupancy(state, dest_id)
    if predicted > node.capacity * 1.05 and node.occupancy >= node.capacity:
        return "Insufficient remaining capacity"
    return None


def build_graph(
    state: WorldState,
    group: Optional[PopulationGroup] = None,
    *,
    for_responder: bool = False,
    ignore_congestion: bool = False,
) -> nx.Graph:
    graph = nx.Graph()
    for node in state.nodes.values():
        graph.add_node(node.id)
    w = state.weights
    for edge in state.edges.values():
        reason = hard_constraint_reason(state, edge, group, for_responder=for_responder)
        if reason:
            continue
        reactive = 0.0 if ignore_congestion else edge.crowd_density
        predicted = 0.0 if ignore_congestion else predicted_edge_density(state, edge)
        congestion = max(reactive, predicted)
        travel = edge.base_travel_time * w.travel_time
        cong = edge.base_travel_time * w.congestion * reactive
        pred = edge.base_travel_time * w.predicted_congestion * predicted
        hazard = edge.hazard_score * w.hazard * 8.0
        src = state.nodes[edge.source]
        dst = state.nodes[edge.target]
        for node in (src, dst):
            if node.hazard_level == RiskLevel.HIGH:
                hazard += w.hazard * 4.0
            elif node.hazard_level == RiskLevel.MODERATE:
                hazard += w.hazard * 1.5
        emergency = w.emergency_conflict * 6.0 if (edge.emergency_restricted and not for_responder) else 0.0
        access = 0.0
        if group and group.accessibility_requirement and not edge.accessibility:
            access = w.accessibility
        cost = travel + cong + pred + hazard + emergency + access
        graph.add_edge(
            edge.source,
            edge.target,
            weight=max(cost, 0.01),
            edge_id=edge.id,
            reactive=reactive,
            predicted=predicted,
        )
    return graph


def path_components(state: WorldState, path: List[str], group: Optional[PopulationGroup]) -> Dict[str, float]:
    travel = 0.0
    hazard = 0.0
    cong = 0.0
    pred = 0.0
    emergency = 0.0
    for a, b in zip(path, path[1:]):
        edge = get_edge(state, a, b)
        if not edge:
            continue
        travel += edge.base_travel_time
        hazard = max(hazard, edge.hazard_score)
        cong = max(cong, edge.crowd_density)
        pred = max(pred, predicted_edge_density(state, edge))
        if edge.emergency_restricted:
            emergency = 1.0
    dest = path[-1]
    occupancy_ratio = predicted_occupancy(state, dest) / max(state.nodes[dest].capacity, 1)
    access_ok = 1.0 if (not group or not group.accessibility_requirement or state.nodes[dest].accessibility) else 0.0
    return {
        "travel_time": round(travel, 2),
        "hazard_exposure": round(hazard, 3),
        "congestion": round(cong, 3),
        "predicted_congestion": round(pred, 3),
        "emergency_conflict": emergency,
        "destination_utilization": round(min(1.0, occupancy_ratio), 3),
        "accessibility_ok": access_ok,
    }


def utility_from_components(state: WorldState, components: Dict[str, float]) -> float:
    """
    UTILITY =
        safety benefit
      + efficiency benefit
      + accessibility benefit
      - hazard exposure
      - congestion
      - travel time
      - emergency conflict
    """
    w = state.weights
    safety = 100.0 * (1.0 - components["hazard_exposure"])
    efficiency = 40.0 / (1.0 + components["travel_time"] / 40.0)
    access = 12.0 * components["accessibility_ok"]
    return (
        safety
        + efficiency
        + access
        - w.hazard * components["hazard_exposure"] * 4.0
        - w.congestion * components["congestion"] * 10.0
        - w.predicted_congestion * components["predicted_congestion"] * 10.0
        - w.travel_time * (components["travel_time"] / 10.0)
        - w.emergency_conflict * components["emergency_conflict"] * 8.0
        - components["destination_utilization"] * 18.0
    )


def enumerate_candidates(
    state: WorldState,
    group: PopulationGroup,
    *,
    for_responder: bool = False,
    destinations: Optional[Iterable[str]] = None,
) -> Tuple[List[CandidateRoute], List[CandidateRoute]]:
    dests = list(destinations) if destinations is not None else [
        n.id
        for n in state.nodes.values()
        if n.type in {NodeType.EXIT, NodeType.SHELTER} and n.safe_zone
    ]
    accepted: List[CandidateRoute] = []
    rejected: List[CandidateRoute] = []
    graph = build_graph(state, group, for_responder=for_responder)

    for dest in dests:
        dest_reason = None if for_responder else destination_constraint(state, dest, group)
        if dest_reason:
            rejected.append(
                CandidateRoute(destination=dest, feasible=False, rejection_reason=dest_reason)
            )
            continue
        if dest not in graph:
            rejected.append(
                CandidateRoute(destination=dest, feasible=False, rejection_reason="Destination isolated from graph")
            )
            continue
        if group.current_node not in graph:
            rejected.append(
                CandidateRoute(destination=dest, feasible=False, rejection_reason="Origin isolated by hazards/closures")
            )
            continue
        try:
            path = nx.shortest_path(graph, group.current_node, dest, weight="weight")
            cost = float(nx.shortest_path_length(graph, group.current_node, dest, weight="weight"))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            rejected.append(
                CandidateRoute(destination=dest, feasible=False, rejection_reason="No path under current constraints")
            )
            continue
        comps = path_components(state, path, group)
        util = utility_from_components(state, comps)
        accepted.append(
            CandidateRoute(
                destination=dest,
                path=path,
                cost=round(cost, 3),
                utility=round(util, 3),
                components=comps,
                predicted_congestion=comps["predicted_congestion"],
                feasible=True,
            )
        )
    accepted.sort(key=lambda c: c.utility, reverse=True)
    return accepted, rejected


def shortest_unconstrained(state: WorldState, start: str, dest: str) -> Optional[List[str]]:
    graph = nx.Graph()
    for edge in state.edges.values():
        if edge.open:
            graph.add_edge(edge.source, edge.target, weight=edge.base_travel_time)
    try:
        return nx.shortest_path(graph, start, dest, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def path_edges(state: WorldState, path: List[str]) -> List[str]:
    ids: List[str] = []
    for a, b in zip(path, path[1:]):
        eid = edge_key(state, a, b)
        if eid:
            ids.append(eid)
    return ids


def signature(state: WorldState) -> str:
    parts = []
    for edge in sorted(state.edges.values(), key=lambda e: e.id):
        parts.append(f"{edge.id}:{int(edge.open)}:{edge.emergency_restricted}:{round(edge.hazard_score,2)}:{round(edge.crowd_density,2)}")
    for node in sorted(state.nodes.values(), key=lambda n: n.id):
        parts.append(f"{node.id}:{node.hazard_level}:{int(node.open)}:{node.occupancy}")
    for hz in sorted(state.hazards.values(), key=lambda h: h.id):
        parts.append(f"h:{hz.id}:{hz.active}:{round(hz.severity,2)}")
    return "|".join(parts)
