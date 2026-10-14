from pathlib import Path

print("=== npc.py 检查 ===")
p = Path("server/generators/npc.py")
t = p.read_text(encoding="utf-8")

print("'COMMON_GOALS' 存在：%s" % ("COMMON_GOALS" in t))
print("'套话' 字样存在：%s" % ("套话" in t))
print()
print("--- FALLBACK_GOALS ---")
i = t.find("FALLBACK_GOALS")
if i >= 0:
    e = t.find("]", i)
    print(t[i:e+1])
print()
print("--- generate_npc 后半段 ---")
i = t.find("if not npc.goals:")
if i >= 0:
    e = t.find("\n\n", i)
    if e < 0:
        e = i + 500
    print(t[i:e])