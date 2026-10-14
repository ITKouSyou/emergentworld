"""NPC 对话：关系上下文 + 语义检索记忆。"""

from __future__ import annotations

from sqlmodel import Session

from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC, World
from server.systems import relationship
from server.systems.memory import retrieve_relevant, summarize_for_prompt


def _recent_events_for_npc(session, npc_id: str, limit: int = 5) -> list[str]:
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


async def npc_dialogue(
    session: Session,
    npc: NPC,
    player_input: str,
    world: World,
    memories: list[str] | None = None,
) -> dict:
    """生成 NPC 回复。

    返回 dict：{"reply": str, "memories_used": [str], "relation_desc": str}
    """
    # 1. 关系
    rel = relationship.get_relation_to(session, npc.id, "player")
    relation_desc = relationship.describe_relation_for_prompt(rel)

    # 2. 记忆：优先用传入的；否则按语义检索
    if memories is None:
        mem_objs = await retrieve_relevant(session, npc.id, player_input, top_k=5)
        mem_summaries = summarize_for_prompt(mem_objs, limit=5)
    else:
        mem_summaries = memories[:5]

    # 3. 关系牵引提示
    relationship_hint = _relationship_hint(rel)

    # 该 NPC 最近参与的事件
    recent_events = _recent_events_for_npc(session, npc.id, limit=5)
    recent_text = "\n".join(recent_events) or "（最近没有特别的事）"

    # 与这个 NPC 相关的进行中任务
    try:
        from server.systems import quest as quest_sys
        quest_lines = quest_sys.summarize_for_prompt(session, npc.id, limit=3)
    except Exception:
        quest_lines = []
    active_quests_text = "\n".join(quest_lines) or "（没有未了的事）"

    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        age=npc.age,
        traits=npc.traits,
        goals="，".join(npc.goals) or "（无明确目标）",
        location=npc.location_id,
        relation_desc=relation_desc,
        relationship_hint=relationship_hint,
        recent_events=recent_text,
        active_quests=active_quests_text,
        memories="\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )

    try:
        reply = await get_llm().text(prompt)
    except Exception as e:
        import traceback
        print("[dialogue] LLM 调用失败：%s" % e)
        traceback.print_exc()
        reply = "%s沉默了一会儿，没有回答。" % npc.name

    return {
        "reply": reply.strip(),
        "memories_used": mem_summaries,
        "relation_desc": relation_desc,
    }


def _relationship_hint(rel) -> str:
    """把关系数值转成"建议的语气"。"""
    hints: list[str] = []
    if rel.trust > 0.3:
        hints.append("你对玩家比较信任，可以透露一些心里话")
    elif rel.trust < -0.2:
        hints.append("你对玩家心存戒备，说话留三分")
    if rel.affection > 0.3:
        hints.append("你对玩家有好感，语气可以温和一些")
    elif rel.affection < -0.2:
        hints.append("你对玩家冷淡或反感，语气可以生硬一些")
    if rel.fear > 0.3:
        hints.append("你有点怕玩家，会表现得谨慎或退让")
    if rel.debt > 0.3:
        hints.append("你欠玩家很多人情，说话会客气或想找机会还")
    if not hints:
        hints.append("你和玩家不算熟，保持礼貌的距离")
    return "；".join(hints)
