r"""EmergentWorld scaffold - Part 10: 地图增强（道路 / 移动动画 / 昼夜）。

运行：
    python scaffold_10_map_enhanced.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ map_layout 覆盖

FILES["server/map_layout.py"] = r'''"""村庄地图的固定布局。

坐标系统：归一化 [0, 1]，左上角是 (0, 0)，右下角是 (1, 1)。
客户端负责把归一化坐标映射到像素。
"""

from __future__ import annotations

# 地点坐标 + 显示半径 + 颜色
LOCATION_LAYOUT: dict[str, dict] = {
    "village_square": {"x": 0.50, "y": 0.55, "radius": 0.055, "color": "#c9a86a"},
    "market":         {"x": 0.28, "y": 0.32, "radius": 0.048, "color": "#d8b46a"},
    "tavern":         {"x": 0.72, "y": 0.64, "radius": 0.048, "color": "#b07a4a"},
    "home":           {"x": 0.20, "y": 0.76, "radius": 0.048, "color": "#8a9bb5"},
    "forest":         {"x": 0.82, "y": 0.22, "radius": 0.065, "color": "#4f7f4f"},
    "village_edge":   {"x": 0.10, "y": 0.42, "radius": 0.048, "color": "#7a7a7a"},
    "village_hall":   {"x": 0.55, "y": 0.26, "radius": 0.048, "color": "#a86a8a"},
}

# 地点之间是否有道路
PATHS: list[tuple[str, str]] = [
    ("village_square", "market"),
    ("village_square", "tavern"),
    ("village_square", "village_hall"),
    ("village_square", "home"),
    ("village_square", "forest"),
    ("village_square", "village_edge"),
    ("market", "village_hall"),
    ("village_edge", "forest"),
    ("market", "forest"),
]

DEFAULT_LOCATION = "village_square"


def get_location(location_id: str) -> dict:
    return LOCATION_LAYOUT.get(location_id, LOCATION_LAYOUT[DEFAULT_LOCATION])


def all_locations() -> dict[str, dict]:
    return LOCATION_LAYOUT


def all_paths() -> list[tuple[str, str]]:
    return PATHS
'''

# ================================================================ map_view 覆盖

FILES["server/core/map_view.py"] = r'''"""构造地图视图数据：地点 + 道路 + NPC 位置 + 活跃事件 + 时间。"""

from __future__ import annotations

import math

from sqlmodel import Session, select

from server import i18n
from server.core.world import load_npcs
from server.map_layout import all_locations, all_paths, get_location
from server.models.db import EventRow, loads
from server.models.schemas import World


def _distribute_in_circle(
    base_x: float,
    base_y: float,
    count: int,
    ring_radius: float = 0.035,
) -> list[tuple[float, float]]:
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

    # 2. 道路
    paths: list[dict] = []
    for a, b in all_paths():
        la = get_location(a)
        lb = get_location(b)
        paths.append({
            "from": a,
            "to": b,
            "from_x": la["x"],
            "from_y": la["y"],
            "to_x": lb["x"],
            "to_y": lb["y"],
        })

    # 3. NPC 分组 + 错开
    npcs = load_npcs(session)
    by_loc: dict[str, list] = {}
    for npc in npcs:
        by_loc.setdefault(npc.location_id, []).append(npc)

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

    # 4. 活跃事件
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

    # 5. 昼夜相关时间
    return {
        "tick": world.tick,
        "day": world.day,
        "hour": world.hour,
        "tension": world.director.tension,
        "locations": locations,
        "paths": paths,
        "npcs": npc_positions,
        "active_events": active_events,
    }
'''

# ================================================================ test 覆盖

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
        assert "paths" in data
        assert "npcs" in data
        assert "hour" in data
        assert len(data["npcs"]) == 3
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


def test_map_paths_are_valid():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=1)
        save_world(s, world)
        data = build_map_data(s, world)
        loc_ids = {loc["id"] for loc in data["locations"]}
        for p in data["paths"]:
            assert p["from"] in loc_ids
            assert p["to"] in loc_ids
'''

# ================================================================ map_view.gd 覆盖（核心）

FILES["client/map_view.gd"] = '''class_name MapView
extends Control

# --- 数据 ---
var locations: Array = []
var paths: Array = []
var npcs: Array = []
var active_events: Array = []
var world_hour: int = 12
var world_day: int = 0

# --- 交互 ---
var hovered_npc_id: String = ""
var selected_npc_id: String = ""

signal npc_clicked(npc_id: String)

# --- 常量 ---
const MARGIN := 20.0
const NPC_DOT_RADIUS := 5.0
const NPC_HOVER_RADIUS := 11.0
const BG_DAY := Color("#1f2a1f")
const BG_NIGHT := Color("#0d1220")
const BORDER_COLOR := Color("#3a5a3a")
const GRID_COLOR := Color(1, 1, 1, 0.05)
const PATH_COLOR := Color(0.65, 0.55, 0.35, 0.55)
const PATH_WIDTH := 2.0
const MOVE_DURATION := 0.75  # 秒

# --- 动画 ---
# npc_id -> {from_x, from_y, to_x, to_y, current_x, current_y, t}
var _npc_animations: Dictionary = {}

var font: Font
var font_size := 12


func _ready() -> void:
	font = ThemeDB.fallback_font
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_exited.connect(_on_mouse_exited)
	set_process(true)


func set_data(data: Dictionary) -> void:
	var new_npcs: Array = data.get("npcs", [])
	_sync_npc_animations(new_npcs)

	locations = data.get("locations", [])
	paths = data.get("paths", [])
	npcs = new_npcs
	active_events = data.get("active_events", [])
	world_hour = int(data.get("hour", 12))
	world_day = int(data.get("day", 0))
	queue_redraw()


func set_selected(npc_id: String) -> void:
	selected_npc_id = npc_id
	queue_redraw()


func _sync_npc_animations(new_npcs: Array) -> void:
	var next_anim: Dictionary = {}
	for npc in new_npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		var to_x := float(npc.get("x", 0.5))
		var to_y := float(npc.get("y", 0.5))

		if _npc_animations.has(npc_id):
			var prev: Dictionary = _npc_animations[npc_id]
			var cur_x := float(prev.get("current_x", to_x))
			var cur_y := float(prev.get("current_y", to_y))
			var old_to_x := float(prev.get("to_x", to_x))
			var old_to_y := float(prev.get("to_y", to_y))

			if abs(to_x - old_to_x) > 0.001 or abs(to_y - old_to_y) > 0.001:
				# 目标变化：从当前位置出发
				next_anim[npc_id] = {
					"from_x": cur_x, "from_y": cur_y,
					"to_x": to_x, "to_y": to_y,
					"current_x": cur_x, "current_y": cur_y,
					"t": 0.0,
				}
			else:
				# 目标不变：保留进度
				next_anim[npc_id] = prev
		else:
			# 新 NPC：直接到位
			next_anim[npc_id] = {
				"from_x": to_x, "from_y": to_y,
				"to_x": to_x, "to_y": to_y,
				"current_x": to_x, "current_y": to_y,
				"t": 1.0,
			}

	_npc_animations = next_anim


func _process(delta: float) -> void:
	var needs_redraw := false
	for npc_id in _npc_animations.keys():
		var anim: Dictionary = _npc_animations[npc_id]
		if float(anim["t"]) >= 1.0:
			continue
		var t := min(1.0, float(anim["t"]) + delta / MOVE_DURATION)
		anim["t"] = t
		# smoothstep 缓动
		var e := t * t * (3.0 - 2.0 * t)
		anim["current_x"] = lerp(float(anim["from_x"]), float(anim["to_x"]), e)
		anim["current_y"] = lerp(float(anim["from_y"]), float(anim["to_y"]), e)
		needs_redraw = true
	if needs_redraw:
		queue_redraw()


# ---------- 输入 ----------

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
		var npc_id := str(npc.get("id", ""))
		var p := _npc_screen_pos(npc_id, canvas_rect)
		var d := p.distance_to(mouse_pos)
		if d < closest_dist:
			closest_dist = d
			closest_id = npc_id
	if closest_id != hovered_npc_id:
		hovered_npc_id = closest_id
		queue_redraw()


# ---------- 坐标 ----------

func _canvas_rect() -> Rect2:
	var w := size.x - MARGIN * 2
	var h := size.y - MARGIN * 2
	return Rect2(MARGIN, MARGIN, w, h)


func _norm_to_screen(nx: float, ny: float, rect: Rect2) -> Vector2:
	return Vector2(rect.position.x + nx * rect.size.x, rect.position.y + ny * rect.size.y)


func _npc_screen_pos(npc_id: String, rect: Rect2) -> Vector2:
	if _npc_animations.has(npc_id):
		var anim: Dictionary = _npc_animations[npc_id]
		return _norm_to_screen(
			float(anim["current_x"]),
			float(anim["current_y"]),
			rect,
		)
	for npc in npcs:
		if str(npc.get("id", "")) == npc_id:
			return _norm_to_screen(float(npc.get("x", 0.5)), float(npc.get("y", 0.5)), rect)
	return Vector2.ZERO


# ---------- 昼夜 ----------

func _ambient_overlay() -> Color:
	# 返回叠加在整个地图上的半透明颜色（越夜越深）
	var h := world_hour
	if h >= 6 and h < 8:
		# 黎明：橙红渐淡
		var t := float(h - 6) / 2.0
		return Color(1.0, 0.55, 0.3, 0.35 * (1.0 - t))
	elif h >= 8 and h < 17:
		# 白天
		return Color(0, 0, 0, 0)
	elif h >= 17 and h < 20:
		# 黄昏：橙红渐浓
		var t := float(h - 17) / 3.0
		return Color(1.0, 0.45, 0.2, 0.4 * t)
	else:
		# 夜晚：深蓝
		return Color(0.08, 0.12, 0.32, 0.55)


func _bg_color() -> Color:
	var overlay := _ambient_overlay()
	# 用叠加 alpha 插值昼夜背景
	return BG_DAY.lerp(BG_NIGHT, overlay.a * 1.4)


# ---------- 绘制 ----------

func _draw() -> void:
	var rect := _canvas_rect()

	# 1. 背景
	draw_rect(rect, _bg_color(), true)

	# 2. 网格
	var grid_step := rect.size.x / 10.0
	var x := rect.position.x
	while x <= rect.position.x + rect.size.x:
		draw_line(Vector2(x, rect.position.y),
			Vector2(x, rect.position.y + rect.size.y), GRID_COLOR, 1.0)
		x += grid_step
	var y := rect.position.y
	while y <= rect.position.y + rect.size.y:
		draw_line(Vector2(rect.position.x, y),
			Vector2(rect.position.x + rect.size.x, y), GRID_COLOR, 1.0)
		y += grid_step

	# 3. 道路
	for p in paths:
		if not p is Dictionary:
			continue
		var a := _norm_to_screen(float(p.get("from_x", 0.0)), float(p.get("from_y", 0.0)), rect)
		var b := _norm_to_screen(float(p.get("to_x", 0.0)), float(p.get("to_y", 0.0)), rect)
		# 外层浅色
		draw_line(a, b, Color(PATH_COLOR.r, PATH_COLOR.g, PATH_COLOR.b, 0.15), PATH_WIDTH + 3.0)
		# 内层实色
		draw_line(a, b, PATH_COLOR, PATH_WIDTH)

	# 4. 地点
	for loc in locations:
		if not loc is Dictionary:
			continue
		var lx := float(loc.get("x", 0.5))
		var ly := float(loc.get("y", 0.5))
		var radius := float(loc.get("radius", 0.05))
		var center := _norm_to_screen(lx, ly, rect)
		var px_radius := radius * rect.size.x
		var base_color := _parse_color(str(loc.get("color", "#888888")))

		draw_circle(center, px_radius, Color(base_color.r, base_color.g, base_color.b, 0.22))
		draw_arc(center, px_radius, 0.0, TAU, 48, base_color, 1.6, true)

	# 5. 活跃事件环
	for ev in active_events:
		if not ev is Dictionary:
			continue
		var loc_id := str(ev.get("location_id", ""))
		for loc in locations:
			if str(loc.get("id", "")) == loc_id:
				var center := _norm_to_screen(float(loc.get("x", 0.5)), float(loc.get("y", 0.5)), rect)
				var radius := float(loc.get("radius", 0.05)) * rect.size.x + 6
				draw_arc(center, radius, 0.0, TAU, 64, Color(1.0, 0.8, 0.3, 0.75), 2.2, true)
				break

	# 6. NPC 点
	for npc in npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		var p := _npc_screen_pos(npc_id, rect)

		var fill_color := Color(0.9, 0.9, 0.98, 0.95)
		var outline_color := Color(0.1, 0.1, 0.15, 1.0)

		if npc_id == selected_npc_id:
			fill_color = Color(1.0, 0.9, 0.3, 1.0)
			outline_color = Color(0.5, 0.35, 0.0, 1.0)
			draw_circle(p, NPC_DOT_RADIUS + 3.0, Color(1.0, 0.9, 0.3, 0.25))
		elif npc_id == hovered_npc_id:
			fill_color = Color(0.7, 1.0, 1.0, 1.0)
			outline_color = Color(0.2, 0.5, 0.6, 1.0)

		draw_circle(p, NPC_DOT_RADIUS, fill_color)
		draw_arc(p, NPC_DOT_RADIUS, 0.0, TAU, 24, outline_color, 1.5, true)

	# 7. 环境光叠加（覆盖以上所有元素，但文字会另画）
	draw_rect(rect, _ambient_overlay(), true)

	# 8. 文字层（不受环境光影响）
	for loc in locations:
		if not loc is Dictionary:
			continue
		var center := _norm_to_screen(float(loc.get("x", 0.5)), float(loc.get("y", 0.5)), rect)
		var px_radius := float(loc.get("radius", 0.05)) * rect.size.x
		var label: String = str(loc.get("label", loc.get("id", "")))
		var text_pos := Vector2(center.x - _text_width(label, font_size) / 2.0, center.y - px_radius - 6)
		# 阴影 + 文字
		draw_string(font, text_pos + Vector2(1, 1), label,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0, 0, 0, 0.75))
		draw_string(font, text_pos, label,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.95, 0.95, 0.9))

	for npc in npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		if npc_id != hovered_npc_id and npc_id != selected_npc_id:
			continue
		var p := _npc_screen_pos(npc_id, rect)
		var name: String = str(npc.get("name", "?"))
		var tw := _text_width(name, font_size)
		var bg_rect := Rect2(p.x - tw / 2.0 - 5, p.y - NPC_DOT_RADIUS - 22, tw + 10, 17)
		draw_rect(bg_rect, Color(0, 0, 0, 0.8), true)
		draw_string(font, Vector2(bg_rect.position.x + 5, bg_rect.position.y + 13),
			name, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 1, 1))


# ---------- 工具 ----------

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

# ================================================================ main.gd 微调（自动刷新地图）

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

# 地图轮询
var map_poll_timer: Timer


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	api.fetch_i18n()

	# 定时刷新地图，让 NPC 移动可见
	map_poll_timer = Timer.new()
	map_poll_timer.wait_time = 1.2
	map_poll_timer.autostart = true
	map_poll_timer.timeout.connect(func(): api.fetch_map())
	add_child(map_poll_timer)


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

	var step24_btn := Button.new()
	step24_btn.text = "推进 24 tick"
	step24_btn.pressed.connect(_on_step_24)
	top.add_child(step24_btn)

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

	# 地图
	var map_tab := VBoxContainer.new()
	map_tab.name = "地图"
	tabs.add_child(map_tab)

	map_view = MapView.new()
	map_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_view.npc_clicked.connect(_on_map_npc_clicked)
	map_tab.add_child(map_view)

	# 档案
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

	var ev_scroll := ScrollContainer.new()
	ev_scroll.name = "编年史"
	tabs.add_child(ev_scroll)
	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ev_scroll.add_child(event_log)

	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.name = "奖励"
	tabs.add_child(rwd_scroll)
	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)

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


func _on_step_24() -> void:
	# 连点 24 次推进，用协程间隔
	_step_24_recursive(24)


func _step_24_recursive(remaining: int) -> void:
	if remaining <= 0:
		return
	api.step_world()
	await get_tree().create_timer(0.6).timeout
	_step_24_recursive(remaining - 1)


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

    print("\nPart 10 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()