# 1. 探索按钮 2. 玩家所在地用中文
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# ---- 探索按钮 ----
if "explore_btn" not in t:
    anchor = '''	var attr_title := Label.new()
	attr_title.text = "属性（可分配点会亮起 [+]）"
	player_tab_panel.add_child(attr_title)'''

    addition = '''	var explore_row := HBoxContainer.new()
	explore_row.add_theme_constant_override("separation", 8)
	player_tab_panel.add_child(explore_row)

	explore_btn = Button.new()
	explore_btn.text = "外出探索"
	explore_btn.pressed.connect(_on_explore_pressed)
	explore_row.add_child(explore_btn)

	explore_result_label = RichTextLabel.new()
	explore_result_label.bbcode_enabled = true
	explore_result_label.fit_content = true
	explore_result_label.custom_minimum_size = Vector2(0, 80)
	player_tab_panel.add_child(explore_result_label)

	var attr_title := Label.new()
	attr_title.text = "属性（可分配点会亮起 [+]）"
	player_tab_panel.add_child(attr_title)'''

    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] 加探索按钮 UI")
    else:
        print("[fail] 探索按钮锚点未找到")
else:
    print("[skip] 已有 explore_btn")

# ---- 变量声明 ----
if "var explore_btn:" not in t:
    anchor = "var player_name_label: Label\n"
    addition = "var explore_btn: Button\nvar explore_result_label: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print("[fix] 加 explore 变量声明")
else:
    print("[skip] 已有 explore 变量")

# ---- 信号连接 ----
if "explore_done" not in t.split("_connect_signals")[1].split("func ")[0] if "_connect_signals" in t else False:
    anchor = "\tapi.player_allocated.connect(_on_player_allocated)\n"
    addition = anchor + "\tapi.explore_done.connect(_on_explore_done)\n"
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] 连接 explore_done 信号")
else:
    print("[skip] 已有 explore_done 连接（或判断失败）")

# 保险：直接再检查
if "_on_explore_done" not in t and "explore_done.connect" not in t:
    anchor = "\tapi.player_allocated.connect(_on_player_allocated)\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\tapi.explore_done.connect(_on_explore_done)\n", 1)
        print("[fix-2] 连接 explore_done 信号")

# ---- 处理函数 ----
if "_on_explore_pressed" not in t:
    tail = '''

func _on_explore_pressed() -> void:
	if not player_created:
		return
	explore_btn.disabled = true
	explore_result_label.text = "[i]你走出村庄，四处张望...[/i]"
	api.explore()


func _on_explore_done(data: Dictionary) -> void:
	explore_btn.disabled = false

	var lines: Array[String] = []

	if data.get("found_location", false):
		lines.append("[color=gold][b]发现新地点：%s[/b][/color]" % str(data.get("target_label", "")))
	else:
		lines.append("[color=gray]未能发现新地点[/color]")

	var flavor: String = str(data.get("flavor", ""))
	if flavor != "":
		lines.append("[i]%s[/i]" % flavor)

	var check = data.get("check", {})
	if check is Dictionary and check.has("result"):
		var result_zh: String = {
			"critical": "大成功",
			"success": "成功",
			"partial": "勉强",
			"failure": "失败",
		}.get(str(check.get("result", "")), "")
		lines.append("[color=cyan]感知 %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]" % [
			int(check.get("base", 0)),
			int(check.get("roll", 0)),
			int(check.get("total", 0)),
			int(check.get("threshold", 0)),
			result_zh,
		])

	var msg: String = str(data.get("message", ""))
	if msg != "":
		lines.append(msg)

	var it = data.get("found_item")
	if it is Dictionary:
		lines.append("[color=gold]拾得：[b]%s[/b]（%s）[/color]" % [
			str(it.get("name", "?")), str(it.get("kind", "")),
		])

	var exp_gain: int = int(data.get("exp_gain", 0))
	if exp_gain > 0:
		lines.append("[color=yellow]经验 +%d[/color]" % exp_gain)

	explore_result_label.text = "\\n".join(lines)

	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	api.fetch_world_state()
	api.fetch_map()
	api.fetch_items(100)
	if current_npc_id != "":
		api.fetch_npc_items(current_npc_id)
'''
    t = t.rstrip() + "\n" + tail
    print("[fix] 加 explore 处理函数")

# ---- 玩家所在地用中文（fallback 硬编码） ----
old_loc = '''	lines.append("[b]所在地：[/b]%s" % loc_label)'''
new_loc = '''	# 优先用 i18n 表，fallback 用硬编码
	if loc_label == loc_id or loc_label == "":
		var fallback := {
			"village_square": "村庄广场",
			"market": "市场",
			"tavern": "酒馆",
			"home": "住处",
			"forest": "森林",
			"village_edge": "村庄边缘",
			"village_hall": "村公所",
			"deep_forest": "深山老林",
			"old_mine": "废弃矿洞",
			"river_bend": "河湾",
			"old_shrine": "古庙遗址",
			"abandoned_farm": "荒废农舍",
			"mountain_pass": "山道",
		}
		loc_label = fallback.get(loc_id, loc_id)
	lines.append("[b]所在地：[/b]%s" % loc_label)'''

if old_loc in t:
    t = t.replace(old_loc, new_loc, 1)
    print("[fix] 玩家所在地改中文 fallback")
else:
    print("[skip] 所在地锚点未找到")

p.write_text(t, encoding="utf-8")
print()
print("B 部分完成")