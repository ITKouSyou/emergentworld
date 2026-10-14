# 诊断日程 + goals
from pathlib import Path
import sqlite3
import json

print("=== 1. 数据库里的 NPC ===")
conn = sqlite3.connect("data/world.db")
rows = conn.execute("SELECT id, name, age, goals_json, schedule_json FROM npc WHERE alive=1").fetchall()
for r in rows[:15]:
    nid, name, age, goals_j, sched_j = r
    goals = json.loads(goals_j or "[]")
    sched = json.loads(sched_j or "{}")
    print("%s | %s  %d岁" % (nid[:12], name, age))
    print("  goals: %r" % goals)
    print("  schedule: %r" % sched)
conn.close()

print()
print("=== 2. main.py /npc 是否返回 schedule ===")
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")
has_sched_field = '"schedule": schedule_lines' in t
has_describe = "describe_schedule" in t
print("describe_schedule 调用：%s" % has_describe)
print("schedule 字段返回：%s" % has_sched_field)

# 打印 _npc_to_display
i = t.find("def _npc_to_display")
if i >= 0:
    e = t.find("\n\ndef ", i + 1)
    if e < 0:
        e = t.find("\n@app", i + 1)
    print()
    print("--- _npc_to_display ---")
    print(t[i:e])

print()
print("=== 3. main.gd 是否有日常作息 ===")
p2 = Path("client/main.gd")
t2 = p2.read_text(encoding="utf-8")
print("'日常作息' 出现：%s" % ("日常作息" in t2))
print("'schedule' 出现：%s" % ('data.get("schedule"' in t2))

print()
print("=== 4. goals 多样性 ===")
conn = sqlite3.connect("data/world.db")
rows = conn.execute("SELECT goals_json FROM npc WHERE alive=1").fetchall()
unique_goals = set()
for r in rows:
    goals = tuple(json.loads(r[0] or "[]"))
    unique_goals.add(goals)
print("总 NPC：%d，唯一 goals 组合：%d" % (len(rows), len(unique_goals)))
conn.close()