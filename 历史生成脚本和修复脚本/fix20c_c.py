# map_view.gd 加玩家显示
from pathlib import Path

p = Path("client/map_view.gd")
t = p.read_text(encoding="utf-8")

# 加变量
if "var player_pos" not in t:
    anchor = "var selected_npc_id: String = \"\"\n"
    addition = "var selected_npc_id: String = \"\"\nvar player_pos: Variant = null\n"
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] 加 player_pos 变量")

# set_data 里提取玩家
if "player_pos = data.get" not in t:
    anchor = '\tseason = str(data.get("season", "spring"))\n\tweather = str(data.get("weather", "clear"))\n\tqueue_redraw()'
    addition = '\tseason = str(data.get("season", "spring"))\n\tweather = str(data.get("weather", "clear"))\n\tplayer_pos = data.get("player", null)\n\tqueue_redraw()'
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] set_data 提取 player_pos")

# _draw 里画玩家（在 NPC 之后、环境光之前）
if "_draw_player" not in t:
    # 找 NPC 循环结束的位置：在 "# 环境光" 之前插入
    anchor = "\t# 环境光\n\tdraw_rect(rect, _ambient_overlay(), true)"
    addition = "\t# 玩家\n\t_draw_player(rect)\n\n\t# 环境光\n\tdraw_rect(rect, _ambient_overlay(), true)"
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] 加 _draw_player 调用")
    else:
        print("[fail] _draw 环境光锚点未找到")

    # 加函数
    tail = '''

func _draw_player(rect: Rect2) -> void:
	if player_pos == null or not player_pos is Dictionary:
		return
	var pdata: Dictionary = player_pos
	var nx := float(pdata.get("x", 0.5))
	var ny := float(pdata.get("y", 0.5))
	var p := _norm_to_screen(nx, ny, rect)

	# 外光晕
	draw_circle(p, NPC_DOT_RADIUS + 6.0, Color(1.0, 0.95, 0.4, 0.25))
	# 主体（金色）
	draw_circle(p, NPC_DOT_RADIUS + 1.5, Color(1.0, 0.85, 0.2, 1.0))
	# 边线
	draw_arc(p, NPC_DOT_RADIUS + 1.5, 0.0, TAU, 24, Color(0.5, 0.35, 0.0, 1.0), 2.0, true)
	# 内点
	draw_circle(p, 2.0, Color(0.3, 0.2, 0.0, 1.0))

	# 名字
	var name: String = str(pdata.get("name", "你"))
	if name == "":
		name = "你"
	var tw := _text_width(name, font_size)
	var bg_rect := Rect2(p.x - tw / 2.0 - 5, p.y - NPC_DOT_RADIUS - 26, tw + 10, 17)
	draw_rect(bg_rect, Color(0.2, 0.15, 0.0, 0.85), true)
	draw_string(font, Vector2(bg_rect.position.x + 5, bg_rect.position.y + 13),
		name, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1.0, 0.95, 0.5))
'''
    t = t.rstrip() + "\n" + tail
    print("[fix] 加 _draw_player 函数")

p.write_text(t, encoding="utf-8")
print()
print("C 部分完成")