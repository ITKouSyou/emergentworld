"""关系系统：NPC 之间的信任、好感、恐惧、债务。"""

from __future__ import annotations

import random

from sqlmodel import Session, select

from server.models.db import RelationshipRow
from server.models.schemas import NPC, Relationship


def _rel_id(a: str, b: str) -> str:
    x, y = sorted([a, b])
    return "rel_%s_%s" % (x, y)


def get_or_create(session: Session, from_npc: str, to_npc: str) -> Relationship:
    rid = _rel_id(from_npc, to_npc)
    row = session.get(RelationshipRow, rid)
    if row is None:
        row = RelationshipRow(id=rid, from_npc=from_npc, to_npc=to_npc)
        session.add(row)
        session.commit()
    return Relationship(
        id=row.id, from_npc=row.from_npc, to_npc=row.to_npc,
        trust=row.trust, affection=row.affection,
        fear=row.fear, debt=row.debt,
        kind=getattr(row, "kind", "") or "",
    )


def adjust(
    session: Session,
    from_npc: str,
    to_npc: str,
    trust: float = 0.0,
    affection: float = 0.0,
    fear: float = 0.0,
    debt: float = 0.0,
) -> Relationship:
    rid = _rel_id(from_npc, to_npc)
    row = session.get(RelationshipRow, rid)
    if row is None:
        row = RelationshipRow(id=rid, from_npc=from_npc, to_npc=to_npc)

    def clamp(v: float) -> float:
        return max(-1.0, min(1.0, v))

    row.trust = clamp(row.trust + trust)
    row.affection = clamp(row.affection + affection)
    row.fear = clamp(row.fear + fear)
    row.debt = clamp(row.debt + debt)
    session.add(row)
    session.commit()
    return Relationship(
        id=row.id, from_npc=row.from_npc, to_npc=row.to_npc,
        trust=row.trust, affection=row.affection,
        fear=row.fear, debt=row.debt,
        kind=getattr(row, "kind", "") or "",
    )


def apply_event_effects(
    session: Session,
    participants: list[str],
    tags: list[str],
    rng: random.Random,
) -> None:
    if len(participants) < 2:
        return
    conflict = "conflict" in tags
    social = "social" in tags or "daily" in tags or "celebration" in tags

    for i, a in enumerate(participants):
        for b in participants[i + 1:]:
            if conflict:
                adjust(session, a, b,
                       trust=-0.05 - rng.random() * 0.1,
                       affection=-0.05,
                       fear=0.05 + rng.random() * 0.1)
                adjust(session, b, a,
                       trust=-0.05 - rng.random() * 0.1,
                       affection=-0.05,
                       fear=0.05 + rng.random() * 0.1)
            elif social:
                adjust(session, a, b,
                       trust=0.03 + rng.random() * 0.05,
                       affection=0.03 + rng.random() * 0.05)
                adjust(session, b, a,
                       trust=0.03 + rng.random() * 0.05,
                       affection=0.03 + rng.random() * 0.05)
            else:
                adjust(session, a, b, trust=rng.uniform(-0.03, 0.03))
                adjust(session, b, a, trust=rng.uniform(-0.03, 0.03))


def list_relationships(session: Session, npc_id: str) -> list[Relationship]:
    rows = session.exec(
        select(RelationshipRow).where(
            (RelationshipRow.from_npc == npc_id) | (RelationshipRow.to_npc == npc_id)
        )
    ).all()
    return [
        Relationship(
            id=r.id, from_npc=r.from_npc, to_npc=r.to_npc,
            trust=r.trust, affection=r.affection,
            fear=r.fear, debt=r.debt,
        )
        for r in rows
    ]


def get_relation_to(session: Session, npc_id: str, target_id: str) -> Relationship:
    """获取 npc 对 target 的关系（单向）。"""
    return get_or_create(session, npc_id, target_id)


def describe_relation_for_prompt(rel: Relationship) -> str:
    """把关系数值转成 LLM 易读的中文描述。"""
    parts: list[str] = []
    if abs(rel.trust) > 0.05:
        level = "非常信任" if rel.trust > 0.4 else ("信任" if rel.trust > 0.15 else ("有些戒备" if rel.trust < -0.15 else "略微保留"))
        parts.append("信任 %.2f（%s）" % (rel.trust, level))
    if abs(rel.affection) > 0.05:
        level = "很有好感" if rel.affection > 0.4 else ("有好感" if rel.affection > 0.15 else ("厌恶" if rel.affection < -0.15 else "淡漠"))
        parts.append("好感 %.2f（%s）" % (rel.affection, level))
    if abs(rel.fear) > 0.05:
        level = "非常恐惧" if rel.fear > 0.4 else ("有些害怕" if rel.fear > 0.15 else "略感不安")
        parts.append("恐惧 %.2f（%s）" % (rel.fear, level))
    if abs(rel.debt) > 0.05:
        level = "欠了很多人情" if rel.debt > 0.3 else ("有些亏欠" if rel.debt > 0.1 else "对方欠我人情")
        parts.append("债务 %.2f（%s）" % (rel.debt, level))

    if not parts:
        return "陌生，没有明显好恶"
    return "，".join(parts)


def npc_effects_from_event(
    session: Session,
    participants: list[str],
    event_id: str,
    summary: str,
    timestamp: int,
    rng: random.Random,
) -> None:
    """写入记忆。用同步版本，避免在事件流程里再 await 一次 embedding。"""
    from server.systems.memory import add_memory
    for npc_id in participants:
        emotion: dict[str, float] = {}
        if rng.random() < 0.3:
            emotion["fear"] = 0.3 + rng.random() * 0.4
        elif rng.random() < 0.3:
            emotion["joy"] = 0.3 + rng.random() * 0.4
        add_memory(
            session,
            npc_id=npc_id,
            event_id=event_id,
            summary=summary,
            emotion=emotion,
            timestamp=timestamp,
        )
