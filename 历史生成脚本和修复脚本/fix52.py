# 修 fix51 的变量名错误
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 检查是否已经做了第一个改动
if "player_actions" in t and "world_events" in t and "—— 世界事件 ——" in t:
    print("[ok] _render_event_list 已改过")
else:
    print("[!] _render_event_list 未改过，需要重跑")
    print("    请复制下面的代码块手动替换 _render_event_list")
    raise SystemExit(0)

# 补上 _render_event_entry 的识别
if "is_action" not in t.split("func _render_event_entry")[1][:500]:
    old = '''func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))'''
    new = '''func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))
	var is_action := false
	var p2 = e.get("payload", {})
	if p2 is Dictionary and bool(p2.get("is_player_action", false)):
		is_action = true'''
    if old in t:
        t = t.replace(old, new, 1)
        print("[fix] _render_event_entry 加 is_action")
    else:
        print("[skip] 锚点未匹配")
else:
    print("[ok] _render_event_entry 已识别 action")

# 事件数量
if "api.fetch_events(30)" in t:
    t = t.replace("api.fetch_events(30)", "api.fetch_events(50)")
    print("[fix] 事件拉取 30→50")

p.write_text(t, encoding="utf-8")

# 打印当前 _render_event_list 确认
t2 = p.read_text(encoding="utf-8")
start = t2.find("func _render_event_list() -> void:")
end = t2.find("\nfunc ", start + 1)
print()
print("--- 当前 _render_event_list ---")
print(t2[start:end])

print()
print("Godot 完全关闭重开，按 F5")