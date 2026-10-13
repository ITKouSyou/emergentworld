# Part 20B - C：客户端加探索按钮
from pathlib import Path

# 1. api.gd 加 explore
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func explore(" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal explore_done(data: Dictionary)

func explore() -> void:
	_request("POST", "/explore", {}, "explore_done")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 explore")
    else:
        print("[fail] api.gd 锚点未找到")
else:
    print("[skip] api.gd 已有 explore")

# 2. main.gd
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 加成员变量
if "explore_btn" not in t:
    anchor = "var player_name_label: Label\n"
    addition = "var explore_btn: Button\nvar explore_result_label: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print("[fix] main.gd 加 explore 成员变量")

# 2.2 连接信号
if "explore_done" not in t:
    anchor = "\tapi.player_allocated.connect(_on_player_allocated)\n"
    addition = anchor + "\tapi.explore_done.connect(_on_explore_done)\n"
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] main.gd 连接 explore_done")

# 2.3 在 _build_player_tab 里加按钮
anchor_build = '''	var attr_title := Label.new()
	attr_title.text = "属性（可分配点会亮起 [+]）"
	player_tab_panel.add_child(attr_title)'''

addition_build = '''	var explore_row := HBoxContainer.new()
	explore_row.add_theme_constant_override("separation", 8)
	player_tab_panel.add_child(explore_row)

	explore_btn = Button.new()
	explore_btn.text = "外出探索"
	explore_btn.pressed.connect(_on_explore_pressed)
	explore_row.add_child(explore_btn)

	explore_result_label = RichTextLabel.new()
	explore_result_label.bbcode_enabled = true
	explore_result_label.fit_content = true
	explore_result_label.custom_minimum_size = Vector2(0, 60)
	player_tab_panel.add_child(explore_result_label)

	var attr_title := Label.new()
	attr_title.text = "属性（可分配点会亮起 [+]）"
	player_tab_panel.add_child(attr_title)'''

if anchor_build in t and "explore_btn" not in t.split("attr_title")[0]:
    t = t.replace(anchor_build, addition_build, 1)
    print("[fix] main.gd 加探索按钮")

# 2.4 加处理函数
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

	# 地点
	if data.get("found_location", false):
		lines.append("[color=gold][b]发现新地点：%s[/b][/color]" % str(data.get("target_label", "")))
	else:
		lines.append("[color=gray]未能发现新地点[/color]")

	# flavor
	var flavor: String = str(data.get("flavor", ""))
	if flavor != "":
		lines.append("[i]%s[/i]" % flavor)

	# check
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

	# message
	var msg: String = str(data.get("message", ""))
	if msg != "":
		lines.append(msg)

	# item
	var it = data.get("found_item")
	if it is Dictionary:
		lines.append("[color=gold]拾得：[b]%s[/b]（%s）[/color]" % [
			str(it.get("name", "?")), str(it.get("kind", "")),
		])

	# exp
	var exp_gain: int = int(data.get("exp_gain", 0))
	if exp_gain > 0:
		lines.append("[color=yellow]经验 +%d[/color]" % exp_gain)

	explore_result_label.text = "\\n".join(lines)

	# 刷新 player 与地图
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
    p.write_text(t, encoding="utf-8")
    print("[fix] main.gd 加探索处理函数")
else:
    p.write_text(t, encoding="utf-8")
    print("[skip] main.gd 已有探索函数")

print()
print("C 部分完成。")
print()
print("接下来：")
print("  1. python fix20b_a.py     # 如果还没跑")
print("  2. python fix20b_b.py     # 如果还没跑")
print("  3. python fix20b_c.py")
print("  4. pytest -v")
print("  5. Remove-Item data\\world.db")
print("  6. python tools\\seed_world.py --npc 10")
print("  7. uvicorn server.main:app --reload")