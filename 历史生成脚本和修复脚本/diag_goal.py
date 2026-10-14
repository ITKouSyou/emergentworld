# 诊断目标系统
from pathlib import Path

print("=== client/main.gd ===")
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

print("goals_received.connect：%s" % ("api.goals_received.connect" in t))
print("_on_goals_received：%s" % ("func _on_goals_received" in t))
print("_build_goal_section：%s" % ("func _build_goal_section" in t))
print("api.fetch_goals() 调用：%s" % ("api.fetch_goals()" in t))
print()

# 打印 _refresh_all
i = t.find("func _refresh_all")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    print("--- _refresh_all ---")
    print(t[i:e])
print()

# 打印 _connect_signals
i = t.find("func _connect_signals")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    print("--- _connect_signals 前 300 字符 ---")
    print(t[i:i+300])

print()
print("=== client/api.gd ===")
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
print("fetch_goals：%s" % ("func fetch_goals" in t))
print("goals_received 信号：%s" % ("signal goals_received" in t))
i = t.find("func fetch_goals")
if i >= 0:
    e = t.find("\nfunc ", i + 1)
    print("--- fetch_goals ---")
    print(t[i:e])