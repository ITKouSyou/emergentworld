# Part 33C：前端加任务 Tab
from pathlib import Path

# 1. api.gd
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

if "func fetch_quests" not in t:
    anchor = "func fetch_world_state() -> void:"
    addition = '''signal quest_list_received(data: Array)
signal quest_abandoned(data: Dictionary)

func fetch_quests() -> void:
	_request("GET", "/quest", {}, "quest_list_received")

func abandon_quest(quest_id: String) -> void:
	_request("POST", "/quest/abandon", {"quest_id": quest_id}, "quest_abandoned")

'''
    if anchor in t:
        t = t.replace(anchor, addition + anchor, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] api.gd 加 quest 方法")

# 2. main.gd
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 2.1 变量
if "var quest_log:" not in t:
    anchor = "var market_log: RichTextLabel\n"
    if anchor in t:
        t = t.replace(anchor, anchor + "var quest_log: RichTextLabel\n", 1)
        print("[fix] 加 quest_log 变量")

# 2.2 信号
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    if after < 0:
        after = len(t)
    body = t[start:after]
    if "api.quest_list_received.connect" not in body:
        anchor = "api.request_failed.connect(_on_request_failed)"
        if anchor not in body:
            anchor = "\tapi.request_failed.connect(_on_request_failed)"
        if anchor in body:
            indent = anchor[:len(anchor) - len(anchor.lstrip())]
            new_lines = (
                indent + "api.quest_list_received.connect(_on_quest_list_received)\n"
                + indent + "api.quest_abandoned.connect(_on_quest_abandoned)\n"
            )
            body = body.replace(anchor, new_lines + anchor, 1)
            t = t[:start] + body + t[after:]
            print("[fix] 连接 quest 信号")

p.write_text(t, encoding="utf-8")

# 2.3 加任务 Tab 到右栏
t = p.read_text(encoding="utf-8")

old_right = '''	_build_event_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_market_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''

new_right = '''	_build_event_tab(right_tabs)
	_build_quest_tab(right_tabs)
	_build_chronicle_tab(right_tabs)
	_build_market_tab(right_tabs)
	_build_reward_tab(right_tabs)
	_build_item_tab(right_tabs)'''

if old_right in t:
    t = t.replace(old_right, new_right, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _build_ui 加任务 Tab")
else:
    print("[skip] _build_ui 已改过")

# 2.4 追加任务 Tab 函数
t = p.read_text(encoding="utf-8")

if "func _build_quest_tab" not in t:
    tail = '''

func _build_quest_tab(parent: TabContainer) -> void:
	var tab := VBoxContainer.new()
	tab.name = "任务"
	tab.add_theme_constant_override("separation", 6)
	parent.add_child(tab)

	var ctrl := HBoxContainer.new()
	ctrl.add_theme_constant_override("separation", 6)
	tab.add_child(ctrl)

	var refresh := Button.new()
	refresh.text = "刷新任务"
	refresh.pressed.connect(func(): api.fetch_quests())
	ctrl.add_child(refresh)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	tab.add_child(scroll)

	quest_log = RichTextLabel.new()
	quest_log.bbcode_enabled = true
	quest_log.fit_content = true
	quest_log.meta_clicked.connect(_on_quest_meta_clicked)
	quest_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(quest_log)


func _on_quest_list_received(data: Array) -> void:
	if quest_log == null:
		return
	quest_log.clear()

	if data.is_empty():
		quest_log.text = "[i]你还没有接到任何任务。触发一些事件后，可能会有人找上你。[/i]"
		return

	var active: Array = []
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
			_render_quest_entry(q, false)


func _render_quest_entry(q: Dictionary, active: bool) -> void:
	var qid: String = str(q.get("id", ""))
	var title: String = str(q.get("title", "?"))
	var desc: String = str(q.get("description", ""))
	var giver: String = str(q.get("giver_name", ""))
	var loc_label: String = str(q.get("target_location_label", ""))
	var state: String = str(q.get("state", ""))
	var exp_r: int = int(q.get("reward_exp", 0))
	var money_r: int = int(q.get("reward_money", 0))

	if active:
		quest_log.append_text("[b][color=gold]◆ %s[/color][/b]\\n" % title)
		if desc != "":
			quest_log.append_text("    %s\\n" % desc)
		if giver != "":
			quest_log.append_text("    [color=lightgray]委托人：%s[/color]\\n" % giver)
		if loc_label != "":
			quest_log.append_text("    [color=cyan]目标地点：%s[/color]\\n" % loc_label)

		var rewards: Array[String] = []
		if exp_r > 0:
			rewards.append("经验 +%d" % exp_r)
		if money_r > 0:
			rewards.append("铜钱 +%d" % money_r)
		if not rewards.is_empty():
			quest_log.append_text("    [color=yellow]奖励：%s[/color]\\n" % "、".join(rewards))

		quest_log.append_text("    [url=abandon:%s][放弃任务][/url]\\n\\n" % qid)
	else:
		var color := "dimgray"
		var state_label := "已结束"
		if state == "completed":
			color = "lightgreen"
			state_label = "✓ 已完成"
		elif state == "abandoned":
			color = "darkgray"
			state_label = "已放弃"
		quest_log.append_text("[color=%s]· %s（%s）[/color]\\n\\n" % [color, title, state_label])


func _on_quest_meta_clicked(meta) -> void:
	var s := str(meta)
	if s.begins_with("abandon:"):
		api.abandon_quest(s.substr(8))


func _on_quest_abandoned(data: Dictionary) -> void:
	api.fetch_quests()


func _on_travel_done(data: Dictionary) -> void:
	if travel_btn != null and is_instance_valid(travel_btn):
		travel_btn.disabled = false

	var from_label: String = str(data.get("from_label", ""))
	var to_label: String = str(data.get("to_label", ""))
	if travel_result_label != null:
		travel_result_label.text = "[color=cyan]你从【%s】来到【%s】[/color]" % [from_label, to_label]

	# 任务完成提示
	var completed: Array = data.get("completed_quests", [])
	if not completed.is_empty():
		var lines: Array[String] = ["[color=gold]★ 完成任务！[/color]"]
		for q in completed:
			if q is Dictionary:
				lines.append("  · %s  +%d 经验  +%d 铜钱" % [
					str(q.get("title", "?")),
					int(q.get("reward_exp", 0)),
					int(q.get("reward_money", 0)),
				])
		if travel_result_label != null:
			travel_result_label.text += "\\n" + "\\n".join(lines)

	var p_data = data.get("player")
	if p_data is Dictionary:
		player_data = p_data
		_render_player_panel()

	api.fetch_world_state()
	api.fetch_map()
	api.fetch_events(30)
	api.fetch_quests()
'''
    # 判断 _on_travel_done 是否已存在，若存在则跳过重定义
    if "func _on_travel_done" in t:
        # 只追加前面部分
        tail = tail.split("func _on_travel_done")[0]
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 加任务 Tab + 处理函数")

# 2.5 _refresh_all 拉任务
t = p.read_text(encoding="utf-8")
i = t.find("func _refresh_all() -> void:")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    body = t[i:e]
    if "api.fetch_quests" not in body:
        body_new = body.rstrip() + "\n\tapi.fetch_quests()\n"
        t = t[:i] + body_new + t[e:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _refresh_all 拉任务")

print()
print("C 完成。重启 uvicorn + Godot 完全关闭重开")