from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 检查函数是否存在
has1 = "func _on_npc_quests_received" in t
has2 = "func _on_quest_accepted" in t
has3 = "func _on_accept_quest_pressed" in t
print("_on_npc_quests_received: %s" % has1)
print("_on_quest_accepted: %s" % has2)
print("_on_accept_quest_pressed: %s" % has3)

if has1 and has2 and has3:
    print("[skip] 三个函数都已存在")
else:
    tail = "\n"
    if not has1:
        tail += '''

func _on_npc_quests_received(data: Array) -> void:
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

		npc_quests_panel.add_child(row)
'''

    if not has3:
        tail += '''

func _on_accept_quest_pressed(npc_id: String, quest_def_id: String) -> void:
	api.accept_npc_quest(npc_id, quest_def_id)
'''

    if not has2:
        tail += '''

func _on_quest_accepted(data: Dictionary) -> void:
	status_label.text = "[color=gold]已接受任务：%s[/color]" % str(data.get("title", ""))
	if npc_quests_panel != null:
		for child in npc_quests_panel.get_children():
			child.queue_free()
	api.fetch_quests()
'''

    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 追加缺失的函数")

# 确认信号连接在 _connect_signals 里
if "api.npc_quests_received.connect" not in t:
    print("[warn] _connect_signals 里没有 npc_quests_received 连接")
else:
    print("[ok] 信号已连接")

if "api.quest_accepted.connect" not in t:
    print("[warn] _connect_signals 里没有 quest_accepted 连接")

# 确认 _on_npc_selected 会拉任务
if "api.fetch_npc_quests(current_npc_id)" not in t:
    print("[warn] _on_npc_selected 没调用 fetch_npc_quests")
else:
    print("[ok] _on_npc_selected 会拉任务")

print()
print("Godot 完全关闭重开，按 F5")