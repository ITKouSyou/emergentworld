"""记忆系统：写入时生成 embedding，检索时按语义相似度排序。"""

from __future__ import annotations

import uuid

from sqlmodel import Session, select

from server.models.db import MemoryRow, dumps, loads
from server.models.schemas import Memory
from server.systems.embedding import (
    cosine,
    deserialize,
    get_embedding,
    serialize,
)


def _row_to_memory(r: MemoryRow) -> Memory:
    return Memory(
        id=r.id,
        npc_id=r.npc_id,
        event_id=r.event_id,
        summary=r.summary,
        emotion=loads(r.emotion_json) or {},
        timestamp=r.timestamp,
        embedding_id=r.embedding_id,
    )


async def add_memory_with_embedding(
    session: Session,
    npc_id: str,
    event_id: str,
    summary: str,
    emotion: dict[str, float] | None = None,
    timestamp: int = 0,
) -> Memory:
    """写入记忆并生成 embedding。"""
    mem_id = "mem_%s" % uuid.uuid4().hex[:8]

    vec = await get_embedding().embed(summary)

    row = MemoryRow(
        id=mem_id,
        npc_id=npc_id,
        event_id=event_id,
        summary=summary,
        emotion_json=dumps(emotion or {}),
        timestamp=timestamp,
        embedding_id=None,
        embedding_json=serialize(vec),
    )
    session.add(row)
    session.commit()

    return Memory(
        id=mem_id,
        npc_id=npc_id,
        event_id=event_id,
        summary=summary,
        emotion=emotion or {},
        timestamp=timestamp,
        embedding_id=None,
    )


def add_memory(
    session: Session,
    npc_id: str,
    event_id: str,
    summary: str,
    emotion: dict[str, float] | None = None,
    timestamp: int = 0,
) -> Memory:
    """同步写入，不带 embedding（用于测试 / 批量模拟）。"""
    mem_id = "mem_%s" % uuid.uuid4().hex[:8]
    row = MemoryRow(
        id=mem_id,
        npc_id=npc_id,
        event_id=event_id,
        summary=summary,
        emotion_json=dumps(emotion or {}),
        timestamp=timestamp,
        embedding_id=None,
        embedding_json="[]",
    )
    session.add(row)
    session.commit()
    return Memory(
        id=mem_id,
        npc_id=npc_id,
        event_id=event_id,
        summary=summary,
        emotion=emotion or {},
        timestamp=timestamp,
        embedding_id=None,
    )


def list_memories(session: Session, npc_id: str, limit: int = 20) -> list[Memory]:
    rows = session.exec(
        select(MemoryRow)
        .where(MemoryRow.npc_id == npc_id)
        .order_by(MemoryRow.timestamp.desc())
        .limit(limit)
    ).all()
    return [_row_to_memory(r) for r in rows]


def _all_memory_rows(session: Session, npc_id: str) -> list[MemoryRow]:
    return list(session.exec(
        select(MemoryRow).where(MemoryRow.npc_id == npc_id)
    ).all())


async def retrieve_relevant(
    session: Session,
    npc_id: str,
    query: str,
    top_k: int = 5,
) -> list[Memory]:
    """语义检索：按与 query 的余弦相似度排序。

    如果没有 embedding 服务，仍会用哈希向量做粗糙排序，
    效果不如语义模型，但比纯时间排序好一点。
    """
    rows = _all_memory_rows(session, npc_id)
    if not rows:
        return []

    q_vec = await get_embedding().embed(query)
    if not q_vec:
        return [_row_to_memory(r) for r in rows[:top_k]]

    scored: list[tuple[float, MemoryRow]] = []
    for r in rows:
        vec = deserialize(r.embedding_json or "")
        if not vec:
            # 没向量的旧记忆，给一个低分但不丢弃
            scored.append((0.0, r))
            continue
        scored.append((cosine(q_vec, vec), r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_row_to_memory(r) for _, r in scored[:top_k]]


def summarize_for_prompt(memories: list[Memory], limit: int = 5) -> list[str]:
    return [m.summary for m in memories[:limit] if m.summary]
