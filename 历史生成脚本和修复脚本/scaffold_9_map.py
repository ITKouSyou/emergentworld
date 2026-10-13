r"""EmergentWorld scaffold - Part 9: 地图视图。

运行：
    python scaffold_9_map.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ 地图数据

FILES["server/map_layout.py"] = r'''"""村庄地图的固定布局。

坐标系统：归一化 [0, 1]，左上角是 (0, 0)，右下角是 (1, 1)。
客户端的画布负责把这个比例映射到实际像素。
"""

from __future__ import annotations

# 地点坐标 + 显示半径（用于绘制光圈/标记）
LOCATION_LAYOUT: dict[str, dict] = {
    "village_square": {"x": 0.50, "y": 0.52, "radius": 0.06, "color": "#c9a86a"},
    "market":         {"x": 0.34, "y": 0.38, "radius": 0.05, "color": "#d8b46a"},
    "tavern":         {"x": 0.62, "y": 0.58, "radius": 0.05, "color": "#b07a4a"},
    "home":           {"x": 0.24, "y": 0.68, "radius": 0.05, "color": "#8a9bb5"},
    "forest":         {"x": 0.78, "y": 0.28, "radius": 0.07, "color": "#4f7f4f"},
    "village_edge":   {"x": 0.12, "y": 0.48, "radius": 0.05, "color": "#7a7a7a"},
    "village_hall":   {"x": 0.55, "y": 0.34, "radius": 0.05, "color": "#a86a8a"},
}

# 默认位置（若 NPC 的 location_id 不在表中）
DEFAULT_LOCATION = "village_square"


def get_location(location_id: str) -> dict:
    return LOCATION_LAYOUT.get(location_id, LOCATION_LAYOUT[DEFAULT_LOCATION])


def all_locations() -> dict[str, dict]:
    return LOCATION_LAYOUT
'''

# ================================================================ map 生成器

FILES["server/core/map_view.py"] = r'''"""构造地图视图数据：地点 + NPC 位置 + 活跃事件。"""

from __future__ import annotations

import math

from sqlmodel import Session, select

from server import i18n
from server.core.world import load_npcs
from server.map_layout import all_locations, get_location
from server.models.db import EventRow, loads
from server.models.schemas import World


def _distribute_in_circle(
    base_x: float,
    base_y: float,
    count: int,
    ring_radius: float = 0.035,
) -> list[tuple[float, float]]:
    """把 count 个 NPC 均匀分布在以 (base_x, base_y) 为圆心的圆周上。

    如果只有 1 个，放中心。2 个以上分布均匀，避免重叠。
    """
    if count <= 1:
        return [(base_x, base_y)]
    points: list[tuple[float, float]] = []
    for i in range(count):
        angle = -math.pi / 2 + (2 * math.pi * i / count)
        px = base_x + math.cos(angle) * ring_radius
        py = base_y + math.sin(angle) * ring_radius
        points.append((px, py))
    return points


def build_map_data(session: Session, world: World) -> dict:
    # 1. 地点
    locations: list[dict] = []
    for loc_id, layout in all_locations().items():
        locations.append({
            "id": loc_id,
            "label": i18n.location_label(loc_id),
            "x": layout["x"],
            "y": layout["y"],
            "radius": layout["radius"],
            "color": layout["color"],
        })

    # 2. NPC 按地点分组
    npcs = load_npcs(session)
    by_loc: dict[str, list] = {}
    for npc in npcs:
        by_loc.setdefault(npc.location_id, []).append(npc)

    # 3. 每个地点的 NPC 错开
    npc_positions: list[dict] = []
    for loc_id, group in by_loc.items():
        layout = get_location(loc_id)
        pts = _distribute_in_circle(layout["x"], layout["y"], len(group))
        for npc, (px, py) in zip(group, pts):
            npc_positions.append({
                "id": npc.id,
                "name": npc.name,
                "location_id": loc_id,
                "x": round(px, 4),
                "y": round(py, 4),
            })

    # 4. 活跃事件（state == active 的最近事件）
    rows = session.exec(
        select(EventRow)
        .where(EventRow.state == "active")
        .order_by(EventRow.created_at.desc())
        .limit(10)
    ).all()

    active_events: list[dict] = []
    for r in rows:
        payload = loads(r.payload_json) or {}
        active_events.append({
            "id": r.id,
            "template_id": r.template_id,
            "template_label": i18n.template_label(r.template_id),
            "location_id": r.location_id,
            "location_label": i18n.location_label(r.location_id),
            "summary": payload.get("summary", ""),
        })

    return {
        "tick": world.tick,
        "day": world.day,
        "tension": world.director.tension,
        "locations": locations,
        "npcs": npc_positions,
        "active_events": active_events,
    }
'''

# ================================================================ main.py 加 /map

FILES["server/main.py"] = r'''"""FastAPI 入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, select

from server import i18n
from server.api import routes_dialogue, routes_review
from server.config import settings
from server.core import director
from server.core.event_flow import run_event_cycle
from server.core.map_view import build_map_data
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.db.session import engine
from server.models.db import EventRow, ItemRow, RewardRow, dumps, loads
from server.models.schemas import Event, NPC, Reward, World
from server.systems import relationship


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_world(session)
    yield


app = FastAPI(title="EmergentWorld", lifespan=lifespan)
app.include_router(routes_dialogue.router)
app.include_router(routes_review.router)


def get_session() -> Session:
    return Session(engine)


@app.get("/")
def root() -> dict:
    return {
        "name": "EmergentWorld",
        "version": "0.5.0",
        "docs": "/docs",
        "endpoints": [
            "/health", "/i18n", "/map",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/event", "/event/trigger",
            "/reward", "/item", "/item/{item_id}",
            "/review/latest",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/i18n")
def i18n_endpoint() -> dict:
    return i18n.all_labels()


@app.get("/map")
def map_view() -> dict:
    """返回地图视图数据：地点、NPC 位置、活跃事件。"""
    with get_session() as s:
        world = load_world(s)
        return build_map_data(s, world)


# ---------- World ----------

@app.get("/world/state", response_model=World)
def world_state() -> World:
    with get_session() as s:
        return load_world(s)


@app.post("/world/tick", response_model=World)
def world_tick() -> World:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        save_world(s, world)
        return world


@app.post("/world/step")
async def world_step() -> dict:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)
        save_world(s, world)
        return {
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
            "tension": world.director.tension,
            "event": event.id if event else None,
            "event_summary": event.payload.get("summary") if event else None,
            "event_template": event.template_id if event else None,
            "template_label": i18n.template_label(event.template_id) if event else None,
        }


# ---------- NPC ----------

def _npc_to_display(npc: NPC) -> dict:
    return {
        "id": npc.id,
        "name": npc.name,
        "age": npc.age,
        "location_id": npc.location_id,
        "location_label": i18n.location_label(npc.location_id),
        "goals": npc.goals,
        "traits": [
            {"key": k, "label": i18n.trait_label(k), "value": float(v)}
            for k, v in npc.traits.items()
        ],
        "needs": [
            {"key": k, "label": i18n.need_label(k), "value": float(v)}
            for k, v in npc.needs.items()
        ],
    }


@app.get("/npc")
def list_npcs() -> list[dict]:
    with get_session() as s:
        return [_npc_to_display(n) for n in load_npcs(s)]


@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id])


@app.get("/npc/{npc_id}/relationships")
def npc_relationships(npc_id: str) -> list[dict]:
    with get_session() as s:
        npcs = {n.id: n.name for n in load_npcs(s)}
        result = []
        for r in relationship.list_relationships(s, npc_id):
            other_id = r.to_npc if r.from_npc == npc_id else r.from_npc
            result.append({
                "from_npc": r.from_npc,
                "to_npc": r.to_npc,
                "other_id": other_id,
                "other_name": npcs.get(other_id, other_id),
                "trust": r.trust,
                "affection": r.affection,
                "fear": r.fear,
                "debt": r.debt,
            })
        return result


# ---------- Event ----------

def _row_to_event(r: EventRow) -> dict:
    payload = loads(r.payload_json) or {}
    return {
        "id": r.id,
        "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": loads(r.participants_json) or [],
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state,
        "state_label": i18n.state_label(r.state),
        "payload": payload,
        "summary": payload.get("summary", ""),
        "narrative": payload.get("narrative", ""),
        "item_id": payload.get("item_id"),
        "created_at": r.created_at,
        "resolved_at": r.resolved_at,
    }


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()
        return [_row_to_event(r) for r in rows]


@app.post("/event/trigger")
async def trigger_event() -> dict:
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered (check templates / npcs)")
        return _row_to_event(
            EventRow(
                id=event.id,
                template_id=event.template_id,
                participants_json=dumps(event.participants),
                location_id=event.location_id,
                state=event.state,
                payload_json=dumps(event.payload),
                created_at=event.created_at,
                resolved_at=event.resolved_at,
            )
        )


# ---------- Reward ----------

@app.get("/reward")
def list_rewards(limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(RewardRow).order_by(RewardRow.id.desc()).limit(limit)
        ).all()
        result = []
        for r in rows:
            payload = loads(r.payload_json) or {}
            result.append({
                "id": r.id,
                "event_id": r.event_id,
                "kind": r.kind,
                "kind_label": i18n.reward_kind_label(r.kind),
                "value": r.value,
                "description": r.description,
                "payload": payload,
            })
        return result


# ---------- Item ----------

def _row_to_item(r: ItemRow) -> dict:
    return {
        "id": r.id,
        "reward_id": r.reward_id,
        "event_id": r.event_id,
        "name": r.name,
        "kind": r.kind,
        "affixes": loads(r.affixes_json) or [],
        "story": r.story,
        "value": r.value,
    }


@app.get("/item")
def list_items(limit: int = 50) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(ItemRow).order_by(ItemRow.id.desc()).limit(limit)
        ).all()
        return [_row_to_item(r) for r in rows]


@app.get("/item/{item_id}")
def get_item(item_id: str) -> dict:
    with get_session() as s:
        row = s.get(ItemRow, item_id)
        if row is None:
            raise HTTPException(404, "item not found")
        return _row_to_item(row)
'''

# ================================================================ 客户端：MapView

FILES["client/map_view.gd"] = '''class_name MapView
extends Control

# 地图数据
var locations: Array = []
var npcs: Array = []
var active_events: Array = []

# 交互
var hovered_npc_id: String = ""
var selected_npc_id: String = ""

signal npc_clicked(npc_id: String)

const MARGIN := 20.0
const NPC_DOT_RADIUS := 5.0
const NPC_HOVER_RADIUS := 9.0
const BG_COLOR := Color("#1f2a1f")
const BORDER_COLOR := Color("#3a5a3a")
const GRID_COLOR := Color(1, 1, 1, 0.05)

var font: Font
var font_size := 12


func _ready() -> void:
	font = ThemeDB.fallback_font
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_exited.connect(_on_mouse_exited)


func set_data(data: Dictionary) -> void:
	locations = data.get("locations", [])
	npcs = data.get("npcs", [])
	active_events = data.get("active_events", [])
	queue_redraw()


func set_selected(npc_id: String) -> void:
	selected_npc_id = npc_id
	queue_redraw()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_update_hover(event.position)
	elif event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_update_hover(event.position)
			if hovered_npc_id != "":
				npc_clicked.emit(hovered_npc_id)


func _on_mouse_exited() -> void:
	hovered_npc_id = ""
	queue_redraw()


func _update_hover(mouse_pos: Vector2) -> void:
	var canvas_rect := _canvas_rect()
	var closest_id := ""
	var closest_dist := NPC_HOVER_RADIUS
	for npc in npcs:
		if not npc is Dictionary:
			continue
		var p := _npc_screen_pos(npc, canvas_rect)
		var d := p.distance_to(mouse_pos)
		if d < closest_dist:
			closest_dist = d
			closest_id = str(npc.get("id", ""))
	if closest_id != hovered_npc_id:
		hovered_npc_id = closest_id
		queue_redraw()


func _canvas_rect() -> Rect2:
	var w := size.x - MARGIN * 2
	var h := size.y - MARGIN * 2
	return Rect2(MARGIN, MARGIN, w, h)


func _norm_to_screen(nx: float, ny: float, rect: Rect2) -> Vector2:
	return Vector2(rect.position.x + nx * rect.size.x, rect.position.y + ny * rect.size.y)


func _npc_screen_pos(npc: Dictionary, rect: Rect2) -> Vector2:
	return _norm_to_screen(float(npc.get("x", 0.5)), float(npc.get("y", 0.5)), rect)


func _draw() -> void:
	var rect := _canvas_rect()

	# 背景
	draw_rect(rect, BG_COLOR, true)

	# 网格
	var grid_step := rect.size.x / 10.0
	var x := rect.position.x
	while x <= rect.position.x + rect.size.x:
		draw_line(Vector2(x, rect.position.y), Vector2(x, rect.position.y + rect.size.y), GRID_COLOR, 1.0)
		x += grid_step
	var y := rect.position.y
	while y <= rect.position.y + rect.size.y:
		draw_line(Vector2(rect.position.x, y), Vector2(rect.position.x + rect.size.x, y), GRID_COLOR, 1.0)
		y += grid_step

	# 边框
	draw_rect(rect, BORDER_COLOR, false, 1.0)

	# 地点
	for loc in locations:
		if not loc is Dictionary:
			continue
		var lx := float(loc.get("x", 0.5))
		var ly := float(loc.get("y", 0.5))
		var radius := float(loc.get("radius", 0.05))
		var center := _norm_to_screen(lx, ly, rect)
		var px_radius := radius * rect.size.x
		var base_color := _parse_color(str(loc.get("color", "#888888")))

		# 光圈
		draw_circle(center, px_radius, Color(base_color.r, base_color.g, base_color.b, 0.18))
		# 边线
		draw_arc(center, px_radius, 0.0, TAU, 48, base_color, 1.5, true)

		# 标签
		var label: String = str(loc.get("label", loc.get("id", "")))
		var text_pos := Vector2(center.x - _text_width(label, font_size) / 2.0, center.y - px_radius - 6)
		draw_string(font, text_pos, label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.92, 0.92, 0.88))

	# 活跃事件：在地点周围画脉冲环
	for ev in active_events:
		if not ev is Dictionary:
			continue
		var loc_id := str(ev.get("location_id", ""))
		for loc in locations:
			if str(loc.get("id", "")) == loc_id:
				var center := _norm_to_screen(float(loc.get("x", 0.5)), float(loc.get("y", 0.5)), rect)
				var radius := float(loc.get("radius", 0.05)) * rect.size.x + 6
				draw_arc(center, radius, 0.0, TAU, 64, Color(1.0, 0.8, 0.3, 0.7), 2.0, true)
				break

	# NPC
	for npc in npcs:
		if not npc is Dictionary:
			continue
		var p := _npc_screen_pos(npc, rect)
		var npc_id := str(npc.get("id", ""))

		# 主体圆点
		var fill_color := Color(0.85, 0.85, 0.95, 0.9)
		var outline_color := Color(0.15, 0.15, 0.2, 1.0)

		if npc_id == selected_npc_id:
			fill_color = Color(1.0, 0.9, 0.3, 1.0)
			outline_color = Color(0.5, 0.35, 0.0, 1.0)
			draw_circle(p, NPC_DOT_RADIUS + 3.0, Color(1.0, 0.9, 0.3, 0.25))
		elif npc_id == hovered_npc_id:
			fill_color = Color(0.7, 1.0, 1.0, 1.0)
			outline_color = Color(0.2, 0.5, 0.6, 1.0)

		draw_circle(p, NPC_DOT_RADIUS, fill_color)
		draw_arc(p, NPC_DOT_RADIUS, 0.0, TAU, 24, outline_color, 1.5, true)

		# 名字（悬停或选中时显示）
		if npc_id == hovered_npc_id or npc_id == selected_npc_id:
			var name: String = str(npc.get("name", "?"))
			var tw := _text_width(name, font_size)
			var bg_rect := Rect2(
				p.x - tw / 2.0 - 4, p.y - NPC_DOT_RADIUS - 20,
				tw + 8, 16
			)
			draw_rect(bg_rect, Color(0, 0, 0, 0.75), true)
			draw_string(font, Vector2(bg_rect.position.x + 4, bg_rect.position.y + 12),
				name, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 1, 1))


func _parse_color(hex_str: String) -> Color:
	var s := hex_str.strip_edges()
	if s.begins_with("#"):
		s = s.substr(1)
	if s.length() == 6:
		var r := ("0x" + s.substr(0, 2)).hex_to_int()
		var g := ("0x" + s.substr(2, 2)).hex_to_int()
		var b := ("0x" + s.substr(4, 2)).hex_to_int()
		return Color(r / 255.0, g / 255.0, b / 255.0, 1.0)
	return Color(0.5, 0.5, 0.5, 1.0)


func _text_width(text: String, size_px: int) -> float:
	return font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x
'''

# ================================================================ 客户端 api.gd 加 map

FILES["client/api.gd"] = '''class_name GameApi
extends Node

const BASE_URL := "http://127.0.0.1:8000"

signal i18n_received(data: Dictionary)
signal world_state_received(data: Dictionary)
signal npc_list_received(data: Array)
signal npc_detail_received(data: Dictionary)
signal dialogue_received(data: Dictionary)
signal event_triggered(data: Dictionary)
signal event_list_received(data: Array)
signal relationships_received(data: Array)
signal reward_list_received(data: Array)
signal item_list_received(data: Array)
signal map_received(data: Dictionary)
signal request_failed(endpoint: String, error: String)


func fetch_i18n() -> void:
	_request("GET", "/i18n", {}, "i18n_received")


func fetch_world_state() -> void:
	_request("GET", "/world/state", {}, "world_state_received")


func step_world() -> void:
	_request("POST", "/world/step", {}, "event_triggered")


func trigger_event() -> void:
	_request("POST", "/event/trigger", {}, "event_triggered")


func fetch_npcs() -> void:
	_request("GET", "/npc", {}, "npc_list_received")


func fetch_npc_detail(npc_id: String) -> void:
	_request("GET", "/npc/%s" % npc_id, {}, "npc_detail_received")


func fetch_relationships(npc_id: String) -> void:
	_request("GET", "/npc/%s/relationships" % npc_id, {}, "relationships_received")


func send_dialogue(npc_id: String, player_input: String) -> void:
	_request("POST", "/npc/%s/dialogue" % npc_id, {"player_input": player_input}, "dialogue_received")


func fetch_events(limit: int = 20) -> void:
	_request("GET", "/event?limit=%d" % limit, {}, "event_list_received")


func fetch_rewards(limit: int = 20) -> void:
	_request("GET", "/reward?limit=%d" % limit, {}, "reward_list_received")


func fetch_items(limit: int = 50) -> void:
	_request("GET", "/item?limit=%d" % limit, {}, "item_list_received")


func fetch_map() -> void:
	_request("GET", "/map", {}, "map_received")


func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)
	http.request_completed.connect(_on_response.bind(http, signal_name))

	var url := BASE_URL + path
	var headers := PackedStringArray([
		"Content-Type: application/json",
		"Accept: application/json",
	])

	var err: int
	if method == "GET":
		err = http.request(url, headers, HTTPClient.METHOD_GET)
	else:
		var body_str := JSON.stringify(body)
		err = http.request(url, headers, HTTPClient.METHOD_POST, body_str)

	if err != OK:
		http.queue_free()
		request_failed.emit(signal_name, "request failed: %d" % err)


func _on_response(
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray,
	http: HTTPRequest,
	signal_name: String
) -> void:
	http.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(signal_name, "transport error: %d" % result)
		return

	var text := body.get_string_from_utf8()
	var data = JSON.parse_string(text)

	if response_code < 200 or response_code >= 300:
		var msg := "HTTP %d" % response_code
		if data is Dictionary and data.has("detail"):
			msg += ": " + str(data["detail"])
		request_failed.emit(signal_name, msg)
		return

	if data == null:
		request_failed.emit(signal_name, "JSON parse failed")
		return

	emit_signal(signal_name, data)
'''

# ================================================================ 客户端 main.gd

FILES["client/main.gd"] = r'''extends Control

var api: GameApi

var i18n_traits: Dictionary = {}
var i18n_needs: Dictionary = {}
var i18n_templates: Dictionary = {}
var i18n_locations: Dictionary = {}
var i18n_reward_kinds: Dictionary = {}
var i18n_states: Dictionary = {}

var status_label: Label
var npc_list: ItemList
var npc_detail: RichTextLabel
var relationship_label: RichTextLabel
var dialogue_log: RichTextLabel
var dialogue_input: LineEdit
var event_log: RichTextLabel
var reward_log: RichTextLabel
var item_log: RichTextLabel
var map_view: MapView

var current_npc_id: String = ""
var npc_data: Dictionary = {}
var npc_order: Array[String] = []


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	api.fetch_i18n()


func _connect_signals() -> void:
	api.i18n_received.connect(_on_i18n_received)
	api.world_state_received.connect(_on_world_state)
	api.npc_list_received.connect(_on_npc_list)
	api.npc_detail_received.connect(_on_npc_detail)
	api.dialogue_received.connect(_on_dialogue)
	api.event_triggered.connect(_on_event_triggered)
	api.event_list_received.connect(_on_event_list)
	api.relationships_received.connect(_on_relationships)
	api.reward_list_received.connect(_on_reward_list)
	api.item_list_received.connect(_on_item_list)
	api.map_received.connect(_on_map_received)
	api.request_failed.connect(_on_request_failed)


func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)

	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	add_child(margin)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8)
	margin.add_child(root)

	_build_top_bar(root)

	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_theme_constant_override("separation", 8)
	root.add_child(split)

	_build_left_panel(split)
	_build_middle_panel(split)
	_build_right_panel(split)


func _build_top_bar(root: VBoxContainer) -> void:
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 12)
	root.add_child(top)

	status_label = Label.new()
	status_label.text = "加载中..."
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(status_label)

	var step_btn := Button.new()
	step_btn.text = "推进一 tick"
	step_btn.pressed.connect(func(): api.step_world())
	top.add_child(step_btn)

	var event_btn := Button.new()
	event_btn.text = "触发事件"
	event_btn.pressed.connect(func(): api.trigger_event())
	top.add_child(event_btn)

	var refresh_btn := Button.new()
	refresh_btn.text = "刷新"
	refresh_btn.pressed.connect(_refresh_all)
	top.add_child(refresh_btn)


func _build_left_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(260, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var title := Label.new()
	title.text = "居民"
	panel.add_child(title)

	npc_list = ItemList.new()
	npc_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	npc_list.item_selected.connect(_on_npc_selected)
	panel.add_child(npc_list)


func _build_middle_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(520, 0)
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(panel)

	var tabs := TabContainer.new()
	tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.tab_alignment = TabBar.ALIGNMENT_LEFT
	panel.add_child(tabs)

	# --- Tab 1: 地图 ---
	var map_tab := VBoxContainer.new()
	map_tab.name = "地图"
	tabs.add_child(map_tab)

	map_view = MapView.new()
	map_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_view.npc_clicked.connect(_on_map_npc_clicked)
	map_tab.add_child(map_view)

	# --- Tab 2: 档案 ---
	var profile_tab := VBoxContainer.new()
	profile_tab.name = "档案"
	profile_tab.add_theme_constant_override("separation", 6)
	tabs.add_child(profile_tab)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 200)
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	profile_tab.add_child(detail_scroll)

	npc_detail = RichTextLabel.new()
	npc_detail.bbcode_enabled = true
	npc_detail.fit_content = true
	npc_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	npc_detail.text = "从左侧选择一位居民"
	detail_scroll.add_child(npc_detail)

	relationship_label = RichTextLabel.new()
	relationship_label.bbcode_enabled = true
	relationship_label.fit_content = true
	relationship_label.custom_minimum_size = Vector2(0, 70)
	profile_tab.add_child(relationship_label)

	var dlg_title := Label.new()
	dlg_title.text = "对话"
	profile_tab.add_child(dlg_title)

	var dlg_scroll := ScrollContainer.new()
	dlg_scroll.custom_minimum_size = Vector2(0, 120)
	dlg_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	profile_tab.add_child(dlg_scroll)

	dialogue_log = RichTextLabel.new()
	dialogue_log.bbcode_enabled = true
	dialogue_log.fit_content = true
	dialogue_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dlg_scroll.add_child(dialogue_log)

	var dlg_input_row := HBoxContainer.new()
	dlg_input_row.add_theme_constant_override("separation", 6)
	profile_tab.add_child(dlg_input_row)

	dialogue_input = LineEdit.new()
	dialogue_input.placeholder_text = "说点什么..."
	dialogue_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dialogue_input.text_submitted.connect(_on_dialogue_submit)
	dlg_input_row.add_child(dialogue_input)

	var send_btn := Button.new()
	send_btn.text = "发送"
	send_btn.pressed.connect(func(): _on_dialogue_submit(dialogue_input.text))
	dlg_input_row.add_child(send_btn)


func _build_right_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(380, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var tabs := TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tabs.tab_alignment = TabBar.ALIGNMENT_LEFT
	panel.add_child(tabs)

	# 编年史
	var ev_scroll := ScrollContainer.new()
	ev_scroll.name = "编年史"
	tabs.add_child(ev_scroll)
	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ev_scroll.add_child(event_log)

	# 奖励
	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.name = "奖励"
	tabs.add_child(rwd_scroll)
	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)

	# 物品
	var item_scroll := ScrollContainer.new()
	item_scroll.name = "物品"
	tabs.add_child(item_scroll)
	item_log = RichTextLabel.new()
	item_log.bbcode_enabled = true
	item_log.fit_content = true
	item_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	item_scroll.add_child(item_log)


func _refresh_all() -> void:
	api.fetch_world_state()
	api.fetch_npcs()
	api.fetch_events(20)
	api.fetch_rewards(20)
	api.fetch_items(50)
	api.fetch_map()


func _on_i18n_received(data: Dictionary) -> void:
	i18n_traits = data.get("traits", {})
	i18n_needs = data.get("needs", {})
	i18n_templates = data.get("templates", {})
	i18n_locations = data.get("locations", {})
	i18n_reward_kinds = data.get("reward_kinds", {})
	i18n_states = data.get("states", {})
	_refresh_all()


func _on_world_state(data: Dictionary) -> void:
	var director = data.get("director", {})
	var tension: float = 0.0
	if director is Dictionary:
		tension = float(director.get("tension", 0.0))
	status_label.text = "第 %d 天  %02d:00   Tick %d   张力 %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		int(data.get("tick", 0)),
		tension,
	]


func _on_map_received(data: Dictionary) -> void:
	if map_view:
		map_view.set_data(data)
		map_view.set_selected(current_npc_id)


func _on_map_npc_clicked(npc_id: String) -> void:
	# 地图点 NPC → 左侧列表同步选中
	for i in range(npc_order.size()):
		if npc_order[i] == npc_id:
			npc_list.select(i)
			_on_npc_selected(i)
			break


func _on_npc_list(data: Array) -> void:
	npc_data.clear()
	npc_order.clear()
	npc_list.clear()
	for npc in data:
		if not npc is Dictionary:
			continue
		var id: String = str(npc.get("id", ""))
		var name: String = str(npc.get("name", "?"))
		var loc: String = str(npc.get("location_label", ""))
		npc_data[id] = npc
		npc_order.append(id)
		npc_list.add_item("%s   @ %s" % [name, loc])


func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	if map_view:
		map_view.set_selected(current_npc_id)
	var name: String = str(npc_data[current_npc_id].get("name", "?"))
	dialogue_log.text = "[i]你走近 %s...[/i]" % name


func _on_npc_detail(data: Dictionary) -> void:
	var lines: Array[String] = []
	lines.append("[b][color=yellow]%s[/color][/b]   %d 岁" % [
		str(data.get("name", "?")),
		int(data.get("age", 0)),
	])
	lines.append("所在地：%s" % str(data.get("location_label", "")))
	lines.append("")

	lines.append("[b]性格[/b]")
	var traits: Array = data.get("traits", [])
	for t in traits:
		if t is Dictionary:
			lines.append("   %s：%.2f" % [
				str(t.get("label", t.get("key", "?"))),
				float(t.get("value", 0)),
			])

	lines.append("")
	lines.append("[b]需求[/b]")
	var needs: Array = data.get("needs", [])
	for n in needs:
		if n is Dictionary:
			lines.append("   %s：%.2f" % [
				str(n.get("label", n.get("key", "?"))),
				float(n.get("value", 0)),
			])

	lines.append("")
	lines.append("[b]目标[/b]")
	var goals: Array = data.get("goals", [])
	for g in goals:
		lines.append("   · %s" % str(g))

	npc_detail.text = "\n".join(lines)


func _on_relationships(data: Array) -> void:
	if data.is_empty():
		relationship_label.text = "[i]（暂无关系记录）[/i]"
		return
	var lines: Array[String] = ["[b]关系[/b]"]
	for r in data:
		if not r is Dictionary:
			continue
		var other_name: String = str(r.get("other_name", r.get("other_id", "?")))
		lines.append("   %s   信任 %+.2f   好感 %+.2f   恐惧 %+.2f   债务 %+.2f" % [
			other_name,
			float(r.get("trust", 0)),
			float(r.get("affection", 0)),
			float(r.get("fear", 0)),
			float(r.get("debt", 0)),
		])
	relationship_label.text = "\n".join(lines)


func _on_dialogue_submit(text: String) -> void:
	text = text.strip_edges()
	if text == "" or current_npc_id == "":
		return
	dialogue_log.append_text("\n[b]你：[/b]%s" % text)
	dialogue_input.text = ""
	api.send_dialogue(current_npc_id, text)


func _on_dialogue(data: Dictionary) -> void:
	var name: String = str(data.get("npc_name", "NPC"))
	var reply: String = str(data.get("reply", ""))
	dialogue_log.append_text("\n[b][color=cyan]%s：[/color][/b]%s\n" % [name, reply])


func _on_event_triggered(data: Dictionary) -> void:
	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		var tpl_label: String = str(data.get("template_label", ""))
		if summary != "":
			event_log.append_text("\n[color=orange]→[/color] [b]%s[/b] %s" % [tpl_label, summary])
	_refresh_all()


func _on_event_list(data: Array) -> void:
	event_log.clear()
	for e in data:
		if not e is Dictionary:
			continue
		var state: String = str(e.get("state", ""))
		var state_zh: String = str(e.get("state_label", state))
		var color := "white"
		if state == "resolved":
			color = "lightgreen"
		elif state == "rejected":
			color = "gray"
		elif state == "active":
			color = "yellow"

		var tpl_label: String = str(e.get("template_label", e.get("template_id", "?")))
		var summary: String = str(e.get("summary", ""))
		var loc_label: String = str(e.get("location_label", ""))

		event_log.append_text("[color=%s]·[/color] [b]%s[/b]（%s，%s）\n    %s\n\n" % [
			color, tpl_label, loc_label, state_zh, summary,
		])


func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	for r in data:
		if not r is Dictionary:
			continue
		var kind_label: String = str(r.get("kind_label", r.get("kind", "?")))
		reward_log.append_text("[b]%s[/b]  %.2f  %s\n" % [
			kind_label,
			float(r.get("value", 0)),
			str(r.get("description", "")),
		])


func _on_item_list(data: Array) -> void:
	item_log.clear()
	if data.is_empty():
		item_log.text = "[i]还没有获得任何物品[/i]"
		return
	for it in data:
		if not it is Dictionary:
			continue
		var name: String = str(it.get("name", "?"))
		var kind: String = str(it.get("kind", ""))
		var affixes: Array = it.get("affixes", [])
		var story: String = str(it.get("story", ""))
		var value: float = float(it.get("value", 0))

		var title := "[b][color=gold]%s[/color][/b]" % name
		if kind != "":
			title += "  [i](%s)[/i]" % kind
		item_log.append_text(title + "\n")

		if not affixes.is_empty():
			var affix_strs: Array[String] = []
			for a in affixes:
				affix_strs.append(str(a))
			item_log.append_text("    词缀：%s\n" % ", ".join(affix_strs))

		if story != "":
			item_log.append_text("    [color=lightgray]%s[/color]\n" % story)

		item_log.append_text("    价值：%.2f\n\n" % value)


func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error
'''

# ================================================================ test

FILES["tests/test_map_view.py"] = r'''from sqlmodel import Session, SQLModel, create_engine

from server.core.map_view import build_map_data
from server.core.world import create_world, save_event, save_npc, save_world
from server.models.schemas import Event, NPC


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_map_data_structure():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=1)
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20,
                            goals=["g"], location_id="village_square"))
        data = build_map_data(s, world)
        assert "locations" in data
        assert "npcs" in data
        assert len(data["npcs"]) == 3
        # 三个 NPC 应该分布在不同位置
        coords = {(n["x"], n["y"]) for n in data["npcs"]}
        assert len(coords) == 3


def test_map_data_includes_active_events():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=1)
        save_world(s, world)
        evt = Event(
            id="evt_x",
            template_id="bandit_raid",
            participants=[],
            location_id="village_edge",
            state="active",
            payload={"summary": "test"},
        )
        save_event(s, evt)
        data = build_map_data(s, world)
        assert len(data["active_events"]) == 1
        assert data["active_events"][0]["location_id"] == "village_edge"
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    written = 0
    skipped = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print("[skip]  " + rel)
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print("[write] " + rel)
        written += 1

    print("\nPart 9 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()