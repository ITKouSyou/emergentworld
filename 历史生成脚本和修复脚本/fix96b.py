# Part 96B：前端任务接取 UI
from pathlib import Path

# ============================================================
# 1. api.gd
# ============================================================
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func fetch_npc_quests" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal npc_quests_received(data: Array)
signal quest_accepted(data: Dictionary)

func fetch_npc_quests(npc_id: String) -> void:
	_request("GET", "/npc/%s/quests" % npc_id, {}, "npc_quests_received")

func accept_npc_quest(npc_id: String, quest_def_id: String) -> void:
	_request("POST", "/npc/%s/quests/accept" % npc_id,
		{"quest_def_id": quest_def_id}, "quest_accepted")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加任务方法")

# ============================================================
# 2. main.gd
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var npc_quests_panel:" not in t:
    anchor = "var current_item_id: String = \"\"\n"
    if anchor in t:
        add = "var npc_quests_panel: VBoxContainer\nvar npc_quests_data: Array = []\n"
        t = t.replace(anchor, anchor + add, 1)
        print("[fix] 加任务 offer 变量")

# 2.2 信号
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    body = t[start:after]
    if "api.npc_quests_received.connect" not in body:
        lines = body.split("\n")
        insert_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            s = lines[i].strip()
            if s.startswith("api.") and ".connect(" in s:
                insert_idx = i
                break
        if insert_idx >= 0:
            indent = lines[insert_idx][:len(lines[insert_idx]) - len(lines[insert_idx].lstrip())]
            lines.insert(insert_idx + 1, indent + "api.npc_quests_received.connect(_on_npc_quests_received)")
            lines.insert(insert_idx + 2, indent + "api.quest_accepted.connect(_on_quest_accepted)")
            body = "\n".join(lines)
            t = t[:start] + body + t[after:]
            p.write_text(t, encoding="utf-8")
            print("[fix] 连接任务 offer 信号")

t = p.read_text(encoding="utf-8")

# 2.3 在 _on_npc_selected 里拉取可 offer 任务
old = '''func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	api.fetch_npc_items(current_npc_id)'''

new = '''func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	api.fetch_npc_items(current_npc_id)
	api.fetch_npc_quests(current_npc_id)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_npc_selected 拉任务")

# 2.4 在 _build_npc_tab 里加任务 offer 面板
t = p.read_text(encoding="utf-8")
old2 = '''	var dlg_title := Label.new()
	dlg_title.text = "对话"
	right.add_child(dlg_title)'''
new2 = '''	# NPC 委托任务面板
	npc_quests_panel = VBoxContainer.new()
	npc_quests_panel.add_theme_constant_override("separation", 4)
	npc_quests_panel.name = "QuestOfferPanel"
	right.add_child(npc_quests_panel)

	var dlg_title := Label.new()
	dlg_title.text = "对话"
	right.add_child(dlg_title)'''
if old2 in t:
    t = t.replace(old2, new2, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 加任务 offer 面板")

# 2.5 追加处理函数
t = p.read_text(encoding="utf-8")
if "_on_npc_quests_received" not in t:
    tail = '''

func _on_npc_quests_received(data: Array) -> void:
	npc_quests_data = data
	if npc_quests_panel == null:
		return
	# 清空旧子节点
	for child in npc_quests_panel.get_children():
		child.queue_free()
	if data.is_empty():
		return

	var title := Label.new()
	title.text = "[委托任务]" % ""
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
		info.text = "%s  → %s  (%d经验,%d钱)" % [title_s, loc_label, exp_r, money_r]
		info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(info)

		var btn := Button.new()
		btn.text = "接受"
		var qid: String = str(q.get("id", ""))
		var nid := current_npc_id
		btn.pressed.connect(func(): _on_accept_quest_pressed(nid, qid))
		row.add_child(btn)

		npc_quests_panel.add_child(row)


func _on_accept_quest_pressed(npc_id: String, quest_def_id: String) -> void:
	api.accept_npc_quest(npc_id, quest_def_id)


func _on_quest_accepted(data: Dictionary) -> void:
	status_label.text = "[color=gold]已接受任务：%s[/color]" % str(data.get("title", ""))
	# 清空 offer 面板 + 刷新任务 Tab
	for child in npc_quests_panel.get_children():
		child.queue_free()
	api.fetch_quests()
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 加任务 offer 处理函数")

print()
print("===== 完成 =====")
print("pytest -v")
print("uvicorn server.main:app")
print("Godot 完全关闭重开")