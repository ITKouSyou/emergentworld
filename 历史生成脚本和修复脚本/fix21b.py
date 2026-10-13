# 前端：事件筛选 + 上色 + 奖励分组 + 史册中文
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# ============================================================
# 1. 加成员变量
# ============================================================
if "var event_filter_tag:" not in t:
    anchor = "var current_event_id: String = \"\"\n"
    addition = (
        "var current_event_id: String = \"\"\n"
        "var event_filter_tag: String = \"\"\n"
        "var all_events_cache: Array = []\n"
        "var event_filter_row: HBoxContainer\n"
        "var pending_only: bool = false\n"
    )
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] 加事件筛选变量")
    else:
        # 备用
        anchor2 = "var pending_events_by_id: Dictionary = {}\n"
        if anchor2 in t:
            t = t.replace(anchor2, anchor2 + addition, 1)
            print("[fix] 加事件筛选变量（备用）")

# ============================================================
# 2. 在 _build_event_tab 里加筛选按钮行
# ============================================================
old_tab = '''	event_log.meta_clicked.connect(_on_event_meta_clicked)
	ev_scroll.add_child(event_log)

	event_action_panel = VBoxContainer.new()
	event_action_panel.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_action_panel)'''

new_tab = '''	event_log.meta_clicked.connect(_on_event_meta_clicked)
	ev_scroll.add_child(event_log)

	event_filter_row = HBoxContainer.new()
	event_filter_row.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_filter_row)

	var filters := [
		["", "全部"],
		["__pending__", "待处理"],
		["conflict", "冲突"],
		["social", "社交"],
		["daily", "日常"],
		["mystery", "悬疑"],
		["action", "我的行动"],
	]
	for pair in filters:
		var b := Button.new()
		b.text = str(pair[1])
		var tag: String = str(pair[0])
		b.pressed.connect(func(): _set_event_filter(tag))
		event_filter_row.add_child(b)

	event_action_panel = VBoxContainer.new()
	event_action_panel.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_action_panel)'''

if old_tab in t:
    t = t.replace(old_tab, new_tab, 1)
    print("[fix] 加事件筛选按钮行")
else:
    print("[skip] _build_event_tab 已改过或未匹配")

# ============================================================
# 3. 重写 _on_event_list（加筛选 + 缓存）
# ============================================================
old_list = '''func _on_event_list(data: Array) -> void:
	event_log.clear()
	pending_events_by_id.clear()

	var awaiting: Array = []
	for e in data:
		if e is Dictionary and bool(e.get("awaiting_player", false)):
			awaiting.append(e)
			pending_events_by_id[str(e.get("id", ""))] = e

	if not awaiting.is_empty():
		event_log.append_text("[b][color=orange]=== 等待你的决定 ===[/color][/b]\\n\\n")
		for e in awaiting:
			_render_event_entry(e, true)
		event_log.append_text("\\n[b]其它事件[/b]\\n\\n")

	for e in data:
		if not e is Dictionary:
			continue
		if bool(e.get("awaiting_player", false)):
			continue
		_render_event_entry(e, false)

	_refresh_event_action_panel()'''

new_list = '''func _on_event_list(data: Array) -> void:
	all_events_cache = data
	_render_event_list()


func _set_event_filter(tag: String) -> void:
	event_filter_tag = tag
	_render_event_list()


func _event_matches_filter(e: Dictionary) -> bool:
	if event_filter_tag == "":
		return true
	if event_filter_tag == "__pending__":
		return bool(e.get("awaiting_player", false))
	var tags: Array = e.get("tags", [])
	return tags.has(event_filter_tag)


func _render_event_list() -> void:
	event_log.clear()
	pending_events_by_id.clear()

	var awaiting: Array = []
	var others: Array = []
	for e in all_events_cache:
		if not e is Dictionary:
			continue
		if bool(e.get("awaiting_player", false)):
			pending_events_by_id[str(e.get("id", ""))] = e
		if not _event_matches_filter(e):
			continue
		if bool(e.get("awaiting_player", false)):
			awaiting.append(e)
		else:
			others.append(e)

	if not awaiting.is_empty():
		event_log.append_text("[b][color=orange]=== 等待你的决定 ===[/color][/b]\\n\\n")
		for e in awaiting:
			_render_event_entry(e, true)
		if not others.is_empty():
			event_log.append_text("\\n[b]其它事件[/b]\\n\\n")

	for e in others:
		_render_event_entry(e, false)

	_refresh_event_action_panel()'''

if old_list in t:
    t = t.replace(old_list, new_list, 1)
    print("[fix] _on_event_list 加筛选")
else:
    print("[fail] _on_event_list 未匹配")

# ============================================================
# 4. _render_event_entry 里对参与者名字上色
# ============================================================
old_names = '''	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			ns.append(_safe_str(n))
		names_str = "（" + "、".join(ns) + "）"'''

new_names = '''	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			var nname := _safe_str(n)
			ns.append(_color_name(nname))
		names_str = "（" + "、".join(ns) + "）"'''

if old_names in t:
    t = t.replace(old_names, new_names, 1)
    print("[fix] 事件参与者名上色")
else:
    print("[skip] 参与者名已改过")

# ============================================================
# 5. _on_reward_list 按 kind 分组
# ============================================================
old_reward = '''func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	for r in data:
		if not r is Dictionary:
			continue
		var kind_label: String = str(r.get("kind_label", r.get("kind", "?")))
		reward_log.append_text("[b]%s[/b]  %.2f  %s\\n" % [
			kind_label, float(r.get("value", 0)), str(r.get("description", "")),
		])'''

new_reward = '''func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	if data.is_empty():
		reward_log.text = "[i]还没有奖励[/i]"
		return

	# 按 kind 分组
	var groups: Dictionary = {}
	var kind_order: Array = []
	for r in data:
		if not r is Dictionary:
			continue
		var k: String = str(r.get("kind", "item"))
		if not groups.has(k):
			groups[k] = []
			kind_order.append(k)
		groups[k].append(r)

	var color_map := {
		"item": "#d8a850",
		"relationship": "#6ac070",
		"info": "#5aa8d8",
		"reputation": "#c870c8",
		"skill": "#e0a060",
		"story": "#a080d0",
	}

	for k in kind_order:
		var color: String = str(color_map.get(k, "#cccccc"))
		var label: String = str({
			"item": "物品",
			"relationship": "关系",
			"info": "情报",
			"reputation": "声望",
			"skill": "技能",
			"story": "剧情",
		}.get(k, k))
		reward_log.append_text("[b][color=%s]◆ %s[/color][/b]\\n" % [color, label])
		for r in groups[k]:
			var v: float = float(r.get("value", 0))
			var desc: String = _safe_str(r.get("description", ""))
			reward_log.append_text("    %.2f  %s\\n" % [v, _highlight_names(desc)])
		reward_log.append_text("\\n")'''

if old_reward in t:
    t = t.replace(old_reward, new_reward, 1)
    print("[fix] 奖励分组")
else:
    print("[skip] _on_reward_list 未匹配")

# ============================================================
# 6. _on_chronicle_list：英文ID → 中文
# ============================================================
old_chr = '''func _on_chronicle_list(data: Array) -> void:
	chronicle_log.clear()
	if data.is_empty():
		chronicle_log.text = "[i]还没有史册。点击下方按钮生成一份。[/i]"
		return
	for c in data:
		if not c is Dictionary:
			continue
		chronicle_log.append_text("[b][color=gold]%s[/color][/b]\\n" % str(c.get("title", "?")))
		chronicle_log.append_text("[color=lightgray]%s[/color]\\n\\n" % str(c.get("body", "")))
		chronicle_log.append_text("[i]——  记录于第 %d tick[/i]\\n\\n" % int(c.get("created_at", 0)))'''

new_chr = '''func _on_chronicle_list(data: Array) -> void:
	chronicle_log.clear()
	if data.is_empty():
		chronicle_log.text = "[i]还没有史册。点击下方按钮生成一份。[/i]"
		return
	for c in data:
		if not c is Dictionary:
			continue
		chronicle_log.append_text("[b][color=gold]%s[/color][/b]\\n" % str(c.get("title", "?")))
		var body: String = str(c.get("body", ""))
		body = _replace_template_ids(body)
		body = _highlight_names(body)
		chronicle_log.append_text("[color=lightgray]%s[/color]\\n\\n" % body)
		chronicle_log.append_text("[i]——  记录于第 %d 回合[/i]\\n\\n" % int(c.get("created_at", 0)))


func _replace_template_ids(text: String) -> String:
	# 把 [xxx_id] 替换成 [中文名]
	var re := RegEx.new()
	re.compile("\\\\[([a-z_]+)\\\\]")
	var result := text
	for m in re.search_all(text):
		var tid: String = m.get_string(1)
		var zh: String = tid
		if i18n_templates.has(tid):
			zh = str(i18n_templates[tid])
		result = result.replace("[%s]" % tid, "[%s]" % zh)
	return result


func _highlight_names(text: String) -> String:
	# 对已知 NPC 名字上色（男蓝女粉），地点青色
	var result := text
	for npc_id in npc_order:
		var npc: Dictionary = npc_data[npc_id]
		var npc_name: String = str(npc.get("name", ""))
		if npc_name == "":
			continue
		var gender: String = str(npc.get("gender", "unknown"))
		var color := "#7ac4e8"
		if gender == "female":
			color = "#f0a0c0"
		elif gender == "male":
			color = "#88b8f0"
		result = result.replace(npc_name, "[color=%s]%s[/color]" % [color, npc_name])
	return result


func _color_name(npc_name: String) -> String:
	for npc_id in npc_order:
		var npc: Dictionary = npc_data[npc_id]
		if str(npc.get("name", "")) == npc_name:
			var gender: String = str(npc.get("gender", "unknown"))
			var color := "#7ac4e8"
			if gender == "female":
				color = "#f0a0c0"
			elif gender == "male":
				color = "#88b8f0"
			return "[color=%s]%s[/color]" % [color, npc_name]
	return npc_name'''

if old_chr in t:
    t = t.replace(old_chr, new_chr, 1)
    print("[fix] 史册替换英文 + 上色")
else:
    print("[skip] _on_chronicle_list 未匹配")

# ============================================================
# 7. 事件条目里也调用 _highlight_names
# ============================================================
t = t.replace(
    'var summary: String = _safe_str(e.get("summary", ""))\n\tvar narrative: String = _safe_str(e.get("narrative", ""))',
    'var summary: String = _highlight_names(_safe_str(e.get("summary", "")))\n\tvar narrative: String = _highlight_names(_safe_str(e.get("narrative", "")))',
)

p.write_text(t, encoding="utf-8")
print()
print("=== 完成 ===")
print("重启 uvicorn，Godot 完全关闭重开")