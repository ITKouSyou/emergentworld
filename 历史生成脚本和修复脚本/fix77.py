# 补 faction_text 定义
from pathlib import Path

p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

# 找 impression_text 那段
old = '''    # 玩家给这个 NPC 留下的印象
    try:
        from server.systems import impression as impr_sys
        impression_text = impr_sys.describe_for_prompt(session, npc.id, limit=4)
    except Exception:
        impression_text = "（你对他还没有特别的印象）"

    prompt = load_prompt("dialogue.md").format('''

new = '''    # 玩家给这个 NPC 留下的印象
    try:
        from server.systems import impression as impr_sys
        impression_text = impr_sys.describe_for_prompt(session, npc.id, limit=4)
    except Exception:
        impression_text = "（你对他还没有特别的印象）"

    # 派系立场
    faction_text = "（你不属于任何派系）"
    try:
        from server.systems import faction as faction_sys
        if npc.faction and npc.faction != "neutral":
            rep = faction_sys.get_player_faction_rep(session, npc.faction)
            attitude = faction_sys.faction_attitude_hint(rep)
            faction_label = faction_sys.FACTIONS.get(npc.faction, {}).get("label", npc.faction)
            faction_text = "你属于【%s】，对玩家派系声望 %+d（%s）" % (
                faction_label, rep, attitude)
    except Exception:
        pass

    prompt = load_prompt("dialogue.md").format('''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 补 faction_text 定义")
else:
    print("[fail] dialogue.py 锚点未找到")

# 检查 dialogue.md 是否有 {faction_attitude}
p2 = Path("server/prompts/dialogue.md")
t2 = p2.read_text(encoding="utf-8")
if "{faction_attitude}" not in t2:
    print("[warn] dialogue.md 缺 {faction_attitude} 占位符")
    # 加占位符
    old2 = '''你与玩家的关系：
  {relation_desc}'''
    new2 = '''你与玩家的关系：
  {relation_desc}

你的派系立场：
  {faction_attitude}'''
    if old2 in t2:
        t2 = t2.replace(old2, new2, 1)
        p2.write_text(t2, encoding="utf-8")
        print("[fix] dialogue.md 加 faction_attitude 占位符")
else:
    print("[ok] dialogue.md 已有 faction_attitude")

print()
print("跑：pytest -v")