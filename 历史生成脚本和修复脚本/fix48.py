# 修 %r 打印 + 打印请求 body
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = '''func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	print("[ui] 用户点击选项：event_id=%r choice_id=%r" % [event_id, choice_id])
	if event_id == "" or choice_id == "":
		print("[ui] 参数为空，忽略")
		return'''

new = '''func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	print("[ui] 用户点击选项：event_id=[%s] choice_id=[%s]" % [event_id, choice_id])
	if event_id == "" or choice_id == "":
		print("[ui] 参数为空，忽略")
		return'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] main.gd %r → %s")
else:
    print("[skip] main.gd 已改过")

# api.gd：打印 resolve body
p2 = Path("client/api.gd")
t2 = p2.read_text(encoding="utf-8")

old2 = '''func resolve_event(event_id: String, choice_id: String) -> void:
	_request("POST", "/event/%s/resolve" % event_id, {"choice_id": choice_id}, "event_resolved")'''

new2 = '''func resolve_event(event_id: String, choice_id: String) -> void:
	var body := {"choice_id": choice_id}
	print("[api] resolve body=%s" % JSON.stringify(body))
	_request("POST", "/event/%s/resolve" % event_id, body, "event_resolved")'''

if old2 in t2:
    t2 = t2.replace(old2, new2, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] api.gd resolve 打印 body")
else:
    print("[skip] api.gd 已改过")

# 顺便检查 _refresh_event_action_panel 里按钮构造
t2 = p2.read_text(encoding="utf-8")  # 重新读
t = p.read_text(encoding="utf-8")    # 重新读

i = t.find("func _refresh_event_action_panel")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    body = t[i:e]
    print()
    print("=== _refresh_event_action_panel 当前内容 ===")
    print(body)