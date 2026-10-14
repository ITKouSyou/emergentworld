# 打印 pending event 的 choices 结构
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = '''	var e: Dictionary = pending_events_by_id[current_event_id]
	var title := Label.new()
	title.text = "你打算怎么做？ —— %s" % str(e.get("template_label", ""))
	event_action_panel.add_child(title)

	var choices: Array = e.get("choices", [])'''

new = '''	var e: Dictionary = pending_events_by_id[current_event_id]
	print("[ui] 事件 %s 的 choices = %s" % [
		current_event_id,
		JSON.stringify(e.get("choices", [])),
	])
	var title := Label.new()
	title.text = "你打算怎么做？ —— %s" % str(e.get("template_label", ""))
	event_action_panel.add_child(title)

	var choices: Array = e.get("choices", [])'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 打印 choices 结构")
else:
    print("[skip] 已改过")

print()
print("Godot 完全关闭重开，按 F5")
print("点击一个待处理事件，Godot Output 面板会打印：")
print("  [ui] 事件 evt_xxx 的 choices = [...]")
print("把这一行发我")