# Part 90B：前端装备 UI
from pathlib import Path

# ============================================================
# 1. api.gd 加装备方法
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func equip_item" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal equip_done(data: Dictionary)
signal unequip_done(data: Dictionary)

func equip_item(item_id: String) -> void:
	_request("POST", "/equip", {"item_id": item_id}, "equip_done")

func unequip_slot(slot: String) -> void:
	_request("POST", "/unequip", {"slot": slot}, "unequip_done")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加装备方法")

# ============================================================
# 2. main.gd
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var equip_slot_labels:" not in t:
    anchor = "var current_item_id: String = \"\"\n"
    if anchor in t:
        add = "var equip_btn: Button\nvar equip_slot_labels: Dictionary = {}\n"
        t = t.replace(anchor, anchor + add, 1)
        print("[fix] 加装备变量")

# 2.2 信号连接
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    body = t[start:after]
    if "api.equip_done.connect" not in body:
        lines = body.split("\n")
        insert_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            s = lines[i].strip()
            if s.startswith("api.") and ".connect(" in s:
                insert_idx = i
                break
        if insert_idx >= 0:
            indent = lines[insert_idx][:len(lines[insert_idx]) - len(lines[insert_idx].lstrip())]
            lines.insert(insert_idx + 1, indent + "api.equip_done.connect(_on_equip_done)")
            lines.insert(insert_idx + 2, indent + "api.unequip_done.connect(_on_unequip_done)")
            body = "\n".join(lines)
            t = t[:start] + body + t[after:]
            p.write_text(t, encoding="utf-8")
            print("[fix] 连接装备信号")

t = p.read_text(encoding="utf-8")

# 2.3 在 _build_player_tab 里加装备槽显示
if "装备槽" not in t:
    # 找玩家统计行的位置
    old = '''	player_stats_label = RichTextLabel.new()
	player_stats_label.bbcode_enabled = true
	player_stats_label.fit_content = true
	player_stats_label.custom_minimum_size = Vector2(0, 120)
	player_tab_panel.add_child(player_stats_label)'''
    new = '''	player_stats_label = RichTextLabel.new()
	player_stats_label.bbcode_enabled = true
	player_stats_label.fit_content = true
	player_stats_label.custom_minimum_size = Vector2(0, 120)
	player_tab_panel.add_child(player_stats_label)

	var equip_title := Label.new()
	equip_title.text = "[装备槽]"
	equip_title.add_theme_font_size_override("font_size", 14)
	player_tab_panel.add_child(equip_title)

	# 三个槽位显示
	for slot_key in ["weapon", "armor", "accessory"]:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)

		var slot_lbl := Label.new()
		slot_lbl.custom_minimum_size = Vector2(60, 0)
		slot_lbl.text = {"weapon": "武器", "armor": "护甲", "accessory": "饰物"}.get(slot_key, slot_key)
		row.add_child(slot_lbl)

		var val_lbl := Label.new()
		val_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		val_lbl.text = "（空）"
		row.add_child(val_lbl)

		var un_btn := Button.new()
		un_btn.text = "卸下"
		un_btn.disabled = true
		var sk := slot_key
		un_btn.pressed.connect(func(): _on_unequip_pressed(sk))
		row.add_child(un_btn)

		player_tab_panel.add_child(row)
		equip_slot_labels[slot_key] = {"label": val_lbl, "btn": un_btn}'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 加装备槽 UI")
    else:
        print("[skip] 装备槽锚点未找到")

# 2.4 更新 _render_player_panel 显示装备
t = p.read_text(encoding="utf-8")
old2 = '''	var attrs: Dictionary = player_data.get("attributes", {})
	var attr_labels := {
		"strength": "力量", "agility": "敏捷", "intelligence": "智慧",
		"perception": "感知", "charisma": "魅力", "luck": "运气",
	}
	for key in player_attr_rows.keys():
		var r: Dictionary = player_attr_rows[key]
		var v: int = int(attrs.get(key, 5))
		(r["label"] as Label).text = str(v)
		(r["btn"] as Button).disabled = unspent <= 0 or v >= 20'''

new2 = '''	# 属性显示用"基础 + 装备加成"
	var base_attrs: Dictionary = player_data.get("attributes", {})
	var total_attrs: Dictionary = player_data.get("total_attributes", base_attrs)
	for key in player_attr_rows.keys():
		var r: Dictionary = player_attr_rows[key]
		var v: int = int(base_attrs.get(key, 5))
		var tv: int = int(total_attrs.get(key, v))
		if tv != v:
			(r["label"] as Label).text = "%d [color=gold](%d)[/color]" % [v, tv]
		else:
			(r["label"] as Label).text = str(v)
		(r["btn"] as Button).disabled = unspent <= 0 or v >= 20

	# 装备槽
	var eq_slots: Array = player_data.get("equipment_slots", [])
	for slot_data in eq_slots:
		if not slot_data is Dictionary:
			continue
		var sk: String = str(slot_data.get("slot", ""))
		if not equip_slot_labels.has(sk):
			continue
		var rec: Dictionary = equip_slot_labels[sk]
		var nm: String = str(slot_data.get("item_name", "（空）"))
		var item_id: String = str(slot_data.get("item_id", ""))
		if nm == "" or nm == "（空）":
			(rec["label"] as Label).text = "（空）"
			(rec["btn"] as Button).disabled = true
		else:
			var attrs_dict: Dictionary = slot_data.get("attributes", {})
			var attr_strs: Array[String] = []
			for k in attrs_dict.keys():
				var k_zh: String = {
					"strength": "力量", "agility": "敏捷", "intelligence": "智慧",
					"perception": "感知", "charisma": "魅力", "luck": "运气",
				}.get(str(k), str(k))
				attr_strs.append("%s+%d" % [k_zh, int(attrs_dict[k])])
			(rec["label"] as Label).text = "%s  %s" % [nm, " ".join(attr_strs)]
			(rec["btn"] as Button).disabled = false'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _render_player_panel 显示装备加成")

# 2.5 追加处理函数
t = p.read_text(encoding="utf-8")
if "_on_equip_done" not in t:
    tail = '''

func _on_unequip_pressed(slot: String) -> void:
	api.unequip_slot(slot)


func _on_equip_done(data: Dictionary) -> void:
	api.fetch_player()
	api.fetch_items(200)
	status_label.text = "[color=gold]装备：%s（%s）[/color]" % [
		str(data.get("item_name", "")),
		str(data.get("slot_label", "")),
	]


func _on_unequip_done(data: Dictionary) -> void:
	api.fetch_player()
	api.fetch_items(200)
	status_label.text = "[color=gray]已卸下 %s[/color]" % str(data.get("slot", ""))


func _on_equip_pressed() -> void:
	if current_item_id == "":
		return
	api.equip_item(current_item_id)
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 加装备处理函数")

# 2.6 物品详情里加"装备"按钮
t = p.read_text(encoding="utf-8")
old3 = '''	var item_buttons := HBoxContainer.new()
	item_buttons.add_theme_constant_override("separation", 6)
	item_tab.add_child(item_buttons)

	use_btn = Button.new()
	use_btn.text = "使用"
	use_btn.pressed.connect(_on_use_pressed)
	item_buttons.add_child(use_btn)'''
new3 = '''	var item_buttons := HBoxContainer.new()
	item_buttons.add_theme_constant_override("separation", 6)
	item_tab.add_child(item_buttons)

	use_btn = Button.new()
	use_btn.text = "使用"
	use_btn.pressed.connect(_on_use_pressed)
	item_buttons.add_child(use_btn)

	equip_btn = Button.new()
	equip_btn.text = "装备"
	equip_btn.pressed.connect(_on_equip_pressed)
	item_buttons.add_child(equip_btn)'''
if old3 in t:
    t = t.replace(old3, new3, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 加装备按钮")

# 2.7 _render_item_detail 里按类别启用按钮
t = p.read_text(encoding="utf-8")
old4 = '''		var owner_id: String = str(it.get("owner_id", ""))
		var is_player := owner_id == "player"
		var is_npc := owner_id != "" and owner_id != "player"
		use_btn.disabled = not is_player
		give_btn.disabled = not is_player
		drop_btn.disabled = not is_player
		take_btn.disabled = not is_npc
		return'''
new4 = '''		var owner_id: String = str(it.get("owner_id", ""))
		var is_player := owner_id == "player"
		var is_npc := owner_id != "" and owner_id != "player"
		use_btn.disabled = not is_player
		give_btn.disabled = not is_player
		drop_btn.disabled = not is_player
		take_btn.disabled = not is_npc

		# 装备按钮：仅装备类可用
		var cat: String = str(it.get("category", "material"))
		if equip_btn != null:
			equip_btn.disabled = not (is_player and cat == "equipment")
		return'''
if old4 in t:
    t = t.replace(old4, new4, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 按类别启用装备按钮")

print()
print("===== 完成 =====")
print("pytest -v")
print("uvicorn server.main:app")
print("Godot 完全关闭重开")