export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type NodeType = 'BUILDING' | 'ZONE' | 'INTERSECTION' | 'EXIT' | 'SHELTER' | 'ASSEMBLY';
export type GroupStatus = 'WAITING' | 'IN_TRANSIT' | 'EVACUATED' | 'SHELTERED' | 'BLOCKED';
export type SimulationMode = 'EVADE_AI' | 'STATIC_BASELINE' | 'DEMO';
export type DataQuality = 'OK' | 'DEGRADED' | 'FAILED';

export interface Node {
  id: string;
  name: string;
  x: number;
  y: number;
  type: NodeType;
  capacity: number;
  occupancy: number;
  hazard_level: RiskLevel;
  safe_zone: boolean;
  accessibility: boolean;
  open: boolean;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  distance: number;
  base_travel_time: number;
  capacity: number;
  crowd_density: number;
  external_crowd_load: number;
  predicted_density: number;
  hazard_score: number;
  open: boolean;
  accessibility: boolean;
  emergency_restricted: boolean;
}

export interface PopulationGroup {
  id: string;
  type: string;
  label: string;
  size: number;
  current_node: string;
  destination?: string | null;
  speed: number;
  status: GroupStatus;
  accessibility_requirement: boolean;
  assigned_route: string[];
  current_edge?: string | null;
  remaining_distance: number;
  progress: number;
  evacuated: number;
  origin_building?: string | null;
  hazard_exposure: number;
}

export interface Hazard {
  id: string;
  type: string;
  location: string;
  severity: number;
  spread_radius: number;
  active: boolean;
  timestamp: number;
}

export interface Responder {
  id: string;
  type: string;
  current_location: string;
  destination: string;
  priority: number;
  availability: string;
  assigned_route: string[];
  current_edge?: string | null;
  remaining_distance: number;
  progress: number;
}

export interface Sensor {
  id: string;
  type: string;
  location: string;
  value: number;
  status: string;
  timestamp: number;
}

export interface EmergencyCorridor {
  id: string;
  responder_id: string;
  edge_ids: string[];
  node_ids: string[];
  active: boolean;
}

export interface CandidateRoute {
  destination: string;
  path: string[];
  cost: number;
  utility: number;
  components: Record<string, number>;
  predicted_congestion: number;
  feasible: boolean;
  rejection_reason?: string | null;
}

export interface RouteChange {
  previous_destination?: string | null;
  new_destination?: string | null;
  previous_route: string[];
  new_route: string[];
  why: string;
  utilization_before: Record<string, number>;
  utilization_after: Record<string, number>;
  delay_delta_seconds: number;
}

export interface Decision {
  decision_id: string;
  timestamp: number;
  sim_time: number;
  group_id: string;
  origin: string;
  selected_destination?: string | null;
  selected_route: string[];
  candidate_routes: CandidateRoute[];
  rejected_routes: CandidateRoute[];
  utility_scores: Record<string, number>;
  reason: string;
  trigger: string;
  situation: string;
  decision_type: string;
  result: string;
  latency_ms: number;
  route_change?: RouteChange | null;
  fallback: boolean;
}

export interface TimelineEvent {
  id: string;
  sim_time: number;
  type: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface Incident {
  name: string;
  location?: string | null;
  severity: RiskLevel;
  affected_zones: number;
  evacuation: string;
  message: string;
  status: string;
}

export interface Metrics {
  total_people: number;
  evacuated: number;
  at_risk: number;
  in_transit: number;
  waiting: number;
  peak_congestion: number;
  predicted_peak_congestion: number;
  active_hazards: number;
  active_responders: number;
  reroutes: number;
  decision_latency_ms: number;
  avg_decision_latency_ms: number;
  tick_time_ms: number;
  avg_tick_time_ms: number;
  hazard_exposure: number;
  completion_rate: number;
  responder_delay: number;
  evacuation_time: number;
  decisions_count: number;
}

export interface MetricsPoint {
  sim_time: number;
  evacuated: number;
  congestion: number;
  predicted_congestion: number;
  risk: number;
  exit_utilization: Record<string, number>;
}

export interface WorldState {
  id: string;
  scenario_id: string;
  mode: SimulationMode;
  seed: number;
  sim_time: number;
  running: boolean;
  tick: number;
  simulation_speed: number;
  nodes: Record<string, Node>;
  edges: Record<string, Edge>;
  groups: Record<string, PopulationGroup>;
  hazards: Record<string, Hazard>;
  responders: Record<string, Responder>;
  sensors: Record<string, Sensor>;
  corridors: Record<string, EmergencyCorridor>;
  decisions: Decision[];
  timeline: TimelineEvent[];
  metrics: Metrics;
  metrics_history: MetricsPoint[];
  incident: Incident;
  weights: Record<string, number>;
  data_quality: DataQuality;
  operator_intervention_required: boolean;
  no_safe_route: boolean;
  demo_active: boolean;
  last_error?: string | null;
}

export interface WsEnvelope {
  type: string;
  timestamp: number;
  sim_time: number;
  state?: WorldState | null;
  decision?: Decision | null;
  incident?: Incident | null;
  message?: string | null;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  event_count: number;
}

export interface BenchmarkScenario {
  scenario_id: string;
  name: string;
  seed: number;
  static_baseline: Record<string, number>;
  evade_ai: Record<string, number>;
  history: {
    baseline: MetricsPoint[];
    evade_ai: MetricsPoint[];
  };
}

export interface BenchmarkResult {
  seed: number;
  note: string;
  wall_time_ms: number;
  scenarios: BenchmarkScenario[];
}

export const emptyMetrics = (): Metrics => ({
  total_people: 0,
  evacuated: 0,
  at_risk: 0,
  in_transit: 0,
  waiting: 0,
  peak_congestion: 0,
  predicted_peak_congestion: 0,
  active_hazards: 0,
  active_responders: 0,
  reroutes: 0,
  decision_latency_ms: 0,
  avg_decision_latency_ms: 0,
  tick_time_ms: 0,
  avg_tick_time_ms: 0,
  hazard_exposure: 0,
  completion_rate: 0,
  responder_delay: 0,
  evacuation_time: 0,
  decisions_count: 0,
});

export const emptyState = (): WorldState => ({
  id: 'default',
  scenario_id: 'campus_fire',
  mode: 'EVADE_AI',
  seed: 42,
  sim_time: 0,
  running: false,
  tick: 0,
  simulation_speed: 1,
  nodes: {},
  edges: {},
  groups: {},
  hazards: {},
  responders: {},
  sensors: {},
  corridors: {},
  decisions: [],
  timeline: [],
  metrics: emptyMetrics(),
  metrics_history: [],
  incident: {
    name: 'NONE',
    location: null,
    severity: 'LOW',
    affected_zones: 0,
    evacuation: 'INACTIVE',
    message: 'Connecting to EVADE-AI backend…',
    status: 'CONNECTING',
  },
  weights: {},
  data_quality: 'OK',
  operator_intervention_required: false,
  no_safe_route: false,
  demo_active: false,
});
