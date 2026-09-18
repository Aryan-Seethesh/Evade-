from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NodeType(str, Enum):
    BUILDING = "BUILDING"
    ZONE = "ZONE"
    INTERSECTION = "INTERSECTION"
    EXIT = "EXIT"
    SHELTER = "SHELTER"
    ASSEMBLY = "ASSEMBLY"


class EdgeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESTRICTED = "RESTRICTED"


class GroupStatus(str, Enum):
    WAITING = "WAITING"
    IN_TRANSIT = "IN_TRANSIT"
    EVACUATED = "EVACUATED"
    SHELTERED = "SHELTERED"
    BLOCKED = "BLOCKED"


class SensorStatus(str, Enum):
    OK = "OK"
    STALE = "STALE"
    FAILED = "FAILED"
    CONFLICT = "CONFLICT"


class DataQuality(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class SimulationMode(str, Enum):
    EVADE_AI = "EVADE_AI"
    STATIC_BASELINE = "STATIC_BASELINE"
    DEMO = "DEMO"


class EventType(str, Enum):
    FIRE_DETECTED = "FIRE_DETECTED"
    HAZARD_INCREASED = "HAZARD_INCREASED"
    HAZARD_SPREAD = "HAZARD_SPREAD"
    EXIT_BLOCKED = "EXIT_BLOCKED"
    EXIT_REOPENED = "EXIT_REOPENED"
    ROUTE_BLOCKED = "ROUTE_BLOCKED"
    ROUTE_REOPENED = "ROUTE_REOPENED"
    CROWD_SURGE = "CROWD_SURGE"
    CROWD_NORMALIZED = "CROWD_NORMALIZED"
    FLOOD_DETECTED = "FLOOD_DETECTED"
    EMERGENCY_VEHICLE_APPROACHING = "EMERGENCY_VEHICLE_APPROACHING"
    EMERGENCY_CORRIDOR_CREATED = "EMERGENCY_CORRIDOR_CREATED"
    EMERGENCY_CORRIDOR_RELEASED = "EMERGENCY_CORRIDOR_RELEASED"
    HAZARD_RESOLVED = "HAZARD_RESOLVED"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    OPERATOR_OVERRIDE = "OPERATOR_OVERRIDE"
    DEMO_STAGE = "DEMO_STAGE"


class RoutingWeights(BaseModel):
    travel_time: float = 1.0
    congestion: float = 2.4
    hazard: float = 12.0
    emergency_conflict: float = 8.0
    accessibility: float = 40.0
    predicted_congestion: float = 2.0


class Node(BaseModel):
    id: str
    name: str
    x: float
    y: float
    type: NodeType = NodeType.INTERSECTION
    capacity: int = 1000
    occupancy: int = 0
    hazard_level: RiskLevel = RiskLevel.LOW
    safe_zone: bool = False
    accessibility: bool = True
    open: bool = True


class Edge(BaseModel):
    id: str
    source: str
    target: str
    distance: float = Field(gt=0)
    base_travel_time: float = Field(gt=0)
    capacity: int = Field(gt=0)
    crowd_density: float = Field(default=0.0, ge=0.0, le=1.0)
    # Incident-injected crowd load; kept separate from groups actively moving.
    external_crowd_load: float = Field(default=0.0, ge=0.0)
    predicted_density: float = Field(default=0.0, ge=0.0, le=1.0)
    hazard_score: float = Field(default=0.0, ge=0.0, le=1.0)
    open: bool = True
    accessibility: bool = True
    emergency_restricted: bool = False


class PopulationGroup(BaseModel):
    id: str
    type: str = "CIVILIAN"
    label: str
    size: int = Field(gt=0)
    current_node: str
    destination: Optional[str] = None
    speed: float = Field(default=1.0, gt=0)
    status: GroupStatus = GroupStatus.WAITING
    accessibility_requirement: bool = False
    assigned_route: List[str] = Field(default_factory=list)
    current_edge: Optional[str] = None
    remaining_distance: float = 0.0
    progress: float = 0.0
    evacuated: int = 0
    origin_building: Optional[str] = None
    hazard_exposure: float = 0.0


class Hazard(BaseModel):
    id: str
    type: str
    location: str
    severity: float = Field(ge=0.0, le=1.0)
    spread_radius: float = 0.0
    active: bool = True
    timestamp: float = 0.0


class Responder(BaseModel):
    id: str
    type: str
    current_location: str
    destination: str
    priority: int = 1
    availability: str = "AVAILABLE"
    assigned_route: List[str] = Field(default_factory=list)
    current_edge: Optional[str] = None
    remaining_distance: float = 0.0
    progress: float = 0.0


class Sensor(BaseModel):
    id: str
    type: str
    location: str
    value: float = 0.0
    status: SensorStatus = SensorStatus.OK
    timestamp: float = 0.0


class EmergencyCorridor(BaseModel):
    id: str
    responder_id: str
    edge_ids: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    active: bool = True


class CandidateRoute(BaseModel):
    destination: str
    path: List[str] = Field(default_factory=list)
    cost: float = 0.0
    utility: float = 0.0
    components: Dict[str, float] = Field(default_factory=dict)
    predicted_congestion: float = 0.0
    feasible: bool = True
    rejection_reason: Optional[str] = None


class RouteChange(BaseModel):
    previous_destination: Optional[str] = None
    new_destination: Optional[str] = None
    previous_route: List[str] = Field(default_factory=list)
    new_route: List[str] = Field(default_factory=list)
    why: str = ""
    utilization_before: Dict[str, float] = Field(default_factory=dict)
    utilization_after: Dict[str, float] = Field(default_factory=dict)
    delay_delta_seconds: float = 0.0


class AgentDecision(BaseModel):
    decision_id: str
    timestamp: float
    sim_time: float
    group_id: str
    origin: str
    selected_destination: Optional[str] = None
    selected_route: List[str] = Field(default_factory=list)
    candidate_routes: List[CandidateRoute] = Field(default_factory=list)
    rejected_routes: List[CandidateRoute] = Field(default_factory=list)
    utility_scores: Dict[str, float] = Field(default_factory=dict)
    reason: str
    trigger: str
    situation: str = ""
    decision_type: str = "ASSIGN"
    result: str = "APPLIED"
    latency_ms: float = 0.0
    route_change: Optional[RouteChange] = None
    fallback: bool = False


class TimelineEvent(BaseModel):
    id: str
    sim_time: float
    type: str
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    name: str = "NONE"
    location: Optional[str] = None
    severity: RiskLevel = RiskLevel.LOW
    affected_zones: int = 0
    evacuation: str = "INACTIVE"
    message: str = "No active incident"
    status: str = "NORMAL"


class Metrics(BaseModel):
    total_people: float = 0.0
    evacuated: float = 0.0
    at_risk: float = 0.0
    in_transit: float = 0.0
    waiting: float = 0.0
    peak_congestion: float = 0.0
    predicted_peak_congestion: float = 0.0
    active_hazards: float = 0.0
    active_responders: float = 0.0
    reroutes: float = 0.0
    decision_latency_ms: float = 0.0
    avg_decision_latency_ms: float = 0.0
    tick_time_ms: float = 0.0
    avg_tick_time_ms: float = 0.0
    hazard_exposure: float = 0.0
    completion_rate: float = 0.0
    responder_delay: float = 0.0
    evacuation_time: float = 0.0
    decisions_count: float = 0.0


class MetricsPoint(BaseModel):
    sim_time: float
    evacuated: float
    congestion: float
    predicted_congestion: float
    risk: float
    exit_utilization: Dict[str, float] = Field(default_factory=dict)


class ScriptedEvent(BaseModel):
    at_time: float
    event_type: EventType
    target_id: str = ""
    value: Any = None
    message: Optional[str] = None


class WorldState(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str = "default"
    scenario_id: str = "campus_fire"
    mode: SimulationMode = SimulationMode.EVADE_AI
    seed: int = 42
    sim_time: float = 0.0
    running: bool = False
    tick: int = 0
    simulation_speed: float = 1.0
    nodes: Dict[str, Node]
    edges: Dict[str, Edge]
    groups: Dict[str, PopulationGroup]
    hazards: Dict[str, Hazard] = Field(default_factory=dict)
    responders: Dict[str, Responder] = Field(default_factory=dict)
    sensors: Dict[str, Sensor] = Field(default_factory=dict)
    corridors: Dict[str, EmergencyCorridor] = Field(default_factory=dict)
    decisions: List[AgentDecision] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    metrics_history: List[MetricsPoint] = Field(default_factory=list)
    incident: Incident = Field(default_factory=Incident)
    weights: RoutingWeights = Field(default_factory=RoutingWeights)
    data_quality: DataQuality = DataQuality.OK
    operator_intervention_required: bool = False
    no_safe_route: bool = False
    demo_active: bool = False
    scripted_events: List[ScriptedEvent] = Field(default_factory=list)
    fired_script_indices: List[int] = Field(default_factory=list)
    world_signature: str = ""
    last_error: Optional[str] = None


class WsMessage(BaseModel):
    type: str
    timestamp: float
    sim_time: float = 0.0
    state: Optional[WorldState] = None
    decision: Optional[AgentDecision] = None
    incident: Optional[Incident] = None
    message: Optional[str] = None


class EventPayload(BaseModel):
    event_type: str
    target_id: str = ""
    value: Any = None


class SpeedPayload(BaseModel):
    speed: float = Field(ge=0.25, le=10.0)


class CreateSimulationPayload(BaseModel):
    scenario_id: str = "campus_fire"
    mode: SimulationMode = SimulationMode.EVADE_AI
    seed: int = 42
    demo: bool = False


class OverridePayload(BaseModel):
    group_id: str
    destination: str
    reason: str = "Operator override"
