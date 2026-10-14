# NPC 生成后检测套话 goals，强制替换
from pathlib import Path

p = Path("server/generators/npc.py")
t = p.read_text(encoding="utf-8")

old = '''    if not npc.goals:
        npc.goals = fallback.goals

    ok, _ = evaluate_npc(npc)'''

new = '''    if not npc.goals:
        npc.goals = fallback.goals

    # 检测套话 goals，强制替换成随机池里的
    COMMON_GOALS = {"安稳度日", "照顾好家人", "过好日子", "平平安安", "安安稳稳"}
    if npc.goals and all(g in COMMON_GOALS for g in npc.goals):
        import random as _r
        rng2 = _r.Random(uuid.uuid4().int)
        npc.goals = list(rng2.choice(FALLBACK_GOALS))
        print("[npc] %s 的 goals 是套话，替换为 %r" % (npc.name, npc.goals))

    ok, _ = evaluate_npc(npc)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] npc.py 检测套话 goals")
else:
    print("[skip] npc.py 已改过或锚点未匹配")

# 顺便从 FALLBACK_GOALS 里删掉那两条套话，避免新 NPC 抽到
t2 = p.read_text(encoding="utf-8")
old2 = '''    ["查明兄长的死因", "为他讨回公道"],
    ["安稳度日", "照顾好家人"],
    ["学会酿酒", "开一间自己的酒铺"],'''
new2 = '''    ["查明兄长的死因", "为他讨回公道"],
    ["学会酿酒", "开一间自己的酒铺"],
    ["找到失散多年的姐姐", "带她回来团圆"],'''
if old2 in t2:
    t2 = t2.replace(old2, new2, 1)
    p2 = p  # 同一文件
    p.write_text(t2, encoding="utf-8")
    print("[fix] FALLBACK_GOALS 删掉套话")

print()
print("重启后端才能生效")