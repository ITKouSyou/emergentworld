# 看 api.gd 的 event_triggered 处理
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
i = t.find("func trigger_event")
print("--- trigger_event ---")
print(t[i:i+200])

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")
i = t.find("func _on_event_triggered")
e = t.find("\nfunc ", i + 1)
print()
print("--- _on_event_triggered ---")
print(t[i:e])