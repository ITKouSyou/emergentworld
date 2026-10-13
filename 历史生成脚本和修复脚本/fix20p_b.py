# Part 20P-B：前端加前往 UI
from pathlib import Path

# ---------- 1. api.gd 加 travel ----------
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func travel(" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal travel_done(data: Dictionary)

func travel(location_id: String) -> void:
	_request("POST", "/travel", {"location_id": location_id}, "travel_done")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 travel")
    else:
        print("[fail] api.gd 锚点未找到")
else:
    print("[skip] api.gd 已有 travel")

# ---------- 2. main.gd ----------
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量声明
if "var travel_option:" not in t:
    anchor = "var action_result_label: RichTextLabel\n"
    addition = "var travel_option: OptionButton\nvar travel_btn: Button\nvar travel_result_label: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + addition, 1)
        print("[fix] main.gd 加 travel 变量")
    else:
        # 备用
        anchor2 = "var player_name_label: Label\n"
        if anchor2 in t:
            t = t.replace(anchor2, anchor2 + addition, 1)
            print("[fix] main.gd 加 travel 变量（备用）")

# 2.2 信号连接（强制插到 _connect_signals 里）
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    end = t.find("\n\nfunc ", start + 1)
    if end < 0:
        end = len(t)
    body = t[start:end]

    if "api.travel_done.connect" not in body:
        anchor = "        api.request_failed.connect(_on_request_failed)"
        if anchor not in body:
            anchor = "\tapi.request_failed.connect(_on_request_failed)"
        if anchor in body:
            indent = anchor[:len(anchor) - len(anchor.lstrip())]
            new_line = indent + "api.travel_done.connect(_on_travel_done)"
            body = body.replace(anchor, new_line + "\n" + anchor, 1)
            t = t[:start] + body + t[end:]
            print("[fix] 连接 travel_done")
        else:
            print("[fail] travel_done 连接锚点未找到")
    else:
        print("[skip] 已有 travel_done 连接")

p.write_text(t, encoding="utf-8")

# 2.3 追加函数（幂等：只在不存在时加）
t = p.read_text(encoding="utf-8")

if "_build_travel_row" not in t:
    tail = '''

func _build_travel_row() -> void:
	# 在 player_tab_panel 里，"外出探索"按钮组上方插入前往行
	if player_tab_panel == null:
		return
	if travel_option != null and is_instance_valid(travel_option):
		return

	# 找一个插入位置：属性标题上方
	var insert_index := player_tab_panel.get_child_count()
	for i in range(player_tab_panel.get_child_count()):
		var c := player_tab_panel.get_child(i)
		if c is Label:
			var lbl := c as Label
			if lbl.text.begins_with("属性"):
				insert_index = i
				break

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	row.name = "TravelRow"

	var lbl_title := Label.new()
	lbl_title.text = "前往："
	row.add_child(lbl_title)

	travel_option = OptionButton.new()
	travel_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(travel_option)

	travel_btn = Button.new()
	travel_btn.text = "出发"
	travel_btn.pressed.connect(_on_travel_pressed)
	row.add_child(travel_btn)

	player_tab_panel.add_child(row)
	player_tab_panel.move_child(row, insert_index)

	travel_result_label = RichTextLabel.new()
	travel_result_label.bbcode_enabled = true
	travel_result_label.fit_content = true
	travel_result_label.custom_minimum_size = Vector2(0, 40)
	player_tab_panel.add_child(travel_result_label)
	player_tab_panel.move_child(travel_result_label, insert_index + 1)


func _refresh_travel_options() -> void:
	if travel_option == null or not is_instance_valid(travel_option):
		return
	travel_option.clear()
	var known: Array = player_data.get("known_locations", [])
	var current_id: String = str(player_data.get("location_id", ""))
	for k in known:
		if not k is Dictionary:
			continue
		var label: String = str(k.get("label", k.get("id", "?")))
		if bool(k.get("current", false)):
			label += "（你在这里）"
		travel_option.add_item(label)
		travel_option.set_item_metadata(travel_option.item_count - 1, str(k.get("id", "")))
	# 默认选中第一个非当前位置
	for i in range(travel_option.item_count):
		var meta: String = str(travel_option.get_item_metadata(i))
		if meta != current_id:
			travel_option.select(i)
			break


func _on_travel_pressed() -> void:
	if not player_created or travel_option == null:
		return
	var idx := travel_option.selected
	if idx < 0:
		return
	var loc_id: String = str(travel_option.get_item_metadata(idx))
	if loc_id == "":
		return
	travel_btn.disabled = true
	travel_result_label.text = "[i]你启程了...[/i]"
	api.travel(loc_id)


func _on_travel_done(data: Dictionary) -> void:
	if travel_btn != null and is_instance_valid(travel_btn):
		travel_btn.disabled = false

	var from_label: String = str(data.get("from_label", ""))
	var to_label: String = str(data.get("to_label", ""))
	if travel_result_label != null:
		travel_result_label.text = "[color=cyan]你从【%s】来到【%s】[/color]" % [from_label, to_label]

	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	api.fetch_world_state()
	api.fetch_map()
	api.fetch_events(30)
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] main.gd 加 travel UI + handler")

# 2.4 在 _ready 或 _ensure_action_ui 里调用 _build_travel_row
t = p.read_text(encoding="utf-8")
if "_build_travel_row()" not in t.replace("func _build_travel_row", ""):
    anchor = "\t_ensure_action_ui()\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "\t_build_travel_row()\n", 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 调用 _build_travel_row")
    else:
        # 备用：在 _build_ui() 后
        anchor2 = "\t_build_ui()\n"
        if anchor2 in t:
            t = t.replace(anchor2, anchor2 + "\t_build_travel_row()\n", 1)
            p.write_text(t, encoding="utf-8")
            print("[fix] 调用 _build_travel_row（备用）")
        else:
            print("[fail] _build_travel_row 调用锚点未找到")
else:
    print("[skip] 已调用 _build_travel_row")

# 2.5 在 _render_player_panel 末尾刷新下拉框
t = p.read_text(encoding="utf-8")
if "_refresh_travel_options()" not in t.replace("func _refresh_travel_options", ""):
    # 找 _render_player_panel 结尾
    start = t.find("func _render_player_panel() -> void:")
    if start >= 0:
        end = t.find("\n\nfunc ", start + 1)
        if end < 0:
            end = len(t)
        body = t[start:end]
        # 在函数末尾插入
        body_new = body.rstrip() + "\n\t_refresh_travel_options()\n"
        t = t[:start] + body_new + t[end:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _render_player_panel 末尾刷新 travel 下拉")
    else:
        print("[fail] _render_player_panel 未找到")
else:
    print("[skip] 已刷新 travel 下拉")

print()
print("B 部分完成")