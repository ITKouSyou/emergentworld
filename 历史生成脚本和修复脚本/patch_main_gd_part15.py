"""在 main.gd 里加入事件选项处理。

改动：
    - 事件日志改为可点击
    - 新增 event_action_panel：选中事件时显示选项按钮
    - 新增 pending_events 缓存
    - 加 _on_event_resolve 处理玩家选择
"""
from pathlib import Path

p = Path("client/main.gd")
text = p.read_text(encoding="utf-8")

# 1. 在 _build_right_panel 里，把 event_log 从直接放在 tab 里，
#    改成外面包一层 VBox，下面加选项按钮面板
OLD_BUILD = '''	# 编年史
	var ev_scroll := ScrollContainer.new()
	ev_scroll.name = "编年史"
	tabs.add_child(ev_scroll)
	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ev_scroll.add_child(event_log)'''

NEW_BUILD = '''	# 编年史
	var ev_tab := VBoxContainer.new()
	ev_tab.name = "编年史"
	ev_tab.add_theme_constant_override("separation", 6)
	tabs.add_child(ev_tab)

	var ev_scroll := ScrollContainer.new()
	ev_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	ev_tab.add_child(ev_scroll)

	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.meta_underlined = false
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	event_log.meta_clicked.connect(_on_event_meta_clicked)
	ev_scroll.add_child(event_log)

	event_action_panel = VBoxContainer.new()
	event_action_panel.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_action_panel)'''

if OLD_BUILD not in text:
    print("未找到 _build_right_panel 的编年史部分，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_BUILD, NEW_BUILD)

# 2. 加成员变量
OLD_VARS = '''var map_poll_timer: Timer
'''
NEW_VARS = '''var map_poll_timer: Timer
var event_action_panel: VBoxContainer
var pending_events_by_id: Dictionary = {}
'''
text = text.replace(OLD_VARS, NEW_VARS, 1)

# 3. 处理事件列表时把 awaiting_player 高亮并记录 id
OLD_EVENT_LIST = '''func _on_event_list(data: Array) -> void:
	event_log.clear()
	for e in data:
		if not e is Dictionary:
			continue
		var state: String = str(e.get("state", ""))
		var state_zh: String = str(e.get("state_label", state))
		var color := "white"
		if state == "resolved":
			color = "lightgreen"
		elif state == "rejected":
			color = "gray"
		elif state == "active":
			color = "yellow"
		var tpl_label: String = str(e.get("template_label", e.get("template_id", "?")))
		var summary: String = str(e.get("summary", ""))
		var loc_label: String = str(e.get("location_label", ""))
		event_log.append_text("[color=%s]·[/color] [b]%s[/b]（%s，%s）\\n    %s\\n\\n" % [
			color, tpl_label, loc_label, state_zh, summary,
		])'''

NEW_EVENT_LIST = '''func _on_event_list(data: Array) -> void:
	event_log.clear()
	pending_events_by_id.clear()

	var awaiting: Array = []
	for e in data:
		if e is Dictionary and bool(e.get("awaiting_player", false)):
			awaiting.append(e)
			pending_events_by_id[str(e.get("id", ""))] = e

	# 顶部显示待处理事件
	if not awaiting.is_empty():
		event_log.append_text("[b][color=orange]=== 等待你的决定 ===[/color][/b]\\n\\n")
		for e in awaiting:
			_render_event_entry(e, true)
		event_log.append_text("\\n[b]历史事件[/b]\\n\\n")

	# 历史
	for e in data:
		if not e is Dictionary:
			continue
		if bool(e.get("awaiting_player", false)):
			continue
		_render_event_entry(e, false)

	_refresh_event_action_panel()


func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = str(e.get("id", ""))
	var state: String = str(e.get("state", ""))
	var state_zh: String = str(e.get("state_label", state))
	var color := "white"
	if state == "resolved":
		color = "lightgreen"
	elif state == "rejected":
		color = "gray"
	elif state == "expired":
		color = "darkgray"
	elif state == "awaiting_player":
		color = "orange"

	var tpl_label: String = str(e.get("template_label", e.get("template_id", "?")))
	var loc_label: String = str(e.get("location_label", ""))
	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			ns.append(str(n))
		names_str = "（" + "、".join(ns) + "）"

	var summary: String = str(e.get("summary", ""))
	var narrative: String = str(e.get("narrative", ""))
	var outcome: String = str(e.get("outcome", ""))
	var choice_label: String = str(e.get("choice_label", ""))

	if pending:
		# 可点击链接到 pending_events_by_id
		event_log.append_text("[color=%s]·[/color] [url=%s][b]%s[/b] %s[/url]（%s，%s）\\n" % [
			color, eid, tpl_label, names_str, loc_label, state_zh,
		])
		if narrative != "":
			event_log.append_text("    [i]%s[/i]\\n" % narrative)
		event_log.append_text("    [color=orange]点此做出选择[/color]\\n\\n")
	else:
		event_log.append_text("[color=%s]·[/color] [b]%s[/b] %s（%s，%s）\\n" % [
			color, tpl_label, names_str, loc_label, state_zh,
		])
		if summary != "":
			event_log.append_text("    %s\\n" % summary)
		if choice_label != "":
			event_log.append_text("    [i]你的选择：%s[/i]\\n" % choice_label)
		if outcome != "":
			event_log.append_text("    [color=lightgreen]%s[/color]\\n" % outcome)
		event_log.append_text("\\n")'''

if OLD_EVENT_LIST not in text:
    print("未找到 _on_event_list，可能已改过")
    raise SystemExit(1)
text = text.replace(OLD_EVENT_LIST, NEW_EVENT_LIST)

# 4. 追加新函数
NEW_FUNCS = '''

# ================================================================ 事件选项

func _on_event_meta_clicked(meta) -> void:
	var eid := str(meta)
	if eid == "" or not pending_events_by_id.has(eid):
		return
	# 选中这个事件：高亮并显示选项按钮
	current_event_id = eid
	_refresh_event_action_panel()


var current_event_id: String = ""


func _refresh_event_action_panel() -> void:
	if event_action_panel == null:
		return
	for child in event_action_panel.get_children():
		child.queue_free()

	if current_event_id == "" or not pending_events_by_id.has(current_event_id):
		var hint := Label.new()
		hint.text = "（点击上方橙色事件做出选择）"
		hint.add_theme_font_size_override("font_size", 12)
		event_action_panel.add_child(hint)
		return

	var e: Dictionary = pending_events_by_id[current_event_id]
	var title := Label.new()
	title.text = "你打算怎么做？ —— %s" % str(e.get("template_label", ""))
	event_action_panel.add_child(title)

	var choices: Array = e.get("choices", [])
	if choices.is_empty():
		var hint := Label.new()
		hint.text = "（此事件没有选项，稍后会自动结算）"
		event_action_panel.add_child(hint)
		return

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	event_action_panel.add_child(row)

	for c in choices:
		if not c is Dictionary:
			continue
		var btn := Button.new()
		btn.text = str(c.get("label", "?"))
		var cid := str(c.get("id", ""))
		var eid := current_event_id
		btn.pressed.connect(func(): _on_event_choice_pressed(eid, cid))
		row.add_child(btn)


func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	api.resolve_event(event_id, choice_id)


func _on_event_resolved(data: Dictionary) -> void:
	# 清空当前选中，刷新
	current_event_id = ""
	_refresh_all()
'''

text = text.rstrip() + "\n" + NEW_FUNCS

# 5. 加信号连接
OLD_SIGNALS = '''	api.map_received.connect(_on_map_received)
	api.request_failed.connect(_on_request_failed)'''
NEW_SIGNALS = '''	api.map_received.connect(_on_map_received)
	api.event_resolved.connect(_on_event_resolved)
	api.request_failed.connect(_on_request_failed)'''
if OLD_SIGNALS in text:
    text = text.replace(OLD_SIGNALS, NEW_SIGNALS)

p.write_text(text, encoding="utf-8", newline="\n")
print("[fix] client/main.gd 已更新")
print()
print("回到 Godot 自动重载")


if __name__ == "__main__":
    main()