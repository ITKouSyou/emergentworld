# 把 fetch_goals 加到 _refresh_all
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _refresh_all() -> void:")
if start < 0:
    print("[fail] 找不到 _refresh_all")
    raise SystemExit(1)

end = t.find("\nfunc ", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]

if "api.fetch_goals()" in body:
    print("[skip] _refresh_all 已有 fetch_goals")
else:
    body_new = body.rstrip() + "\n\tapi.fetch_goals()\n"
    t = t[:start] + body_new + t[end:]
    p.write_text(t, encoding="utf-8")
    print("[fix] _refresh_all 加 fetch_goals")

# 打印
t2 = p.read_text(encoding="utf-8")
i = t2.find("func _refresh_all")
e = t2.find("\nfunc ", i + 1)
print()
print("--- 新 _refresh_all ---")
print(t2[i:e])

print()
print("Godot 完全关闭重开，按 F5")