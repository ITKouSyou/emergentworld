# 诊断前端信号连接
from pathlib import Path

print("=== client/api.gd ===")
p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

print("do_action 存在：%s" % ("func do_action" in t))
print("action_done 信号：%s" % ("signal action_done" in t))

idx = t.find("func do_action")
if idx >= 0:
    end = t.find("\n\nfunc ", idx + 1)
    if end < 0:
        end = len(t)
    print("--- do_action 函数 ---")
    print(t[idx:end])

print()
print("=== client/main.gd ===")
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

print("action_done.connect：%s" % ("action_done.connect" in t))
print("_on_action_pressed：%s" % ("func _on_action_pressed" in t))
print("_on_action_done：%s" % ("func _on_action_done" in t))
print("_ensure_action_ui：%s" % ("func _ensure_action_ui" in t))

# 打印 _connect_signals 函数内容
i = t.find("func _connect_signals")
if i >= 0:
    e = t.find("\n\nfunc ", i + 1)
    print("--- _connect_signals ---")
    print(t[i:e if e > 0 else len(t)])