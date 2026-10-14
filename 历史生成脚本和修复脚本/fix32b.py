# 让 NPC 对话知道"自己最近参与的事件"
from pathlib import Path

# 1. dialogue.py：查该 NPC 最近参与的事件
p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

if "_recent_events_for_npc" not in t:
    anchor = "async def npc_dialogue("
    addition = '''def _recent_events_for_npc(session, npc_id: str, limit: int = 5) -> list[str]:
    """查该 NPC 最近参与的事件，返回摘要文本列表。"""
    from sqlmodel import select
    from server.models.db import EventRow, loads as _loads

    rows = session.exec(
        select(EventRow)
        .order_by(EventRow.created_at.desc())
        .limit(40)
    ).all()

    lines: list[str] = []
    for r in rows:
        participants = _loads(r.participants_json) or []
        if npc_id not in participants:
            continue
        payload = _loads(r.payload_json) or {}
        summary = payload.get("summary", "")
        outcome = payload.get("outcome", "")
        state = r.state

        # 判断是否"未解决"
        marker = ""
        if state == "awaiting_player":
            marker = "（进行中，还没有结果）"
        elif state == "resolved" and not outcome:
            marker = "（刚发生）"
        elif outcome and any(kw in outcome for kw in ["还在找", "没找到", "未", "悬而未决", "继续"]):
            marker = "（事情还没了结）"

        line = "- %s%s" % (summary, marker)
        if outcome:
            line += "  结果：" + outcome[:40]
        lines.append(line)
        if len(lines) >= limit:
            break

    return lines


async def npc_dialogue('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] dialogue.py 加 _recent_events_for_npc")
    else:
        print("[fail] dialogue.py 锚点未找到")

# 2. 在主函数里调用
old = '''    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        age=npc.age,
        traits=npc.traits,
        goals="，".join(npc.goals) or "（无明确目标）",
        location=npc.location_id,
        relation_desc=relation_desc,
        relationship_hint=relationship_hint,
        memories="\\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )'''

new = '''    # 该 NPC 最近参与的事件
    recent_events = _recent_events_for_npc(session, npc.id, limit=5)
    recent_text = "\\n".join(recent_events) or "（最近没有特别的事）"

    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        age=npc.age,
        traits=npc.traits,
        goals="，".join(npc.goals) or "（无明确目标）",
        location=npc.location_id,
        relation_desc=relation_desc,
        relationship_hint=relationship_hint,
        recent_events=recent_text,
        memories="\\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] npc_dialogue 调用加 recent_events")
else:
    print("[skip] 调用已改过或未匹配")

# 3. dialogue.md 加占位符
p2 = Path("server/prompts/dialogue.md")
t2 = p2.read_text(encoding="utf-8")

if "{recent_events}" not in t2:
    old_md = '''你记得的事：
{memories}'''
    new_md = '''你最近经历的事：
{recent_events}

你记得的事：
{memories}'''
    if old_md in t2:
        t2 = t2.replace(old_md, new_md, 1)
        p2.write_text(t2, encoding="utf-8")
        print("[fix] dialogue.md 加 recent_events 占位符")
    else:
        print("[fail] dialogue.md 锚点未找到")
else:
    print("[skip] dialogue.md 已有 recent_events")

print()
print("B 完成。重启 uvicorn + Godot")