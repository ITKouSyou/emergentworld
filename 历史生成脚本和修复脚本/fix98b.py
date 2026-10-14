# Part 98B：前端两阶段任务 UI
from pathlib import Path

# ============================================================
# 1. api.gd 加 turn_in + active_quests
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func turn_in_quest" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal npc_active_quests_received(data: Array)
signal quest_turned_in(data: Dictionary)

func fetch_npc_active_quests(npc_id: String) -> void:
	_request("GET", "/npc/%s/active_quests" % npc_id, {}, "npc_active_quests_received")

func turn_in_quest(quest_id: String) -> void:
	_request("POST", "/quest/%s/turn_in" % quest_id, {}, "quest_turned_in")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 turn_in 方法")

# ============================================================
# 2. main.gd
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 信号连接
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    body = t[start:after]
    if "api.npc_active_quests_received.connect" not in body:
        lines = body.split("\n")
        insert_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            s = lines[i].strip()
            if s.startswith("api.") and ".connect(" in s:
                insert_idx = i
                break
        if insert_idx >= 0:
            indent = lines[insert_idx][:len(lines[insert_idx]) - len(lines[insert_idx].lstrip())]
            lines.insert(insert_idx + 1, indent + "api.npc_active_quests_received.connect(_on_npc_active_quests_received)")
            lines.insert(insert_idx + 2, indent + "api.quest_turned_in.connect(_on_quest_turned_in)")
            body = "\n".join(lines)
            t = t[:start] + body + t[after:]
            p.write_text(t, encoding="utf-8")
            print("[fix] 连接 turn_in 信号")

t = p.read_text(encoding="utf-8")

# 2.2 _on_npc_selected 也拉 active_quests
t = t.replace(
    "\tapi.fetch_npc_quests(current_npc_id)\n",
    "\tapi.fetch_npc_quests(current_npc_id)\n\tapi.fetch_npc_active_quests(current_npc_id)\n",
)

# 2.3 在 _on_npc_quests_received 里也显示待提交任务（调用两次渲染）
t = p.read_text(encoding="utf-8")
old = '''func _on_npc_quests_received(data: Array) -> void:
	npc_quests_data = data
	if npc_quests_panel == null:
		return
	for child in npc_quests_panel.get_children():
		child.queue_free()
	if data.is_empty():
		return

	var title := Label.new()
	title.text = "[委托任务]"
	title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	npc_quests_panel.add_child(title)

	for q in data:
		if not q is Dictionary:
			continue
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)

		var info := Label.new()
		var title_s: String = str(q.get("title", "?"))
		var exp_r: int = int(q.get("reward_exp", 0))
		var money_r: int = int(q.get("reward_money", 0))
		var loc_label: String = str(q.get("require_location_label", ""))
		info.text = "%s -> %s (%d经验,%d钱)" % [title_s, loc_label, exp_r, money_r]
		info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(info)

		var btn := Button.new()
		btn.text = "接受"
		var qid: String = str(q.get("id", ""))
		var nid := current_npc_id
		btn.pressed.connect(func(): _on_accept_quest_pressed(nid, qid))
		row.add_child(btn)

		npc_quests_panel.add_child(row)'''

new = '''var _npc_offer_quests: Array = []
var _npc_active_quests: Array = []


func _on_npc_quests_received(data: Array) -> void:
	_npc_offer_quests = data
	_render_npc_quests_panel()


func _on_npc_active_quests_received(data: Array) -> void:
	_npc_active_quests = data
	_render_npc_quests_panel()


func _render_npc_quests_panel() -> void:
	if npc_quests_panel == null:
		return
	for child in npc_quests_panel.get_children():
		child.queue_free()

	# 待提交优先
	if not _npc_active_quests.is_empty():
		var t1 := Label.new()
		t1.text = "[待提交]"
		t1.add_theme_color_override("font_color", Color(1.0, 0.6, 0.3))
		npc_quests_panel.add_child(t1)

		for q in _npc_active_quests:
			if not q is Dictionary:
				continue
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 6)

			var info := Label.new()
			var title_s: String = str(q.get("title", "?"))
			var exp_r: int = int(q.get("reward_exp", 0))
			var money_r: int = int(q.get("reward_money", 0))
			var ready: bool = bool(q.get("ready", false))
			var rk: String = str(q.get("require_item_kind", ""))
			var rc: int = int(q.get("require_item_count", 0))

			var status := ""
			if rc > 0:
				if ready:
					status = "[color=green]（已集齐%s）[/color]" % rk
				else:
					status = "[color=gray]（还需%s×%d）[/color]" % [rk, rc]

			info.text = "%s  (%d经验,%d钱) %s" % [title_s, exp_r, money_r, status]
			info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(info)

			var btn := Button.new()
			btn.text = "提交"
			if not ready:
				btn.disabled = true
			var qid: String = str(q.get("id", ""))
			btn.pressed.connect(func(): _on_turn_in_pressed(qid))
			row.add_child(btn)
			npc_quests_panel.add_child(row)

	# 可接受
	if not _npc_offer_quests.is_empty():
		var t2 := Label.new()
		t2.text = "[可接受]"
		t2.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
		npc_quests_panel.add_child(t2)

		for q in _npc_offer_quests:
			if not q is Dictionary:
				continue
			var row2 := HBoxContainer.new()
			row2.add_theme_constant_override("separation", 6)

			var info2 := Label.new()
			var title_s2: String = str(q.get("title", "?"))
			var exp_r2: int = int(q.get("reward_exp", 0))
			var money_r2: int = int(q.get("reward_money", 0))
			var loc_label: String = str(q.get("require_location_label", ""))
			info2.text = "%s -> %s (%d经验,%d钱)" % [title_s2, loc_label, exp_r2, money_r2]
			info2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row2.add_child(info2)

			var btn2 := Button.new()
			btn2.text = "接受"
			var qid2: String = str(q.get("id", ""))
			var nid := current_npc_id
			btn2.pressed.connect(func(): _on_accept_quest_pressed(nid, qid2))
			row2.add_child(btn2)
			npc_quests_panel.add_child(row2)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 任务面板重写（待提交 + 可接受）")
else:
    print("[skip] 任务面板已改过或锚点未匹配")

# 2.4 加 turn_in 处理
t = p.read_text(encoding="utf-8")
if "func _on_turn_in_pressed" not in t:
    tail = '''

func _on_turn_in_pressed(quest_id: String) -> void:
	api.turn_in_quest(quest_id)


func _on_quest_turned_in(data: Dictionary) -> void:
	if data.get("ok") == false:
		status_label.text = "[color=red]提交失败：%s[/color]" % str(data.get("error", ""))
		return
	status_label.text = "[color=gold]完成任务：%s（+%d经验 +%d钱）[/color]" % [
		str(data.get("title", "")),
		int(data.get("reward_exp", 0)),
		int(data.get("reward_money", 0)),
	]
	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()
	# 刷新
	api.fetch_quests()
	api.fetch_items(200)
	if current_npc_id != "":
		api.fetch_npc_active_quests(current_npc_id)
		api.fetch_npc_quests(current_npc_id)
		api.fetch_npc_items(current_npc_id)
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 加 turn_in 处理函数")

# 2.5 _on_accept_quest 后也刷新 active quests
t = p.read_text(encoding="utf-8")
old3 = '''func _on_quest_accepted(data: Dictionary) -> void:
	status_label.text = "[color=gold]已接受任务：%s[/color]" % str(data.get("title", ""))
	if npc_quests_panel != null:
		for child in npc_quests_panel.get_children():
			child.queue_free()
	api.fetch_quests()'''
new3 = '''func _on_quest_accepted(data: Dictionary) -> void:
	status_label.text = "[color=gold]已接受任务：%s[/color]" % str(data.get("title", ""))
	api.fetch_quests()
	if current_npc_id != "":
		api.fetch_npc_quests(current_npc_id)
		api.fetch_npc_active_quests(current_npc_id)'''
if old3 in t:
    t = t.replace(old3, new3, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_quest_accepted 刷新 offer/active")

# 2.6 任务 Tab 分三列：进行中 / 待提交 / 已结束
t = p.read_text(encoding="utf-8")
old4 = '''	var active: Array = []
	var done: Array = []
	for q in data:
		if not q is Dictionary:
			continue
		var st: String = str(q.get("state", ""))
		if st == "active":
			active.append(q)
		elif st in ("completed", "failed", "abandoned"):
			done.append(q)

	if not active.is_empty():
		quest_log.append_text("[b][color=orange]=== 进行中 ===[/color][/b]\\n\\n")
		for q in active:
			_render_quest_entry(q, true)

	if not done.is_empty():
		quest_log.append_text("\\n[b][color=gray]=== 已结束 ===[/color][/b]\\n\\n")
		for q in done:
			_render_quest_entry(q, false)'''

new4 = '''	var active: Array = []
	var done: Array = []
	for q in data:
		if not q is Dictionary:
			continue
		var st: String = str(q.get("state", ""))
		if st == "active":
			active.append(q)
		elif st in ("completed", "failed", "abandoned"):
			done.append(q)

	if not active.is_empty():
		quest_log.append_text("[b][color=orange]=== 进行中 ===[/color][/b]\\n\\n")
		for q in active:
			_render_quest_entry(q, true)

	if not done.is_empty():
		quest_log.append_text("\\n[b][color=gray]=== 已结束 ===[/color][/b]\\n\\n")
		for q in done:
			_render_quest_entry(q, false)'''
# 这段就是原文，只是确认没被其他地方改坏

# 2.7 任务条目里显示物品要求
t = p.read_text(encoding="utf-8")
old5 = '''		if loc_label != "":
			quest_log.append_text("    [color=cyan]目标地点：%s[/color]\\n" % loc_label)'''
new5 = '''		if loc_label != "":
			quest_log.append_text("    [color=cyan]目标地点：%s[/color]\\n" % loc_label)

		var rk: String = str(q.get("require_item_kind", ""))
		var rc: int = int(q.get("require_item_count", 0))
		if rk != "" and rc > 0:
			quest_log.append_text("    [color=yellow]需要：%s×%d[/color]\\n" % [rk, rc])'''
if old5 in t:
    t = t.replace(old5, new5, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 任务条目显示物品要求")

print()
print("===== 完成 =====")
print("pytest -v")
print("uvicorn server.main:app")
print("Godot 完全关闭重开")