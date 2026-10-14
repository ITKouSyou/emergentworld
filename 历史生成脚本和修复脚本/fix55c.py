# 前端：NPC 详情显示日程
from pathlib import Path

# 1. 后端返回 schedule
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

old = '''def _npc_to_display(npc: NPC, npc_names: dict[str, str] | None = None) -> dict:
    names = npc_names or {}
    fam = npc.family'''
new = '''def _npc_to_display(npc: NPC, npc_names: dict[str, str] | None = None) -> dict:
    names = npc_names or {}
    fam = npc.family
    from server.systems import schedule as _sched_sys
    schedule_lines = _sched_sys.describe_schedule(npc)'''
if old in t:
    t = t.replace(old, new, 1)
    print("[fix] main.py _npc_to_display 加 schedule")

old2 = '''        "family": family_info,
    }'''
new2 = '''        "family": family_info,
        "schedule": schedule_lines,
    }'''
if old2 in t and '"schedule": schedule_lines' not in t:
    t = t.replace(old2, new2, 1)
    print("[fix] main.py 返回 schedule 字段")

p.write_text(t, encoding="utf-8")

# 2. 前端显示
p2 = Path("client/main.gd")
t2 = p2.read_text(encoding="utf-8")

old3 = '''	# 家庭
	var fam: Dictionary = data.get("family", {})'''
new3 = '''	# 日程
	var sched: Array = data.get("schedule", [])
	if not sched.is_empty():
		lines.append("")
		lines.append("[b]日常作息[/b]")
		for s in sched:
			lines.append("   %s" % str(s))

	# 家庭
	var fam: Dictionary = data.get("family", {})'''
if old3 in t2 and "日常作息" not in t2:
    t2 = t2.replace(old3, new3, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] main.gd 显示日程")
else:
    print("[skip] main.gd 已改过或锚点未匹配")

print()
print("重启后端：Ctrl+C → uvicorn server.main:app")
print("Godot 完全关闭重开，按 F5")