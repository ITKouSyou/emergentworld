# 前端：档案显示"对你的印象"
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 在 _on_npc_detail 里，日程后面加印象
old = '''	# 日程
	var sched: Array = data.get("schedule", [])
	if not sched.is_empty():
		lines.append("")
		lines.append("[b]日常作息[/b]")
		for s in sched:
			lines.append("   %s" % str(s))

	# 家庭'''

new = '''	# 对你的印象（放在目标之后，家庭之前）
	var impr: Array = data.get("impressions", [])
	if not impr.is_empty():
		lines.append("")
		lines.append("[b][color=cyan]对你的印象[/color][/b]")
		for s in impr:
			lines.append("   · %s" % str(s))

	# 日程
	var sched: Array = data.get("schedule", [])
	if not sched.is_empty():
		lines.append("")
		lines.append("[b]日常作息[/b]")
		for s in sched:
			lines.append("   %s" % str(s))

	# 家庭'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _on_npc_detail 加印象显示")
else:
    print("[fail] main.gd 锚点未找到")

print()
print("Godot 完全关闭重开，按 F5")