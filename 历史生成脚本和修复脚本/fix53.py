# 事件列表加时间戳 + 视觉区分
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. _render_event_entry 加时间戳
old = '''func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))
	var is_action := false
	var p2 = e.get("payload", {})
	if p2 is Dictionary and bool(p2.get("is_player_action", false)):
		is_action = true
	var state: String = str(e.get("state", ""))
	var state_zh: String = str(e.get("state_label", state))'''

new = '''func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))
	var is_action := false
	var p2 = e.get("payload", {})
	if p2 is Dictionary and bool(p2.get("is_player_action", false)):
		is_action = true
	var state: String = str(e.get("state", ""))
	var state_zh: String = str(e.get("state_label", state))
	var created_at: int = int(e.get("created_at", 0))
	var eid_short: String = eid
	if eid.length() > 10:
		eid_short = eid.substr(eid.length() - 6)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _render_event_entry 加时间戳字段")

# 2. 每个条目加 [第 N 回合 #id] 前缀
t = p.read_text(encoding="utf-8")

old_pending = '''	if pending:
		event_log.append_text("[color=orange]·[/color] [url=%s][b]%s[/b] %s（%s，%s）[/url]\\n" % [
			eid, tpl_label, names_str, loc_label, state_zh,
		])'''

new_pending = '''	if pending:
		event_log.append_text("[color=orange]·[/color] [color=gray][第 %d 回合][/color] [url=%s][b]%s[/b] %s（%s，%s）[/url]\\n" % [
			created_at, eid, tpl_label, names_str, loc_label, state_zh,
		])'''

if old_pending in t:
    t = t.replace(old_pending, new_pending, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] pending 条目加时间戳")

t = p.read_text(encoding="utf-8")
old_other = '''		event_log.append_text("[color=%s]·[/color] [b]%s[/b] %s（%s，%s）\\n" % [
			color, tpl_label, names_str, loc_label, state_zh,
		])'''

new_other = '''		event_log.append_text("[color=%s]·[/color] [color=gray][第 %d 回合 #%s][/color] [b]%s[/b] %s（%s，%s）\\n" % [
			color, created_at, eid_short, tpl_label, names_str, loc_label, state_zh,
		])'''

if old_other in t:
    t = t.replace(old_other, new_other, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 普通条目加时间戳 + id 后缀")

# 3. _on_event_triggered 加即时提示
t = p.read_text(encoding="utf-8")
old_trigger = '''func _on_event_triggered(data: Dictionary) -> void:
	if is_step_24_running:
		step_24_done += 1
		_set_loading("推进 24 回合 (%d/24)" % step_24_done)
	else:
		_set_loading("")

	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		var tpl_label: String = str(data.get("template_label", ""))
		if summary != "":
			event_log.append_text("\\n[color=orange]→[/color] [b]%s[/b] %s" % [tpl_label, summary])'''

new_trigger = '''func _on_event_triggered(data: Dictionary) -> void:
	if is_step_24_running:
		step_24_done += 1
		_set_loading("推进 24 回合 (%d/24)" % step_24_done)
	else:
		_set_loading("")

	var new_event_id: String = str(data.get("event", ""))
	var tpl_label: String = str(data.get("template_label", ""))
	var summary: String = str(data.get("event_summary", ""))
	var awaiting: bool = bool(data.get("awaiting_player", false))

	# 先给用户一个明确的"刚刚发生了什么"提示
	if new_event_id != "" and summary != "":
		var marker := "☆ 新事件"
		if awaiting:
			marker = "★ 等你决定"
		status_label.text = "[color=orange]%s：%s[/color]" % [marker, tpl_label]'''

if old_trigger in t:
    t = t.replace(old_trigger, new_trigger, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_event_triggered 加新事件提示")

# 4. /world/step 响应里也要带上 event / awaiting_player 字段
p2 = Path("server/main.py")
t2 = p2.read_text(encoding="utf-8")

# 检查已有的
if '"event": event.id if event else None' in t2:
    print("[ok] /world/step 已返回 event 字段")
else:
    print("[warn] /world/step 可能没返回 event 字段")

print()
print("Godot 完全关闭重开，按 F5")