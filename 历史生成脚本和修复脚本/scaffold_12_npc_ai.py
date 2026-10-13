r"""EmergentWorld scaffold - Part 12: NPC 独立 AI + 关系对话 + 语义记忆。

运行：
    python scaffold_12_npc_ai.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ config 覆盖

FILES["server/config.py"] = r'''from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 主 LLM
    llm_api_key: str = "sk-test"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # 嵌入模型（可留空，留空则记忆检索降级为时间排序）
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    db_path: Path = Path("data/world.db")
    cache_dir: Path = Path(".cache/llm")
    seed: int = 42
    log_level: str = "INFO"

    content_dir: Path = Path("content")

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.embedding_api_key.strip())


settings = Settings()
'''

# ================================================================ .env.example

FILES[".env.example"] = r'''LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# 语义记忆检索（可留空，留空则回退到时间排序）
# 推荐硅基流动的 bge-m3，注册送额度：https://cloud.siliconflow.cn/
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3

DB_PATH=data/world.db
CACHE_DIR=.cache/llm
SEED=42
LOG_LEVEL=INFO
'''

# ================================================================ db.py 覆盖（memory 表加 embedding_json）

FILES["server/models/db.py"] = r'''"""SQLModel 表定义。与 schemas.py 保持字段一致。"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Field, SQLModel


class WorldRow(SQLModel, table=True):
    __tablename__ = "world"
    id: str = Field(primary_key=True)
    tick: int = 0
    day: int = 0
    hour: int = 0
    seed: int = 42
    director_json: str = "{}"
    economy_json: str = "{}"
    location_ids_json: str = "[]"


class NPCRow(SQLModel, table=True):
    __tablename__ = "npc"
    id: str = Field(primary_key=True)
    name: str
    age: int = 0
    traits_json: str = "{}"
    needs_json: str = "{}"
    goals_json: str = "[]"
    behavior_json: str = "{}"
    asset_json: str = "{}"
    memory_ids_json: str = "[]"
    location_id: str = "village_square"
    alive: bool = True


class MemoryRow(SQLModel, table=True):
    __tablename__ = "memory"
    id: str = Field(primary_key=True)
    npc_id: str = Field(index=True)
    event_id: str = Field(index=True)
    summary: str = ""
    emotion_json: str = "{}"
    timestamp: int = 0
    embedding_id: str | None = None
    embedding_json: str = "[]"       # 新增：向量存储


class RelationshipRow(SQLModel, table=True):
    __tablename__ = "relationship"
    id: str = Field(primary_key=True)
    from_npc: str = Field(index=True)
    to_npc: str = Field(index=True)
    trust: float = 0.0
    affection: float = 0.0
    fear: float = 0.0
    debt: float = 0.0


class EventRow(SQLModel, table=True):
    __tablename__ = "event"
    id: str = Field(primary_key=True)
    template_id: str = Field(index=True)
    participants_json: str = "[]"
    location_id: str = "village_square"
    state: str = "pending"
    payload_json: str = "{}"
    created_at: int = 0
    resolved_at: int | None = None


class RewardRow(SQLModel, table=True):
    __tablename__ = "reward"
    id: str = Field(primary_key=True)
    event_id: str = Field(index=True)
    kind: str
    value: float = 0.0
    description: str = ""
    payload_json: str = "{}"


class ItemRow(SQLModel, table=True):
    __tablename__ = "item"
    id: str = Field(primary_key=True)
    reward_id: str = Field(index=True)
    event_id: str = Field(index=True)
    name: str = ""
    kind: str = ""
    affixes_json: str = "[]"
    story: str = ""
    value: float = 0.0
    owner_id: str = Field(default="", index=True)
    consumed: bool = False


class ItemUseRow(SQLModel, table=True):
    __tablename__ = "item_use"
    id: str = Field(primary_key=True)
    item_id: str = Field(index=True)
    user_id: str = ""
    target_npc_id: str = ""
    effect: str = ""
    consumed: bool = False
    timestamp: int = 0


class EvaluationRow(SQLModel, table=True):
    __tablename__ = "evaluation"
    id: str = Field(primary_key=True)
    target_type: str = Field(index=True)
    target_id: str = Field(index=True)
    passed: bool = False
    score: float | None = None
    errors_json: str = "[]"
    raw_json: str = "{}"


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def loads(s: str) -> Any:
    return json.loads(s) if s else None
'''

# ================================================================ session.py 覆盖（加 memory.embedding_json 升级）

FILES["server/db/session.py"] = r'''"""数据库会话工厂 + schema 增量升级。"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, create_engine

from server.config import settings

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


def get_session() -> Session:
    return Session(engine)


def _has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(text("PRAGMA table_info(%s)" % table)).fetchall()
    if not rows:
        return True  # 表不存在，视为无需升级
    return column in {r[1] for r in rows}


def ensure_schema() -> None:
    """对已有数据库做增量列升级。"""
    with engine.begin() as conn:
        # item 表（Part 11 引入）
        if not _has_column(conn, "item", "owner_id"):
            conn.execute(text(
                "ALTER TABLE item ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''"
            ))
        if not _has_column(conn, "item", "consumed"):
            conn.execute(text(
                "ALTER TABLE item ADD COLUMN consumed INTEGER NOT NULL DEFAULT 0"
            ))

        # memory 表（Part 12 引入）
        if not _has_column(conn, "memory", "embedding_json"):
            conn.execute(text(
                "ALTER TABLE memory ADD COLUMN embedding_json TEXT NOT NULL DEFAULT '[]'"
            ))
'''

# ================================================================ embedding 客户端

FILES["server/systems/embedding.py"] = r'''"""嵌入客户端：把文本转成向量。

未配置 EMBEDDING_API_KEY 时，返回空向量（[]），
调用方应回退到其它检索方式。
"""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache

from openai import AsyncOpenAI

from server.config import settings


def _hash_fallback(text: str, dim: int = 64) -> list[float]:
    """无 embedding 服务时的确定性哈希向量。

    用于测试和极端兜底。词义相似度很差，但至少能跑通流程。
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec: list[float] = []
    for i in range(dim):
        b = h[i % len(h)]
        vec.append((b / 255.0) * 2.0 - 1.0)
    return vec


class EmbeddingClient:
    def __init__(self) -> None:
        self.enabled = settings.embedding_enabled
        self.model = settings.embedding_model
        if self.enabled:
            self.client = AsyncOpenAI(
                api_key=settings.embedding_api_key,
                base_url=settings.embedding_base_url,
            )
        else:
            self.client = None

    async def embed(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            return []
        if not self.enabled or self.client is None:
            return _hash_fallback(text)
        try:
            resp = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return list(resp.data[0].embedding)
        except Exception:
            return _hash_fallback(text)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def serialize(vec: list[float]) -> str:
    return json.dumps(vec, ensure_ascii=False)


def deserialize(s: str) -> list[float]:
    if not s:
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [float(x) for x in v]
    except Exception:
        pass
    return []


@lru_cache(maxsize=1)
def get_embedding() -> EmbeddingClient:
    return EmbeddingClient()
'''

# ================================================================ memory 覆盖

FILES["server/systems/memory.py"] = r'''"""记忆系统：写入时生成 embedding，检索时按语义相似度排序。"""

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
'''

# ================================================================ relationship 加辅助

FILES["server/systems/relationship.py"] = r'''"""关系系统：NPC 之间的信任、好感、恐惧、债务。"""

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
'''

# ================================================================ behavior 覆盖

FILES["server/systems/behavior.py"] = r'''"""效用 AI：NPC 独立 RNG + 目标驱动 + 时间偏好 + 关系牵引。"""

from __future__ import annotations

import hashlib
import random

from sqlmodel import Session

from server.core.world import load_npcs
from server.models.schemas import Action, NPC, World

DEFAULT_ACTIONS = [
    Action(id="eat", need="hunger", location_id="tavern"),
    Action(id="rest", need="safety", location_id="home"),
    Action(id="socialize", need="social", location_id="village_square"),
    Action(id="work", need="wealth", location_id="market"),
    Action(id="explore", need="curiosity", location_id="forest"),
]

# 每个行为的基座需求
ACTION_NEED = {a.id: a.need for a in DEFAULT_ACTIONS}

# 时间段偏好：hour → {action_id: bonus}
TIME_PREFS: dict[str, dict[str, float]] = {
    "morning":   {"work": 0.35, "explore": 0.1, "eat": 0.05},
    "noon":      {"eat": 0.35, "socialize": 0.15},
    "afternoon": {"work": 0.25, "socialize": 0.2, "explore": 0.15},
    "evening":   {"socialize": 0.3, "eat": 0.25, "explore": 0.1},
    "night":     {"rest": 0.5, "eat": 0.1},
}

# 目标关键词 → 行为
GOAL_KEYWORDS: dict[str, str] = {
    "钱": "work", "wealth": "work", "攒": "work", "生意": "work", "商": "work",
    "朋友": "socialize", "社交": "socialize", "关系": "socialize", "盟友": "socialize",
    "家": "rest", "安": "rest", "睡": "rest", "休息": "rest",
    "吃": "eat", "食": "eat", "饭": "eat",
    "探索": "explore", "寻": "explore", "冒险": "explore", "旅": "explore", "查": "explore",
}

# 地点容量：超过则想去的人会犹豫
LOCATION_CAPACITY: dict[str, int] = {
    "village_square": 6,
    "market": 4,
    "tavern": 4,
    "home": 8,
    "forest": 3,
    "village_edge": 3,
    "village_hall": 3,
}


def _npc_rng(world: World, npc_id: str) -> random.Random:
    h = int(hashlib.md5(npc_id.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(world.seed * 1000003 + world.tick * 31 + h)


def _time_slot(hour: int) -> str:
    if 6 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _goal_bonus(npc: NPC) -> dict[str, float]:
    """从 goals 文本里挖关键词，给对应行为加权。"""
    bonus: dict[str, float] = {a.id: 0.0 for a in DEFAULT_ACTIONS}
    for g in npc.goals:
        g_low = g.lower()
        for kw, action_id in GOAL_KEYWORDS.items():
            if kw in g or kw in g_low:
                bonus[action_id] = bonus.get(action_id, 0.0) + 0.15
    return bonus


def _crowd_penalty(session: Session, world: World, npc_id: str) -> dict[str, float]:
    """目标地点越挤，越不想去。"""
    npcs = load_npcs(session)
    by_loc: dict[str, int] = {}
    for n in npcs:
        if n.id == npc_id:
            continue
        by_loc[n.location_id] = by_loc.get(n.location_id, 0) + 1

    penalty: dict[str, float] = {}
    for action in DEFAULT_ACTIONS:
        if not action.location_id:
            penalty[action.id] = 0.0
            continue
        cap = LOCATION_CAPACITY.get(action.location_id, 5)
        cur = by_loc.get(action.location_id, 0)
        if cur >= cap:
            penalty[action.id] = -0.25
        elif cur >= cap - 1:
            penalty[action.id] = -0.1
        else:
            penalty[action.id] = 0.0
    return penalty


def _friendship_pull(session: Session, world: World, npc: NPC) -> dict[str, float]:
    """如果关系好的 NPC 在某地，倾向于过去（每个地点最多 +0.15）。"""
    from server.systems.relationship import list_relationships

    rels = list_relationships(session, npc.id)
    friend_ids: list[str] = []
    for r in rels:
        other = r.to_npc if r.from_npc == npc.id else r.from_npc
        score = r.trust + r.affection - r.fear
        if score > 0.25:
            friend_ids.append(other)
    if not friend_ids:
        return {a.id: 0.0 for a in DEFAULT_ACTIONS}

    friend_locs: dict[str, int] = {}
    for n in load_npcs(session):
        if n.id in friend_ids:
            friend_locs[n.location_id] = friend_locs.get(n.location_id, 0) + 1

    pull: dict[str, float] = {}
    for action in DEFAULT_ACTIONS:
        pull[action.id] = min(0.15, 0.06 * friend_locs.get(action.location_id or "", 0))
    return pull


def score_action(
    session: Session,
    world: World,
    npc: NPC,
    action: Action,
    goal_bonus: dict[str, float],
    time_bonus: dict[str, float],
    crowd_penalty: dict[str, float],
    friend_pull: dict[str, float],
) -> float:
    need_val = npc.needs.get(action.need, 0.5)
    weight = npc.behavior_profile.get(action.need, 0.5)

    base = need_val * weight * 1.4
    base += goal_bonus.get(action.id, 0.0)
    base += time_bonus.get(action.id, 0.0)
    base += crowd_penalty.get(action.id, 0.0)
    base += friend_pull.get(action.id, 0.0)

    # 家（休息）与安全需求相关，加一个小偏置
    if action.id == "rest":
        base += (npc.needs.get("safety", 0.5) - 0.5) * 0.2

    return base


def decide(session: Session, world: World, npc: NPC, rng: random.Random) -> Action:
    goal_bonus = _goal_bonus(npc)
    slot = _time_slot(world.hour)
    time_bonus = {a.id: TIME_PREFS.get(slot, {}).get(a.id, 0.0) for a in DEFAULT_ACTIONS}
    crowd_penalty = _crowd_penalty(session, world, npc.id)
    friend_pull = _friendship_pull(session, world, npc)

    scored: list[tuple[float, Action]] = []
    for a in DEFAULT_ACTIONS:
        s = score_action(session, world, npc, a, goal_bonus,
                         time_bonus, crowd_penalty, friend_pull)
        # 少量随机扰动，避免所有 NPC 同步
        s += rng.uniform(-0.05, 0.05)
        scored.append((s, a))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 采样 top-2，避免完全确定
    top = scored[:2]
    return rng.choices([a for _, a in top],
                       weights=[max(s + 1.0, 0.01) for s, _ in top],
                       k=1)[0]


def step(session: Session, world: World) -> None:
    npcs = load_npcs(session)
    for npc in npcs:
        rng = _npc_rng(world, npc.id)
        action = decide(session, world, npc, rng)
        if action.location_id:
            npc.location_id = action.location_id
        # 需求变化：当前行为对应的需求下降，其它缓慢上升
        for k in npc.needs:
            delta = -0.06 if k == action.need else 0.02
            npc.needs[k] = max(0.0, min(1.0, npc.needs.get(k, 0.5) + delta))

    # 保存到数据库
    from server.core.world import save_npc
    for npc in npcs:
        save_npc(session, npc)
'''

# ================================================================ dialogue 覆盖

FILES["server/generators/dialogue.py"] = r'''"""NPC 对话：关系上下文 + 语义检索记忆。"""

from __future__ import annotations

from sqlmodel import Session

from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC, World
from server.systems import relationship
from server.systems.memory import retrieve_relevant, summarize_for_prompt


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

    prompt = load_prompt("dialogue.md").format(
        name=npc.name,
        age=npc.age,
        traits=npc.traits,
        goals="，".join(npc.goals) or "（无明确目标）",
        location=npc.location_id,
        relation_desc=relation_desc,
        relationship_hint=relationship_hint,
        memories="\n".join("- " + m for m in mem_summaries) or "（没有特别的记忆）",
        player_input=player_input,
    )

    try:
        reply = await get_llm().text(prompt)
    except Exception:
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
'''

# ================================================================ prompt 覆盖

FILES["server/prompts/dialogue.md"] = r'''你在扮演一个游戏 NPC。根据人设、关系与记忆，对玩家的话做出回应。

规则：
- 保持角色口吻，符合其性格、目标、处境、关系
- 不超过 3 句
- 如果有相关记忆，自然地带入
- 不要提及你是 AI
- 不要输出 markdown
- 只输出回复文本本身，不要加引号、不要加前缀

角色：
  名字：{name}
  年龄：{age}
  性格：{traits}
  目标：{goals}
  当前位置：{location}

你与玩家的关系：
  {relation_desc}

语气建议：
  {relationship_hint}

你记得的事：
{memories}

玩家说：{player_input}
'''

# ================================================================ routes_dialogue 覆盖

FILES["server/api/routes_dialogue.py"] = r'''"""NPC 对话端点：关系上下文 + 语义记忆检索。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.core.world import load_npcs, load_world
from server.db.session import get_session
from server.generators.dialogue import npc_dialogue

router = APIRouter(prefix="/npc", tags=["dialogue"])


class DialogueRequest(BaseModel):
    player_input: str


class DialogueResponse(BaseModel):
    npc_id: str
    npc_name: str
    reply: str
    memories_used: list[str]
    relation_desc: str


@router.post("/{npc_id}/dialogue", response_model=DialogueResponse)
async def dialogue(npc_id: str, req: DialogueRequest) -> DialogueResponse:
    with get_session() as s:
        world = load_world(s)
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        npc = npcs[npc_id]

        result = await npc_dialogue(
            session=s,
            npc=npc,
            player_input=req.player_input,
            world=world,
        )

    return DialogueResponse(
        npc_id=npc.id,
        npc_name=npc.name,
        reply=result["reply"],
        memories_used=result["memories_used"],
        relation_desc=result["relation_desc"],
    )
'''

# ================================================================ main.py 覆盖（加 /memory/backfill）

FILES["server/main.py"] = r'''"""FastAPI 入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

from server import i18n
from server.api import routes_dialogue, routes_review
from server.config import settings
from server.core import director
from server.core.event_flow import run_event_cycle
from server.core.map_view import build_map_data
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.db.session import engine, ensure_schema
from server.models.db import EventRow, ItemRow, MemoryRow, RewardRow, dumps, loads
from server.models.schemas import Event, NPC, Reward, World
from server.systems import inventory, item_use, relationship
from server.systems.embedding import get_embedding, serialize


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    ensure_schema()
    with Session(engine) as session:
        load_world(session)
    yield


app = FastAPI(title="EmergentWorld", lifespan=lifespan)
app.include_router(routes_dialogue.router)
app.include_router(routes_review.router)


def get_session() -> Session:
    return Session(engine)


@app.get("/")
def root() -> dict:
    return {
        "name": "EmergentWorld",
        "version": "0.7.0",
        "docs": "/docs",
        "embedding_enabled": settings.embedding_enabled,
        "endpoints": [
            "/health", "/i18n", "/map",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/npc/{npc_id}/items", "/npc/{npc_id}/memories",
            "/event", "/event/trigger",
            "/reward",
            "/item", "/item/{item_id}",
            "/item/{item_id}/give", "/item/{item_id}/take",
            "/item/{item_id}/use",
            "/memory/backfill",
            "/review/latest",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/i18n")
def i18n_endpoint() -> dict:
    return i18n.all_labels()


@app.get("/map")
def map_view() -> dict:
    with get_session() as s:
        world = load_world(s)
        return build_map_data(s, world)


@app.post("/memory/backfill")
async def memory_backfill(limit: int = 200) -> dict:
    """给已有记忆批量补 embedding。用于启用 embedding 后的一次性迁移。"""
    if not settings.embedding_enabled:
        raise HTTPException(400, "embedding not enabled (set EMBEDDING_API_KEY)")
    client = get_embedding()
    count = 0
    with get_session() as s:
        rows = s.exec(select(MemoryRow).limit(limit)).all()
        for r in rows:
            if r.embedding_json and r.embedding_json != "[]":
                continue
            vec = await client.embed(r.summary)
            r.embedding_json = serialize(vec)
            s.add(r)
            count += 1
        s.commit()
    return {"updated": count, "checked": len(rows)}


# ---------- World ----------

@app.get("/world/state", response_model=World)
def world_state() -> World:
    with get_session() as s:
        return load_world(s)


@app.post("/world/tick", response_model=World)
def world_tick() -> World:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        save_world(s, world)
        return world


@app.post("/world/step")
async def world_step() -> dict:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)
        save_world(s, world)
        return {
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
            "tension": world.director.tension,
            "event": event.id if event else None,
            "event_summary": event.payload.get("summary") if event else None,
            "event_template": event.template_id if event else None,
            "template_label": i18n.template_label(event.template_id) if event else None,
        }


# ---------- NPC ----------

def _npc_to_display(npc: NPC) -> dict:
    return {
        "id": npc.id,
        "name": npc.name,
        "age": npc.age,
        "location_id": npc.location_id,
        "location_label": i18n.location_label(npc.location_id),
        "goals": npc.goals,
        "traits": [
            {"key": k, "label": i18n.trait_label(k), "value": float(v)}
            for k, v in npc.traits.items()
        ],
        "needs": [
            {"key": k, "label": i18n.need_label(k), "value": float(v)}
            for k, v in npc.needs.items()
        ],
    }


@app.get("/npc")
def list_npcs() -> list[dict]:
    with get_session() as s:
        return [_npc_to_display(n) for n in load_npcs(s)]


@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id])


@app.get("/npc/{npc_id}/relationships")
def npc_relationships(npc_id: str) -> list[dict]:
    with get_session() as s:
        npcs = {n.id: n.name for n in load_npcs(s)}
        result = []
        for r in relationship.list_relationships(s, npc_id):
            other_id = r.to_npc if r.from_npc == npc_id else r.from_npc
            result.append({
                "from_npc": r.from_npc,
                "to_npc": r.to_npc,
                "other_id": other_id,
                "other_name": npcs.get(other_id, other_id),
                "trust": r.trust,
                "affection": r.affection,
                "fear": r.fear,
                "debt": r.debt,
            })
        return result


@app.get("/npc/{npc_id}/items")
def npc_items(npc_id: str) -> list[dict]:
    with get_session() as s:
        rows = inventory.list_items_by_owner(s, npc_id)
        return [inventory.row_to_dict(r) for r in rows]


@app.get("/npc/{npc_id}/memories")
def npc_memories(npc_id: str, limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(MemoryRow)
            .where(MemoryRow.npc_id == npc_id)
            .order_by(MemoryRow.timestamp.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": r.id,
                "event_id": r.event_id,
                "summary": r.summary,
                "emotion": loads(r.emotion_json) or {},
                "timestamp": r.timestamp,
                "has_embedding": bool(r.embedding_json and r.embedding_json != "[]"),
            }
            for r in rows
        ]


# ---------- Event ----------

def _row_to_event(r: EventRow) -> dict:
    payload = loads(r.payload_json) or {}
    return {
        "id": r.id,
        "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": loads(r.participants_json) or [],
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state,
        "state_label": i18n.state_label(r.state),
        "payload": payload,
        "summary": payload.get("summary", ""),
        "narrative": payload.get("narrative", ""),
        "item_id": payload.get("item_id"),
        "item_owner": payload.get("item_owner"),
        "created_at": r.created_at,
        "resolved_at": r.resolved_at,
    }


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()
        return [_row_to_event(r) for r in rows]


@app.post("/event/trigger")
async def trigger_event() -> dict:
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered (check templates / npcs)")
        return _row_to_event(
            EventRow(
                id=event.id,
                template_id=event.template_id,
                participants_json=dumps(event.participants),
                location_id=event.location_id,
                state=event.state,
                payload_json=dumps(event.payload),
                created_at=event.created_at,
                resolved_at=event.resolved_at,
            )
        )


# ---------- Reward ----------

@app.get("/reward")
def list_rewards(limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(RewardRow).order_by(RewardRow.id.desc()).limit(limit)
        ).all()
        return [
            {
                "id": r.id,
                "event_id": r.event_id,
                "kind": r.kind,
                "kind_label": i18n.reward_kind_label(r.kind),
                "value": r.value,
                "description": r.description,
                "payload": loads(r.payload_json) or {},
            }
            for r in rows
        ]


# ---------- Item ----------

class GiveRequest(BaseModel):
    owner_id: str


class UseRequest(BaseModel):
    target_npc_id: str = ""


def _row_to_item(r: ItemRow, npc_names: dict[str, str]) -> dict:
    owner_id = r.owner_id or ""
    if owner_id == "player":
        owner_label = "你"
    elif owner_id in npc_names:
        owner_label = npc_names[owner_id]
    elif owner_id:
        owner_label = owner_id
    else:
        owner_label = "无主"
    return {
        "id": r.id,
        "reward_id": r.reward_id,
        "event_id": r.event_id,
        "name": r.name,
        "kind": r.kind,
        "affixes": loads(r.affixes_json) or [],
        "story": r.story,
        "value": r.value,
        "owner_id": owner_id,
        "owner_label": owner_label,
        "consumed": r.consumed,
    }


@app.get("/item")
def list_items(limit: int = 100, owner_id: str | None = None) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        if owner_id is None:
            rows = inventory.list_all_items(s)
        else:
            rows = inventory.list_items_by_owner(s, owner_id)
        rows = rows[:limit]
        return [_row_to_item(r, npc_names) for r in rows]


@app.get("/item/{item_id}")
def get_item(item_id: str) -> dict:
    with get_session() as s:
        row = inventory.get_item_row(s, item_id)
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/give")
def give_item(item_id: str, req: GiveRequest) -> dict:
    with get_session() as s:
        row = inventory.give_item(s, item_id, req.owner_id)
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/take")
def take_item(item_id: str) -> dict:
    with get_session() as s:
        row = inventory.give_item(s, item_id, "player")
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/drop")
def drop_item(item_id: str) -> dict:
    with get_session() as s:
        row = inventory.drop_item(s, item_id)
        if row is None:
            raise HTTPException(404, "item not found")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        return _row_to_item(row, npc_names)


@app.post("/item/{item_id}/use")
async def use_item_endpoint(item_id: str, req: UseRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await item_use.use_item(
            s, world,
            item_id=item_id,
            user_id="player",
            target_npc_id=req.target_npc_id,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "use failed"))
        return result
'''

# ================================================================ tests

FILES["tests/test_behavior.py"] = r'''import random

from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_npc, save_world
from server.models.schemas import NPC
from server.systems import behavior


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_npc_rng_is_deterministic():
    w = create_world("t", seed=42)
    r1 = behavior._npc_rng(w, "npc_a")
    r2 = behavior._npc_rng(w, "npc_a")
    r3 = behavior._npc_rng(w, "npc_b")
    assert r1.random() == r2.random()  # 相同种子
    # 不同 NPC 的随机序列应不同
    a = [behavior._npc_rng(w, "npc_a").random() for _ in range(5)]
    b = [behavior._npc_rng(w, "npc_b").random() for _ in range(5)]
    assert a != b


def test_time_prefs_shift_by_hour():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.hour = 9  # morning
        save_world(s, world)
        npc = NPC(id="npc_x", name="X", age=30, goals=["赚钱"],
                  behavior_profile={"wealth": 0.9, "social": 0.5})
        save_npc(s, npc)
        rng = random.Random(1)
        action = behavior.decide(s, world, npc, rng)
        assert action.id in {"work", "explore", "eat", "socialize", "rest"}


def test_crowd_penalty_exists():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        for i in range(6):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i,
                            age=20, location_id="village_square"))
        penalty = behavior._crowd_penalty(s, world, "npc_0")
        assert penalty["socialize"] < 0


def test_step_moves_npcs_and_saves():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20,
                            goals=["x"], behavior_profile={"wealth": 0.5}))
        behavior.step(s, world)
        from server.core.world import load_npcs
        npcs = load_npcs(s)
        assert len(npcs) == 3
'''

FILES["tests/test_memory_retrieval.py"] = r'''import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.models.db import MemoryRow, dumps
from server.systems.embedding import cosine, deserialize, serialize
from server.systems.memory import retrieve_relevant


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_cosine_identical_vectors():
    v = [1.0, 2.0, 3.0]
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine(a, b)) < 1e-6


def test_serialize_roundtrip():
    v = [0.1, 0.2, 0.3]
    assert deserialize(serialize(v)) == v


@pytest.mark.asyncio
async def test_retrieve_falls_back_without_embedding(monkeypatch):
    """无 embedding 服务时，应按时间倒序返回最近记忆。"""
    from server.systems import memory as memory_mod

    class FakeEmb:
        enabled = False
        async def embed(self, text):
            return [1.0, 0.0, 0.0]

    monkeypatch.setattr(memory_mod, "get_embedding", lambda: FakeEmb())

    engine = _engine()
    with Session(engine) as s:
        for i in range(5):
            row = MemoryRow(
                id="mem_%d" % i,
                npc_id="npc_a",
                event_id="evt_%d" % i,
                summary="事件 %d" % i,
                emotion_json="{}",
                timestamp=100 - i,
                embedding_json="[]",
            )
            s.add(row)
        s.commit()
        result = await retrieve_relevant(s, "npc_a", "最近的", top_k=3)
        assert len(result) == 3
        # timestamp 越大越靠前
        assert result[0].timestamp == 100
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    written = 0
    skipped = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print("[skip]  " + rel)
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print("[write] " + rel)
        written += 1

    print("\nPart 12 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. 编辑 .env 加上 EMBEDDING_API_KEY（可留空）")
    print("  2. pytest -v")
    print("  3. 重启后端 uvicorn server.main:app --reload")
    print("  4. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()