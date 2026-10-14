# 地图点击已发现地点 → 前往
from pathlib import Path

# ============================================================
# 1. map_view.gd：加 location_clicked 信号 + 点击判定
# ============================================================
p = Path("client/map_view.gd")
t = p.read_text(encoding="utf-8")

# 加信号
if "signal location_clicked" not in t:
    old_sig = 'signal npc_clicked(npc_id: String)'
    new_sig = 'signal npc_clicked(npc_id: String)\nsignal location_clicked(location_id: String)'
    if old_sig in t:
        t = t.replace(old_sig, new_sig, 1)
        print("[fix] map_view 加 location_clicked 信号")

# 替换 _gui_input，先判地点再判 NPC
old_input = '''func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_update_hover(event.position)
	elif event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_update_hover(event.position)
			if hovered_npc_id != "":
				npc_clicked.emit(hovered_npc_id)'''

new_input = '''func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_update_hover(event.position)
	elif event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_update_hover(event.position)
			# 先判 NPC
			if hovered_npc_id != "":
				npc_clicked.emit(hovered_npc_id)
				return
			# 再判地点
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
	return ""'''

if old_input in t:
    t = t.replace(old_input, new_input, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] map_view _gui_input 加地点点击")
else:
    print("[fail] map_view _gui_input 锚点未找到")

# ============================================================
# 2. main.gd：连接信号 + 处理
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 连接信号
if "map_view.location_clicked.connect" not in t:
    old_conn = 'map_view.npc_clicked.connect(_on_map_npc_clicked)'
    new_conn = '''map_view.npc_clicked.connect(_on_map_npc_clicked)
	map_view.location_clicked.connect(_on_map_location_clicked)'''
    if old_conn in t:
        t = t.replace(old_conn, new_conn, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.gd 连接 location_clicked")

# 加处理函数
t = p.read_text(encoding="utf-8")
if "func _on_map_location_clicked" not in t:
    tail = '''

func _on_map_location_clicked(location_id: String) -> void:
	if not player_created:
		return
	var cur_loc: String = str(player_data.get("location_id", ""))
	if location_id == cur_loc:
		status_label.text = "[color=gray]你已经在这里了[/color]"
		return

	print("[ui] 地图点击前往：%s" % location_id)
	if travel_btn != null and is_instance_valid(travel_btn):
		travel_btn.disabled = true
	if travel_result_label != null:
		travel_result_label.text = "[i]你启程了...[/i]"
	api.travel(location_id)
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] main.gd 加 _on_map_location_clicked")

print()
print("Godot 完全关闭重开，按 F5")