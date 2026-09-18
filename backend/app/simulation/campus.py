from __future__ import annotations

from typing import Dict, List, Tuple

from app.models.schema import Edge, Node, NodeType, PopulationGroup, Responder, Sensor, SensorStatus


def _n(
    id: str,
    name: str,
    x: float,
    y: float,
    typ: NodeType,
    capacity: int,
    *,
    safe: bool = False,
    accessible: bool = True,
) -> Node:
    return Node(
        id=id,
        name=name,
        x=x,
        y=y,
        type=typ,
        capacity=capacity,
        safe_zone=safe,
        accessibility=accessible,
        open=True,
    )


def _e(
    id: str,
    a: str,
    b: str,
    distance: float,
    time: float,
    cap: int,
    *,
    accessible: bool = True,
) -> Edge:
    return Edge(
        id=id,
        source=a,
        target=b,
        distance=distance,
        base_travel_time=time,
        capacity=cap,
        accessibility=accessible,
        open=True,
    )


def campus_graph() -> Tuple[Dict[str, Node], Dict[str, Edge]]:
    nodes = {
        "building_a": _n("building_a", "Building A", 14, 20, NodeType.BUILDING, 500),
        "building_b": _n("building_b", "Building B", 14, 58, NodeType.BUILDING, 560),
        "building_c": _n("building_c", "Building C", 40, 80, NodeType.BUILDING, 480),
        "building_d": _n("building_d", "Building D", 74, 26, NodeType.BUILDING, 420),
        "quad": _n("quad", "Central Quad", 46, 48, NodeType.ZONE, 400, safe=True),
        "j_north": _n("j_north", "North Junction", 34, 22, NodeType.INTERSECTION, 320),
        "j_west": _n("j_west", "West Junction", 22, 40, NodeType.INTERSECTION, 280),
        "j_south": _n("j_south", "South Junction", 48, 78, NodeType.INTERSECTION, 340),
        "j_east": _n("j_east", "East Junction", 70, 52, NodeType.INTERSECTION, 340),
        "exit_north": _n("exit_north", "Exit A — North", 82, 10, NodeType.EXIT, 650, safe=True),
        "exit_south": _n("exit_south", "Exit B — South", 82, 90, NodeType.EXIT, 900, safe=True),
        "exit_east": _n("exit_east", "Exit C — East", 94, 48, NodeType.EXIT, 700, safe=True),
        "exit_west": _n("exit_west", "Exit D — West", 6, 38, NodeType.EXIT, 380, safe=True, accessible=False),
        "shelter": _n("shelter", "Assembly Shelter", 62, 48, NodeType.SHELTER, 1600, safe=True),
        "assembly": _n("assembly", "Assembly Area", 90, 74, NodeType.ASSEMBLY, 1200, safe=True),
    }
    edges = {
        "e_a_jn": _e("e_a_jn", "building_a", "j_north", 80, 28, 250),
        "e_a_jw": _e("e_a_jw", "building_a", "j_west", 70, 24, 220),
        "e_b_jw": _e("e_b_jw", "building_b", "j_west", 55, 22, 260),
        "e_b_quad": _e("e_b_quad", "building_b", "quad", 90, 32, 240),
        "e_c_js": _e("e_c_js", "building_c", "j_south", 40, 16, 260),
        "e_d_je": _e("e_d_je", "building_d", "j_east", 70, 26, 250),
        "e_d_jn": _e("e_d_jn", "building_d", "j_north", 110, 38, 180),
        "e_jn_quad": _e("e_jn_quad", "j_north", "quad", 70, 22, 320),
        "e_jw_quad": _e("e_jw_quad", "j_west", "quad", 65, 20, 300),
        "e_js_quad": _e("e_js_quad", "j_south", "quad", 80, 24, 360),
        "e_je_quad": _e("e_je_quad", "j_east", "quad", 60, 18, 360),
        "e_jn_en": _e("e_jn_en", "j_north", "exit_north", 85, 26, 300),
        "e_js_es": _e("e_js_es", "j_south", "exit_south", 80, 24, 380),
        "e_je_ee": _e("e_je_ee", "j_east", "exit_east", 55, 18, 340),
        "e_jw_ew": _e("e_jw_ew", "j_west", "exit_west", 50, 16, 200, accessible=False),
        "e_quad_sh": _e("e_quad_sh", "quad", "shelter", 40, 12, 500),
        "e_je_sh": _e("e_je_sh", "j_east", "shelter", 35, 12, 420),
        "e_js_as": _e("e_js_as", "j_south", "assembly", 95, 30, 280),
        "e_ee_as": _e("e_ee_as", "exit_east", "assembly", 70, 22, 260),
        "e_jn_je": _e("e_jn_je", "j_north", "j_east", 90, 28, 260),
        "e_js_je": _e("e_js_je", "j_south", "j_east", 75, 24, 300),
    }
    return nodes, edges


STATIC_PLAN: Dict[str, str] = {
    "building_a": "exit_north",
    "building_b": "exit_north",
    "building_c": "exit_south",
    "building_d": "exit_south",
}


def default_groups() -> Dict[str, PopulationGroup]:
    return {
        "students_a": PopulationGroup(
            id="students_a",
            type="STUDENTS",
            label="Students — Block A",
            size=420,
            current_node="building_a",
            origin_building="building_a",
        ),
        "students_b": PopulationGroup(
            id="students_b",
            type="STUDENTS",
            label="Students — Block B",
            size=520,
            current_node="building_b",
            origin_building="building_b",
        ),
        "faculty": PopulationGroup(
            id="faculty",
            type="STAFF",
            label="Faculty & Staff",
            size=180,
            current_node="building_c",
            origin_building="building_c",
            accessibility_requirement=True,
            speed=0.85,
        ),
        "visitors": PopulationGroup(
            id="visitors",
            type="VISITORS",
            label="Visitors",
            size=120,
            current_node="building_d",
            origin_building="building_d",
        ),
        "lab_group": PopulationGroup(
            id="lab_group",
            type="STUDENTS",
            label="Lab Occupants — Block B",
            size=90,
            current_node="building_b",
            origin_building="building_b",
            speed=0.9,
        ),
    }


def default_responders() -> Dict[str, Responder]:
    return {
        "fire-truck-1": Responder(
            id="fire-truck-1",
            type="FIRE_TRUCK",
            current_location="exit_north",
            destination="building_b",
            priority=1,
            availability="STANDBY",
        ),
        "ambulance-1": Responder(
            id="ambulance-1",
            type="AMBULANCE",
            current_location="exit_east",
            destination="building_c",
            priority=2,
            availability="STANDBY",
        ),
    }


def default_sensors() -> Dict[str, Sensor]:
    sensors: Dict[str, Sensor] = {}
    for node_id, typ in [
        ("building_a", "SMOKE"),
        ("building_b", "SMOKE"),
        ("building_c", "TEMPERATURE"),
        ("building_d", "SMOKE"),
        ("exit_north", "CROWD"),
        ("exit_south", "CROWD"),
        ("exit_east", "CROWD"),
        ("exit_west", "CROWD"),
        ("quad", "CCTV"),
        ("j_south", "INFRASTRUCTURE"),
    ]:
        sensors[f"sensor-{node_id}"] = Sensor(
            id=f"sensor-{node_id}",
            type=typ,
            location=node_id,
            value=0.0,
            status=SensorStatus.OK,
        )
    return sensors


def destinations(nodes: Dict[str, Node]) -> List[str]:
    return [n.id for n in nodes.values() if n.type in {NodeType.EXIT, NodeType.SHELTER, NodeType.ASSEMBLY} and n.safe_zone]
