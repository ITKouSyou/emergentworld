from pathlib import Path

p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

# 打印 npc_dialogue 函数体
i = t.find("async def npc_dialogue")
e = t.find("\n\n\n", i + 1)
if e < 0:
    e = len(t)
print("=== npc_dialogue 函数体 ===")
print(t[i:e])