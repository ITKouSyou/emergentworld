# 修 test_event_flow.py 里另一个 fake_fill
from pathlib import Path

p = Path("tests/test_event_flow.py")
t = p.read_text(encoding="utf-8")

old = "async def fake_fill(tpl, world, npcs, rng, player=None):"
new = "async def fake_fill(tpl, world, npcs, rng, player=None, event_roles=None):"

n = t.count(old)
if n > 0:
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print("[fix] fake_fill 加 event_roles (%d 处)" % n)
else:
    print("[skip] 未匹配")

print()
print("跑：pytest -v")