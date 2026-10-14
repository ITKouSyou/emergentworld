from pathlib import Path

p = Path("server/generators/npc.py")
t = p.read_text(encoding="utf-8")
lines = t.split("\n")
print("总行数：%d" % len(lines))
print()
for i, line in enumerate(lines):
    print("%4d | %s" % (i + 1, line))