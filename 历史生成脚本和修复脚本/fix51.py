# 事件列表分开：世界事件 / 我的行动
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 找 _render_event_list 函数
start = t.find("func _render_event_list() -> void:")
if start < 0:
    print("[fail] 找不到 _render_event_list")
    raise SystemExit(1)

end = t.find("\nfunc ", start + 1)
if end < 0:
    end = len(t)

new_body = '''func _render_event_list() -> void:
	event_log.clear()
	pending_events_by_id.clear()

	var awaiting: Array = []
	var world_events: Array = []
	var player_actions: Array = []

	for e in all_events_cache:
		if not e is Dictionary:
			continue
		if bool(e.get("awaiting_player", false)):
			pending_events_by_id[str(e.get("id", ""))] = e

		if not _event_matches_filter(e):
			continue

		if bool(e.get("awaiting_player", false)):
			awaiting.append(e)
			continue

		# 检查是否玩家的行动
		var tags: Array = e.get("tags", [])
		var is_action: bool = tags.has("action")
		var payload = e.get("payload", {})
		if payload is Dictionary and bool(payload.get("is_player_action", false)):
			is_action = true

		if is_action:
			player_actions.append(e)
		else:
			world_events.append(e)

	# 1. 待处理
	if not awaiting.is_empty():
		event_log.append_text("[b][color=orange]=== 等待你的决定 ===[/color][/b]\\n\\n")
		for e in awaiting:
			_render_event_entry(e, true)
		event_log.append_text("\\n")

	# 2. 世界事件
	if not world_events.is_empty():
		event_log.append_text("[b]—— 世界事件 ——[/b]\\n\\n")
		for e in world_events:
			_render_event_entry(e, false)
		event_log.append_text("\\n")

	# 3. 玩家行动（折叠到最下面）
	if not player_actions.is_empty():
		event_log.append_text("[b][color=gray]—— 我的行动 ——[/color][/b]\\n\\n")
		for e in player_actions:
			_render_event_entry(e, false)

	_refresh_event_action_panel()'''

t = t[:start] + new_body + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] _render_event_list 分开世界/行动")

# 顺便：在 _render_event_entry 里，玩家行动用更暗的颜色
t2 = p.read_text(encoding="utf-8")
old_render = '''func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))'''
new_render = '''func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))
	var is_action := false
	var p2 = e.get("payload", {})
	if p2 is Dictionary and bool(p2.get("is_player_action", false)):
		is_action = true'''
if old_render in t2:
    t2 = t2.replace(old_render, new_render, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] _render_event_entry 识别 action")

# 事件列表默认 30→50
t3 = p2.read_text(encoding="utf-8")
t3 = t3.replace("api.fetch_events(30)", "api.fetch_events(50)")
p2.write_text(t3, encoding="utf-8")
print("[fix] 事件拉取 30→50")

print()
print("Godot 完全关闭重开，按 F5")