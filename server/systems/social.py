"""NPC 自主对话：同地点两人有概率交谈，产生记忆与关系变化。"""

from __future__ import annotations

import random
import uuid
from typing import Optional

from sqlmodel import Session

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label
from server.models.schemas import NPC, World
from server.systems import relationship
from server.systems.memory import add_memory

MAX_SOCIAL_PER_DAY = 3
MIN_TICKS_BETWEEN = 4


def _group_by_location(npcs: list[NPC]) -> dict[str, list[NPC]]:
    by_loc: dict[str, list[NPC]] = {}
    for npc in npcs:
        by_loc.setdefault(npc.location_id, []).append(npc)
    return by_loc


def _relation_desc(a: NPC, b: NPC, session: Session) -> str:
    rel = relationship.get_relation_to(session, a.id, b.id)
    parts: list[str] = []
    if rel.trust > 0.3:
        parts.append("彼此信任")
    elif rel.trust < -0.2:
        parts.append("互相戒备")
    if rel.affection > 0.3:
        parts.append("关系亲近")
    elif rel.affection < -0.2:
        parts.append("相互冷淡")
    if not parts:
        return "点头之交"
    return "，".join(parts)


def _fallback_lines(a: NPC, b: NPC, topic: str) -> list[dict]:
    return [
        {"speaker": a.name, "text": "%s，最近可好？" % b.name},
        {"speaker": b.name, "text": "还成。你呢，%s？" % a.name},
    ]


async def maybe_social_dialogue(
    session: Session,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
) -> Optional[dict]:
    """每 tick 有机会触发一次 NPC 对话。返回对话记录或 None。"""
    if world.social_count_today >= MAX_SOCIAL_PER_DAY:
        return None
    if world.tick - world.last_social_tick < MIN_TICKS_BETWEEN:
        return None

    by_loc = _group_by_location(npcs)
    candidates: list[tuple[str, list[NPC]]] = [
        (loc, group) for loc, group in by_loc.items() if len(group) >= 2
    ]
    if not candidates:
        return None

    # 只有 25% 概率真的发生
    if rng.random() > 0.08:
        return None

    loc_id, group = rng.choice(candidates)
    a, b = rng.sample(group, 2)
    rel_desc = _relation_desc(a, b, session)
    loc_zh = location_label(loc_id)

    prompt = load_prompt("npc_chat.md").format(
        name_a=a.name,
        age_a=a.age,
        goals_a="，".join(a.goals) or "（无）",
        name_b=b.name,
        age_b=b.age,
        goals_b="，".join(b.goals) or "（无）",
        relation=rel_desc,
        location=loc_zh,
    )

    topic = "闲聊"
    lines: list[dict] = []
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            topic = str(raw.get("topic", "闲聊"))[:20]
            raw_lines = raw.get("lines", [])
            if isinstance(raw_lines, list):
                for item in raw_lines[:4]:
                    if not isinstance(item, dict):
                        continue
                    sp = str(item.get("speaker", "")).strip()
                    tx = str(item.get("text", "")).strip()[:80]
                    if sp and tx:
                        lines.append({"speaker": sp, "text": tx})
    except Exception:
        pass

    if not lines:
        lines = _fallback_lines(a, b, topic)

    summary = "%s 与 %s 在%s谈起%s。" % (a.name, b.name, loc_zh, topic)
    for npc in (a, b):
        add_memory(
            session,
            npc_id=npc.id,
            event_id="social_%s" % uuid.uuid4().hex[:6],
            summary=summary,
            emotion={"joy": 0.2} if topic != "争执" else {"anger": 0.3},
            timestamp=world.tick,
        )

    # 关系微调
    delta = rng.uniform(0.01, 0.04)
    relationship.adjust(session, a.id, b.id, trust=delta, affection=delta)
    relationship.adjust(session, b.id, a.id, trust=delta, affection=delta)

    world.last_social_tick = world.tick
    world.social_count_today += 1

    return {
        "a_id": a.id,
        "a_name": a.name,
        "b_id": b.id,
        "b_name": b.name,
        "location_id": loc_id,
        "location_label": loc_zh,
        "topic": topic,
        "lines": lines,
        "summary": summary,
        "tick": world.tick,
    }
