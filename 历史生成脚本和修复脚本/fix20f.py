# Part 20F：前端加行动按钮组 + 最近活动
from pathlib import Path

# 1. api.gd 加 do_action
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
if "func do_action(" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal action_done(data: Dictionary)

func do_action(action_name: String) -> void:
	_request("POST", "/action", {"action": action_name}, "action_done")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 do_action")
else:
    print("[skip] api.gd 已有 do_action")

# 2. main.gd
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var action_result_label:" not in t:
    anchor = "var explore_result_label: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor
            + "var action_result_label: RichTextLabel\n"
            + "var action_buttons_row: HBoxContainer\n", 1)
        print("[fix] main.gd 加变量")
    else:
        # 尝试其它锚点
        anchor2 = "var explore_btn: Button\n"
        if anchor2 in t:
            t = t.replace(anchor2, anchor2
                + "var explore_result_label: RichTextLabel\n"
                + "var action_result_label: RichTextLabel\n"
                + "var action_buttons_row: HBoxContainer\n", 1)
            print("[fix] main.gd 加变量（备用）")

# 2.2 信号连接
if "action_done.connect" not in t:
    anchor = "\tapi.player_allocated.connect(_on_player_allocated)\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\tapi.action_done.connect(_on_action_done)\n", 1)
        print("[fix] main.gd 连接 action_done")

# 2.3 在 _ensure_explore_ui 里加行动按钮组（如果函数存在）
if "func _ensure_action_ui" not in t:
    tail = '''

func _ensure_action_ui() -> void:
	if player_tab_panel == null:
		return
	if action_buttons_row != null and is_instance_valid(action_buttons_row):
		return

	action_buttons_row = HBoxContainer.new()
	action_buttons_row.add_theme_constant_override("separation", 4)

	var actions := [
		["explore", "外出探索"],
		["gather", "采集"],
		["hunt", "打猎"],
		["train", "修炼"],
		["socialize", "社交"],
	]
	for pair in actions:
		var btn := Button.new()
		btn.text = pair[1]
		var akey: String = str(pair[0])
		btn.pressed.connect(func(): _on_action_pressed(akey))
		action_buttons_row.add_child(btn)

	action_result_label = RichTextLabel.new()
	action_result_label.bbcode_enabled = true
	action_result_label.fit_content = true
	action_result_label.custom_minimum_size = Vector2(0, 100)

	# 插入到 player_tab_panel 里"属性"标题之前
	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	player_tab_panel.add_child(action_buttons_row)
	player_tab_panel.move_child(action_buttons_row, insert_index)
	player_tab_panel.add_child(action_result_label)
	player_tab_panel.move_child(action_result_label, insert_index + 1)


func _on_action_pressed(action_name: String) -> void:
	if not player_created:
		return
	# 禁用所有按钮
	if action_buttons_row != null:
		for c in action_buttons_row.get_children():
			if c is Button:
				(c as Button).disabled = true
	if action_result_label != null:
		action_result_label.text = "[i]你开始了...[/i]"
	api.do_action(action_name)


func _on_action_done(data: Dictionary) -> void:
	if action_buttons_row != null:
		for c in action_buttons_row.get_children():
			if c is Button:
				(c as Button).disabled = false

	var lines: Array[String] = []
	var action_label: String = str(data.get("action_label", ""))

	# 判定结果
	var check = data.get("check", {})
	if check is Dictionary and check.has("result"):
		var result_zh: String = {
			"critical": "大成功",
			"success": "成功",
			"partial": "勉强",
			"failure": "失败",
		}.get(str(check.get("result", "")), "")
		lines.append("[color=cyan]%s  %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]" % [
			str(check.get("attribute", "")),
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

	# 世界事件
	var we = data.get("world_event")
	if we is Dictionary:
		lines.append("")
		lines.append("[color=orange]→ 世界也在转动：[/color][b]%s[/b] %s" % [
			str(we.get("template_label", "")),
			str(we.get("summary", "")),
		])
		if bool(we.get("awaiting_player", false)):
			lines.append("[color=orange]（有一件事正在等你决定，见"事件"Tab）[/color]")

	# 社交
	var sd = data.get("social")
	if sd is Dictionary:
		var lines_arr: Array = sd.get("lines", [])
		if not lines_arr.is_empty():
			lines.append("")
			lines.append("[color=cyan]你听见有人说话：[/color]")
			for line in lines_arr:
				if line is Dictionary:
					lines.append("   [b]%s[/b]：%s" % [
						str(line.get("speaker", "")),
						str(line.get("text", "")),
					])

	if action_result_label != null:
		action_result_label.text = "\\n".join(lines)

	# 刷新 player
	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	# 刷新世界
	api.fetch_world_state()
	api.fetch_map()
	api.fetch_events(30)
	api.fetch_items(100)
	api.fetch_npcs()
'''
    t = t.rstrip() + "\n" + tail
    print("[fix] main.gd 加 _ensure_action_ui + handler")

# 2.4 在 _ensure_explore_ui 或 _ready 里调用 _ensure_action_ui
if "_ensure_action_ui()" not in t.replace("func _ensure_action_ui", ""):
    if "func _ensure_explore_ui" in t:
        # 在 _ensure_explore_ui 末尾追加调用
        anchor = "func _ensure_explore_ui() -> void:\n\tif player_tab_panel == null:"
        if anchor in t:
            t = t.replace(anchor, "_ensure_explore_ui_orig() -> void:\n\tif player_tab_panel == null:", 1)
            print("[skip] 复杂，改用简单方案")

# 简单方案：在 _ready 末尾调用
if "_ensure_action_ui()" not in t:
    anchor = "\tapi.fetch_i18n()\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\t_ensure_action_ui()\n", 1)
        print("[fix] 在 _ready 里调用 _ensure_action_ui")

p.write_text(t, encoding="utf-8")
print()
print("前端完成。Godot 完全关闭重开，按 F5。")