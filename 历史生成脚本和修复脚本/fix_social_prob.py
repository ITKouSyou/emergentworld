# 把 NPC 闲谈触发概率从 25% 降到 8%
from pathlib import Path

p = Path("server/systems/social.py")
t = p.read_text(encoding="utf-8")

old = "    if rng.random() > 0.25:\n        return None"
new = "    if rng.random() > 0.08:\n        return None"

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] social 触发概率 25% -> 8%")
else:
    print("[skip] 已改过或锚点未找到")