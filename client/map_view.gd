class_name MapView
extends Control

var locations: Array = []
var paths: Array = []
var npcs: Array = []
var active_events: Array = []
var world_hour: int = 12
var world_day: int = 0
var season: String = "spring"
var weather: String = "clear"

var hovered_npc_id: String = ""
var selected_npc_id: String = ""

signal npc_clicked(npc_id: String)
signal location_clicked(location_id: String)

const MARGIN := 20.0
const NPC_DOT_RADIUS := 5.0
const NPC_HOVER_RADIUS := 16.0
const BG_SPRING := Color("#2a3a2a")
const BG_SUMMER := Color("#243321")
const BG_AUTUMN := Color("#33291f")
const BG_WINTER := Color("#232b35")
const BG_NIGHT := Color("#0d1220")
const BORDER_COLOR := Color("#3a5a3a")
const GRID_COLOR := Color(1, 1, 1, 0.05)
const PATH_COLOR := Color(0.65, 0.55, 0.35, 0.55)
const PATH_WIDTH := 2.0
const MOVE_DURATION := 0.75

var avatar_cache: Dictionary = {}
var _npc_animations: Dictionary = {}
var font: Font
var font_size := 12
var _weather_t: float = 0.0

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
	season = str(data.get("season", "spring"))
	weather = str(data.get("weather", "clear"))
	queue_redraw()

func set_avatar_cache(cache: Dictionary) -> void:
	avatar_cache = cache
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
				next_anim[npc_id] = {
					"from_x": cur_x, "from_y": cur_y,
					"to_x": to_x, "to_y": to_y,
					"current_x": cur_x, "current_y": cur_y, "t": 0.0,
				}
			else:
				next_anim[npc_id] = prev
		else:
			next_anim[npc_id] = {
				"from_x": to_x, "from_y": to_y,
				"to_x": to_x, "to_y": to_y,
				"current_x": to_x, "current_y": to_y, "t": 1.0,
			}
	_npc_animations = next_anim

func _process(delta: float) -> void:
	_weather_t += delta
	var needs_redraw := false
	for npc_id in _npc_animations.keys():
		var anim: Dictionary = _npc_animations[npc_id]
		if float(anim["t"]) >= 1.0:
			continue
		var t: float = min(1.0, float(anim["t"]) + delta / MOVE_DURATION)
		anim["t"] = t
		var e: float = t * t * (3.0 - 2.0 * t)
		anim["current_x"] = lerp(float(anim["from_x"]), float(anim["to_x"]), e)
		anim["current_y"] = lerp(float(anim["from_y"]), float(anim["to_y"]), e)
		needs_redraw = true
	if weather != "clear" and weather != "fog":
		needs_redraw = true
	if needs_redraw:
		queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_update_hover(event.position)
	elif event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_update_hover(event.position)
			if hovered_npc_id != "":
				npc_clicked.emit(hovered_npc_id)
				return
			var loc_id := _location_at(event.position)
			if loc_id != "":
				location_clicked.emit(loc_id)

func _location_at(mouse_pos: Vector2) -> String:
	var rect := _canvas_rect()
	for loc in locations:
		if not loc is Dictionary:
			continue
		if bool(loc.get("unknown", false)):
			continue
		var center := _norm_to_screen(
			float(loc.get("x", 0.5)),
			float(loc.get("y", 0.5)),
			rect,
		)
		var radius := float(loc.get("radius", 0.05)) * rect.size.x
		if mouse_pos.distance_to(center) <= radius:
			return str(loc.get("id", ""))
	return ""

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

func _canvas_rect() -> Rect2:
	var w := size.x - MARGIN * 2
	var h := size.y - MARGIN * 2
	return Rect2(MARGIN, MARGIN, w, h)

func _norm_to_screen(nx: float, ny: float, rect: Rect2) -> Vector2:
	return Vector2(rect.position.x + nx * rect.size.x, rect.position.y + ny * rect.size.y)

func _npc_screen_pos(npc_id: String, rect: Rect2) -> Vector2:
	if _npc_animations.has(npc_id):
		var anim: Dictionary = _npc_animations[npc_id]
		return _norm_to_screen(float(anim["current_x"]), float(anim["current_y"]), rect)
	for npc in npcs:
		if str(npc.get("id", "")) == npc_id:
			return _norm_to_screen(float(npc.get("x", 0.5)), float(npc.get("y", 0.5)), rect)
	return Vector2.ZERO

func _ambient_overlay() -> Color:
	var h := world_hour
	if h >= 6 and h < 8:
		var t := float(h - 6) / 2.0
		return Color(1.0, 0.55, 0.3, 0.35 * (1.0 - t))
	elif h >= 8 and h < 17:
		return Color(0, 0, 0, 0)
	elif h >= 17 and h < 20:
		var t := float(h - 17) / 3.0
		return Color(1.0, 0.45, 0.2, 0.4 * t)
	else:
		return Color(0.08, 0.12, 0.32, 0.55)

func _bg_color() -> Color:
	var base := BG_SPRING
	if season == "summer":
		base = BG_SUMMER
	elif season == "autumn":
		base = BG_AUTUMN
	elif season == "winter":
		base = BG_WINTER
	var overlay := _ambient_overlay()
	return base.lerp(BG_NIGHT, overlay.a * 1.4)

func _draw() -> void:
	var rect := _canvas_rect()
	draw_rect(rect, _bg_color(), true)

	var grid_step := rect.size.x / 10.0
	var x := rect.position.x
	while x <= rect.position.x + rect.size.x:
		draw_line(Vector2(x, rect.position.y), Vector2(x, rect.position.y + rect.size.y), GRID_COLOR, 1.0)
		x += grid_step
	var y := rect.position.y
	while y <= rect.position.y + rect.size.y:
		draw_line(Vector2(rect.position.x, y), Vector2(rect.position.x + rect.size.x, y), GRID_COLOR, 1.0)
		y += grid_step

	for p in paths:
		if not p is Dictionary:
			continue
		var a := _norm_to_screen(float(p.get("from_x", 0.0)), float(p.get("from_y", 0.0)), rect)
		var b := _norm_to_screen(float(p.get("to_x", 0.0)), float(p.get("to_y", 0.0)), rect)
		draw_line(a, b, Color(PATH_COLOR.r, PATH_COLOR.g, PATH_COLOR.b, 0.15), PATH_WIDTH + 3.0)
		draw_line(a, b, PATH_COLOR, PATH_WIDTH)

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

	# --- NPC 绘制（带头像） ---
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
			draw_circle(p, NPC_DOT_RADIUS + 4.0, Color(1.0, 0.9, 0.3, 0.25))
		elif npc_id == hovered_npc_id:
			fill_color = Color(0.7, 1.0, 1.0, 1.0)
			outline_color = Color(0.2, 0.5, 0.6, 1.0)

		var avatar_url: String = str(npc.get("avatar_url", ""))
		var tex: Texture2D = null
		if avatar_url != "" and avatar_cache.has(avatar_url):
			tex = avatar_cache[avatar_url]

		if tex != null:
			var tex_size := 20.0
			var r := Rect2(p - Vector2(tex_size/2, tex_size/2), Vector2(tex_size, tex_size))
			# 绘制黑色描边底框
			var bg_rect := Rect2(r.position - Vector2(2, 2), r.size + Vector2(4, 4))
			draw_rect(bg_rect, Color(0.1, 0.1, 0.15, 1.0), true)
			# 如果选中，画个发光外圈
			if npc_id == selected_npc_id:
				draw_rect(Rect2(bg_rect.position - Vector2(1, 1), bg_rect.size + Vector2(2, 2)), Color(1.0, 0.9, 0.3, 0.8), false, 1.5)
			elif npc_id == hovered_npc_id:
				draw_rect(Rect2(bg_rect.position - Vector2(1, 1), bg_rect.size + Vector2(2, 2)), Color(0.7, 1.0, 1.0, 0.8), false, 1.5)
			draw_texture_rect(tex, r, false)
		else:
			draw_circle(p, NPC_DOT_RADIUS, fill_color)
			draw_arc(p, NPC_DOT_RADIUS, 0.0, TAU, 24, outline_color, 1.5, true)

	# 环境光叠加
	draw_rect(rect, _ambient_overlay(), true)
	_draw_weather(rect)

	# 文字层
	for loc in locations:
		if not loc is Dictionary:
			continue
		var center := _norm_to_screen(float(loc.get("x", 0.5)), float(loc.get("y", 0.5)), rect)
		var px_radius := float(loc.get("radius", 0.05)) * rect.size.x
		var label: String = str(loc.get("label", loc.get("id", "")))
		var text_pos := Vector2(center.x - _text_width(label, font_size) / 2.0, center.y - px_radius - 6)
		draw_string(font, text_pos + Vector2(1, 1), label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0, 0, 0, 0.75))
		draw_string(font, text_pos, label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.95, 0.95, 0.9))

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
		draw_string(font, Vector2(bg_rect.position.x + 5, bg_rect.position.y + 13), name, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 1, 1))

func _draw_weather(rect: Rect2) -> void:
	if weather == "clear":
		return
	if weather == "rain":
		draw_rect(rect, Color(0.3, 0.4, 0.7, 0.18), true)
		for i in range(80):
			var seed_x := fmod(float(i) * 53.7, rect.size.x)
			var seed_y := fmod(float(i) * 91.3 + _weather_t * 600.0, rect.size.y)
			var px := rect.position.x + seed_x
			var py := rect.position.y + seed_y
			draw_line(Vector2(px, py), Vector2(px - 3.0, py + 12.0), Color(0.7, 0.8, 1.0, 0.5), 1.0)
	elif weather == "fog":
		draw_rect(rect, Color(0.75, 0.75, 0.8, 0.35), true)
	elif weather == "snow":
		draw_rect(rect, Color(0.85, 0.9, 1.0, 0.12), true)
		for i in range(100):
			var px := rect.position.x + fmod(float(i) * 37.1 + sin(_weather_t + float(i)) * 15.0, rect.size.x)
			var py := rect.position.y + fmod(float(i) * 73.9 + _weather_t * 40.0, rect.size.y)
			draw_circle(Vector2(px, py), 1.8, Color(1, 1, 1, 0.75))
	elif weather == "storm":
		draw_rect(rect, Color(0.15, 0.2, 0.35, 0.30), true)
		for i in range(120):
			var px := rect.position.x + fmod(float(i) * 61.3, rect.size.x)
			var py := rect.position.y + fmod(float(i) * 89.7 + _weather_t * 900.0, rect.size.y)
			draw_line(Vector2(px, py), Vector2(px - 5.0, py + 16.0), Color(0.7, 0.8, 1.0, 0.6), 1.2)
		if fmod(_weather_t, 4.0) < 0.12:
			draw_rect(rect, Color(1, 1, 1, 0.35), true)

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
