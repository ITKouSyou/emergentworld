# 用动态挂载方式加探索按钮，不依赖原有函数体
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 变量声明（如果缺）
if "var explore_btn:" not in t:
    anchor = "var player_name_label: Label\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "var explore_btn: Button\nvar explore_result_label: RichTextLabel\n", 1)
        print("[fix] 加 explore 变量")
    else:
        # 备用锚点
        anchor = "var player_stats_label: RichTextLabel\n"
        if anchor in t:
            t = t.replace(anchor, anchor + "var explore_btn: Button\nvar explore_result_label: RichTextLabel\n", 1)
            print("[fix] 加 explore 变量（备用锚点）")
else:
    print("[skip] 已有 explore 变量")

# 2. 信号连接（如果缺）
if "explore_done.connect" not in t:
    anchor = "\tapi.player_allocated.connect(_on_player_allocated)\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\tapi.explore_done.connect(_on_explore_done)\n", 1)
        print("[fix] 连接 explore_done")
    else:
        print("[fail] 信号连接锚点未找到")
else:
    print("[skip] 已有 explore_done 连接")

# 3. 在 _build_ui 末尾调用动态挂载
if "_ensure_explore_ui" not in t:
    # 尝试多个锚点
    anchors = [
        "\t_build_player_tab(tabs_root)\n\t_build_world_tab(tabs_root)\n",
        "\t_build_player_tab(parent)\n\t_build_world_tab(parent)\n",
    ]
    inserted = False
    for anchor in anchors:
        if anchor in t:
            new = anchor + "\t_ensure_explore_ui()\n"
            t = t.replace(anchor, new, 1)
            print("[fix] 插入 _ensure_explore_ui 调用")
            inserted = True
            break

    if not inserted:
        print("[fail] _build_ui 锚点未找到，尝试在 _ready 里插入")
        anchor = "\t_build_ui()\n"
        if anchor in t:
            t = t.replace(anchor, anchor + "\t_ensure_explore_ui()\n", 1)
            print("[fix] 在 _ready 里插入 _ensure_explore_ui")
else:
    print("[skip] 已有 _ensure_explore_ui")

# 4. 加 _ensure_explore_ui 和 handler 函数
if "_ensure_explore_ui" not in t.split("\n\nfunc ")[-1] and "func _ensure_explore_ui" not in t:
    tail = '''

func _ensure_explore_ui() -> void:
	if player_tab_panel == null:
		push_warning("player_tab_panel 未初始化，无法加探索按钮")
		return

	# 避免重复
	if explore_btn != null and is_instance_valid(explore_btn):
		return

	# 在 player_tab_panel 里找一个位置插入，放在"属性"标题上方
	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	# 探索行
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)

	explore_btn = Button.new()
	explore_btn.text = "外出探索"
	explore_btn.pressed.connect(_on_explore_pressed)
	row.add_child(explore_btn)

	player_tab_panel.add_child(row)
	player_tab_panel.move_child(row, insert_index)

	# 结果框
	explore_result_label = RichTextLabel.new()
	explore_result_label.bbcode_enabled = true
	explore_result_label.fit_content = true
	explore_result_label.custom_minimum_size = Vector2(0, 90)
	player_tab_panel.add_child(explore_result_label)
	player_tab_panel.move_child(explore_result_label, insert_index + 1)


func _on_explore_pressed() -> void:
	if not player_created:
		return
	explore_btn.disabled = true
	explore_result_label.text = "[i]你走出村庄，四处张望...[/i]"
	api.explore()


func _on_explore_done(data: Dictionary) -> void:
	if explore_btn != null and is_instance_valid(explore_btn):
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

	if explore_result_label != null and is_instance_valid(explore_result_label):
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
    print("[fix] 加 _ensure_explore_ui + handlers")

p.write_text(t, encoding="utf-8")
print()
print("D 部分完成。回 Godot 按 F5")