# 把 loading 提示里的 tick 换中文
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

repls = [
    ('"推进 24 tick (0/24)"', '"推进 24 回合 (0/24)"'),
    ('"推进 24 tick (%d/24)" % step_24_done', '"推进 24 回合 (%d/24)" % step_24_done'),
    ('"推进 24 tick ("', '"推进 24 回合 ("'),
]

count = 0
for old, new in repls:
    if old in t:
        n = t.count(old)
        t = t.replace(old, new)
        print("[fix] %r (%d 处)" % (old, n))
        count += n

p.write_text(t, encoding="utf-8")
print()
print("共修 %d 处" % count)
print("Godot 完全关闭重开，按 F5")