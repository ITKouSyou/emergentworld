"""EmergentWorld Part 18：NPC 自主对话 + 编年史长文本 + 季节天气。

运行：
    python scaffold_18.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================
# server/models/schemas.py
# ================================================================

FILES["server/models/schemas.py"] = r'''"""所有 Pydantic 数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NPC(BaseModel):
    id: str
    name: str
    age: int = Field(ge=0, le=200)
    gender: str = "unknown"
    traits: dict[str, float] = Field(default_factory=dict)
    needs: dict[str, float] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)
    behavior_profile: dict[str, float] = Field(default_factory=dict)
    asset_params: dict[str, Any] = Field(default_factory=dict)
    memory_ids: list[str] = Field(default_factory=list)
    location_id: str = "village_square"
    alive: bool = True


class Memory(BaseModel):
    id: str
    npc_id: str
    event_id: str
    summary: str
    emotion: dict[str, float] = Field(default_factory=dict)
    timestamp: int
    embedding_id: str | None = None


class Relationship(BaseModel):
    id: str
    from_npc: str
    to_npc: str
    trust: float = 0.0
    affection: float = 0.0
    fear: float = 0.0
    debt: float = 0.0


EventState = Literal[
    "pending", "active", "awaiting_player",
    "resolved", "expired", "rejected",
]


class Event(BaseModel):
    id: str
    template_id: str
    participants: list[str] = Field(default_factory=list)
    location_id: str = "village_square"
    state: EventState = "pending"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: int = 0
    resolved_at: int | None = None


class EventTemplate(BaseModel):
    id: str
    tags: list[str] = Field(default_factory=list)
    cooldown: int = 3
    weight: float = 1.0
    conditions: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    prompt: str = ""
    evaluator: dict[str, Any] = Field(default_factory=dict)
    interactive: bool = True


class Reward(BaseModel):
    id: str
    event_id: str
    kind: Literal["item", "relationship", "info", "reputation", "skill", "story"]
    value: float = Field(ge=0.0)
    description: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    id: str
    name: str
    kind: str
    affixes: list[str] = Field(default_factory=list)
    story: str = ""
    value: float = 0.0


class Evaluation(BaseModel):
    id: str
    target_type: Literal["event", "npc", "reward", "template"]
    target_id: str
    passed: bool
    score: float | None = None
    errors: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class Chronicle(BaseModel):
    id: str
    title: str
    body: str
    from_tick: int = 0
    to_tick: int = 0
    created_at: int = 0


class DirectorState(BaseModel):
    tension: float = 0.2
    last_event_tick: int = -999
    event_history: list[str] = Field(default_factory=list)


class EconomyState(BaseModel):
    total_currency: float = 1000.0
    inflation: float = 1.0
    reward_budget_multiplier: float = 1.0


class World(BaseModel):
    id: str
    tick: int = 0
    day: int = 0
    hour: int = 0
    seed: int = 42
    season: str = "spring"
    weather: str = "clear"
    weather_changed_tick: int = 0
    last_social_tick: int = -999
    social_count_today: int = 0
    director: DirectorState = Field(default_factory=DirectorState)
    economy: EconomyState = Field(default_factory=EconomyState)
    location_ids: list[str] = Field(default_factory=lambda: ["village_square"])


class Action(BaseModel):
    id: str
    need: str
    location_id: str | None = None
    target_npc: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
'''

# ================================================================
# server/models/db.py
# ================================================================

FILES["server/models/db.py"] = r'''"""SQLModel 表定义。"""

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
    season: str = "spring"
    weather: str = "clear"
    weather_changed_tick: int = 0
    last_social_tick: int = -999
    social_count_today: int = 0


class NPCRow(SQLModel, table=True):
    __tablename__ = "npc"
    id: str = Field(primary_key=True)
    name: str
    age: int = 0
    gender: str = "unknown"
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
    embedding_json: str = "[]"


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


class ChronicleRow(SQLModel, table=True):
    __tablename__ = "chronicle"
    id: str = Field(primary_key=True)
    title: str = ""
    body: str = ""
    from_tick: int = 0
    to_tick: int = 0
    created_at: int = 0


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

# ================================================================
# server/db/session.py
# ================================================================

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
        return True
    return column in {r[1] for r in rows}


def _add_col(conn, table: str, col: str, ddl: str) -> None:
    if not _has_column(conn, table, col):
        conn.execute(text("ALTER TABLE %s ADD COLUMN %s" % (table, ddl)))


def ensure_schema() -> None:
    with engine.begin() as conn:
        # item
        _add_col(conn, "item", "owner_id", "owner_id TEXT NOT NULL DEFAULT ''")
        _add_col(conn, "item", "consumed", "consumed INTEGER NOT NULL DEFAULT 0")
        # memory
        _add_col(conn, "memory", "embedding_json", "embedding_json TEXT NOT NULL DEFAULT '[]'")
        # npc
        _add_col(conn, "npc", "gender", "gender TEXT NOT NULL DEFAULT 'unknown'")
        # world
        _add_col(conn, "world", "season", "season TEXT NOT NULL DEFAULT 'spring'")
        _add_col(conn, "world", "weather", "weather TEXT NOT NULL DEFAULT 'clear'")
        _add_col(conn, "world", "weather_changed_tick",
                 "weather_changed_tick INTEGER NOT NULL DEFAULT 0")
        _add_col(conn, "world", "last_social_tick",
                 "last_social_tick INTEGER NOT NULL DEFAULT -999")
        _add_col(conn, "world", "social_count_today",
                 "social_count_today INTEGER NOT NULL DEFAULT 0")
'''

# ================================================================
# server/core/world.py
# ================================================================

FILES["server/core/world.py"] = r'''"""世界状态管理。"""

from __future__ import annotations

from sqlmodel import Session, select

from server.models.db import EventRow, NPCRow, WorldRow, dumps, loads
from server.models.schemas import DirectorState, EconomyState, Event, NPC, World


def create_world(world_id: str = "default", seed: int = 42) -> World:
    return World(id=world_id, seed=seed)


def save_world(session: Session, world: World) -> None:
    row = session.get(WorldRow, world.id) or WorldRow(id=world.id)
    row.tick = world.tick
    row.day = world.day
    row.hour = world.hour
    row.seed = world.seed
    row.director_json = dumps(world.director.model_dump())
    row.economy_json = dumps(world.economy.model_dump())
    row.location_ids_json = dumps(world.location_ids)
    row.season = world.season
    row.weather = world.weather
    row.weather_changed_tick = world.weather_changed_tick
    row.last_social_tick = world.last_social_tick
    row.social_count_today = world.social_count_today
    session.add(row)
    session.commit()


def load_world(session: Session, world_id: str = "default") -> World:
    row = session.get(WorldRow, world_id)
    if row is None:
        w = create_world(world_id)
        save_world(session, w)
        return w
    return World(
        id=row.id,
        tick=row.tick,
        day=row.day,
        hour=row.hour,
        seed=row.seed,
        season=row.season or "spring",
        weather=row.weather or "clear",
        weather_changed_tick=row.weather_changed_tick or 0,
        last_social_tick=row.last_social_tick if row.last_social_tick is not None else -999,
        social_count_today=row.social_count_today or 0,
        director=DirectorState(**loads(row.director_json)),
        economy=EconomyState(**loads(row.economy_json)),
        location_ids=loads(row.location_ids_json) or ["village_square"],
    )


def save_npc(session: Session, npc: NPC) -> None:
    row = session.get(NPCRow, npc.id) or NPCRow(id=npc.id, name=npc.name)
    row.name = npc.name
    row.age = npc.age
    row.gender = npc.gender
    row.traits_json = dumps(npc.traits)
    row.needs_json = dumps(npc.needs)
    row.goals_json = dumps(npc.goals)
    row.behavior_json = dumps(npc.behavior_profile)
    row.asset_json = dumps(npc.asset_params)
    row.memory_ids_json = dumps(npc.memory_ids)
    row.location_id = npc.location_id
    row.alive = npc.alive
    session.add(row)
    session.commit()


def load_npcs(session: Session) -> list[NPC]:
    rows = session.exec(select(NPCRow).where(NPCRow.alive == True)).all()  # noqa: E712
    return [
        NPC(
            id=r.id,
            name=r.name,
            age=r.age,
            gender=r.gender or "unknown",
            traits=loads(r.traits_json) or {},
            needs=loads(r.needs_json) or {},
            goals=loads(r.goals_json) or [],
            behavior_profile=loads(r.behavior_json) or {},
            asset_params=loads(r.asset_json) or {},
            memory_ids=loads(r.memory_ids_json) or [],
            location_id=r.location_id,
            alive=r.alive,
        )
        for r in rows
    ]


def save_event(session: Session, event: Event) -> None:
    row = session.get(EventRow, event.id) or EventRow(id=event.id, template_id=event.template_id)
    row.template_id = event.template_id
    row.participants_json = dumps(event.participants)
    row.location_id = event.location_id
    row.state = event.state
    row.payload_json = dumps(event.payload)
    row.created_at = event.created_at
    row.resolved_at = event.resolved_at
    session.add(row)
    session.commit()
'''

# ================================================================
# server/systems/weather.py
# ================================================================

FILES["server/systems/weather.py"] = r'''"""季节与天气系统。"""

from __future__ import annotations

import random

from server.models.schemas import World

SEASONS = ["spring", "summer", "autumn", "winter"]
DAYS_PER_SEASON = 7

WEATHER_KINDS = ["clear", "rain", "fog", "snow", "storm"]

WEATHER_WEIGHTS: dict[str, dict[str, int]] = {
    "spring": {"clear": 4, "rain": 3, "fog": 1},
    "summer": {"clear": 5, "rain": 2, "storm": 1},
    "autumn": {"clear": 3, "fog": 3, "rain": 2},
    "winter": {"snow": 4, "fog": 2, "clear": 2},
}

WEATHER_DURATION_TICKS = 6


def season_for_day(day: int) -> str:
    idx = (day // DAYS_PER_SEASON) % len(SEASONS)
    return SEASONS[idx]


def _weighted_choice(weights: dict[str, int], rng: random.Random) -> str:
    total = sum(weights.values())
    r = rng.random() * total
    acc = 0.0
    for k, w in weights.items():
        acc += w
        if r <= acc:
            return k
    return next(iter(weights))


def update_weather(world: World, rng: random.Random) -> bool:
    """根据季节与时间更新天气。返回是否发生变化。"""
    new_season = season_for_day(world.day)
    season_changed = new_season != world.season
    world.season = new_season

    if world.tick - world.weather_changed_tick < WEATHER_DURATION_TICKS:
        return season_changed

    weights = WEATHER_WEIGHTS.get(world.season, {"clear": 1})
    new_weather = _weighted_choice(weights, rng)
    if new_weather != world.weather:
        world.weather = new_weather
        world.weather_changed_tick = world.tick
        return True
    world.weather_changed_tick = world.tick
    return False
'''

# ================================================================
# server/systems/social.py
# ================================================================

FILES["server/systems/social.py"] = r'''"""NPC 自主对话：同地点两人有概率交谈，产生记忆与关系变化。"""

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
    if rng.random() > 0.25:
        return None

    loc_id, group = rng.choice(candidates)
    a, b = rng.sample(group, 2)
    rel_desc = _relation_desc(a, b, session)
    loc_zh = location_label(loc_id)

    prompt = load_prompt("npc_chat.md").format(
        name_a=a.name,
        goals_a="，".join(a.goals) or "（无）",
        name_b=b.name,
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
'''

# ================================================================
# server/systems/chronicle.py
# ================================================================

FILES["server/systems/chronicle.py"] = r'''"""编年史：收集最近事件，LLM 生成长文本，存入 chronicle 表。"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlmodel import Session, select

from server.generators.base import get_llm, load_prompt
from server.models.db import ChronicleRow, EventRow, loads


def _collect_recent(session: Session, limit: int = 60) -> list[str]:
    rows = session.exec(
        select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
    ).all()
    lines: list[str] = []
    for r in reversed(rows):
        payload = loads(r.payload_json) or {}
        summary = payload.get("summary") or ""
        outcome = payload.get("outcome") or ""
        line = "- [%s] %s" % (r.template_id, summary)
        if outcome:
            line += "  →  %s" % outcome
        lines.append(line)
    return lines


def _fallback_body(events: list[str]) -> str:
    if not events:
        return "（这段时间村里风平浪静。）"
    return "近日要闻：\n" + "\n".join(events[-10:])


async def generate_chronicle(
    session: Session,
    from_tick: int = 0,
    to_tick: int = 0,
    title_hint: str = "",
) -> Optional[dict]:
    events = _collect_recent(session, limit=60)
    prompt = load_prompt("chronicle.md").format(events="\n".join(events) or "（无）")

    body = ""
    try:
        body = await get_llm().text(prompt)
    except Exception:
        body = _fallback_body(events)

    if not body.strip():
        body = _fallback_body(events)

    title = title_hint or "第 %d 天纪事" % max(1, to_tick // 24)

    row = ChronicleRow(
        id="chr_%s" % uuid.uuid4().hex[:8],
        title=title,
        body=body.strip(),
        from_tick=from_tick,
        to_tick=to_tick,
        created_at=to_tick,
    )
    session.add(row)
    session.commit()

    return {
        "id": row.id,
        "title": row.title,
        "body": row.body,
        "from_tick": row.from_tick,
        "to_tick": row.to_tick,
        "created_at": row.created_at,
    }


def list_chronicles(session: Session, limit: int = 20) -> list[dict]:
    rows = session.exec(
        select(ChronicleRow).order_by(ChronicleRow.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "body": r.body,
            "from_tick": r.from_tick,
            "to_tick": r.to_tick,
            "created_at": r.created_at,
        }
        for r in rows
    ]
'''

# ================================================================
# server/prompts/npc_chat.md
# ================================================================

FILES["server/prompts/npc_chat.md"] = r'''你是游戏里两个 NPC 对话的生成器。

**所有输出必须是简体中文，并输出为合法 JSON。**

结构：
{"topic": "话题主题（4-8 字）", "lines": [{"speaker": "名字", "text": "台词"}, ...]}

规则：
- lines 里 2 到 4 句对话，双方轮流说话
- 每句不超过 40 字
- 台词符合角色性格与目标
- speaker 必须使用真实名字（{name_a} 或 {name_b}）
- 不要输出 markdown，不要输出解释

场景：
  地点：{location}
  两人关系：{relation}

角色 A：{name_a}
  目标：{goals_a}

角色 B：{name_b}
  目标：{goals_b}
'''

# ================================================================
# server/core/tick.py
# ================================================================

FILES["server/core/tick.py"] = r'''"""时间推进。"""

from __future__ import annotations

import random

from sqlmodel import Session

from server.core import director
from server.core.world import save_world
from server.models.schemas import World
from server.systems import behavior, economy, weather


def tick(session: Session, world: World) -> None:
    rng = random.Random(world.seed * 99991 + world.tick)

    behavior.step(session, world)
    economy.settle(session, world)
    director.decay_tension(world)
    weather.update_weather(world, rng)

    world.hour += 1
    if world.hour >= 24:
        world.hour = 0
        world.day += 1
        world.social_count_today = 0
    world.tick += 1

    save_world(session, world)
'''

# ================================================================
# server/core/map_view.py
# ================================================================

FILES["server/core/map_view.py"] = r'''"""构造地图视图数据。"""

from __future__ import annotations

import math

from sqlmodel import Session, select

from server import i18n
from server.core.world import load_npcs
from server.map_layout import all_locations, all_paths, get_location
from server.models.db import EventRow, loads
from server.models.schemas import World


def _distribute_in_circle(base_x: float, base_y: float, count: int,
                          ring_radius: float = 0.035) -> list[tuple[float, float]]:
    if count <= 1:
        return [(base_x, base_y)]
    points: list[tuple[float, float]] = []
    for i in range(count):
        angle = -math.pi / 2 + (2 * math.pi * i / count)
        px = base_x + math.cos(angle) * ring_radius
        py = base_y + math.sin(angle) * ring_radius
        points.append((px, py))
    return points


def build_map_data(session: Session, world: World) -> dict:
    locations: list[dict] = []
    for loc_id, layout in all_locations().items():
        locations.append({
            "id": loc_id,
            "label": i18n.location_label(loc_id),
            "x": layout["x"], "y": layout["y"],
            "radius": layout["radius"],
            "color": layout["color"],
        })

    paths: list[dict] = []
    for a, b in all_paths():
        la = get_location(a)
        lb = get_location(b)
        paths.append({
            "from": a, "to": b,
            "from_x": la["x"], "from_y": la["y"],
            "to_x": lb["x"], "to_y": lb["y"],
        })

    npcs = load_npcs(session)
    by_loc: dict[str, list] = {}
    for npc in npcs:
        by_loc.setdefault(npc.location_id, []).append(npc)

    npc_positions: list[dict] = []
    for loc_id, group in by_loc.items():
        layout = get_location(loc_id)
        pts = _distribute_in_circle(layout["x"], layout["y"], len(group))
        for npc, (px, py) in zip(group, pts):
            npc_positions.append({
                "id": npc.id, "name": npc.name,
                "location_id": loc_id,
                "x": round(px, 4), "y": round(py, 4),
            })

    rows = session.exec(
        select(EventRow).where(EventRow.state == "active")
        .order_by(EventRow.created_at.desc()).limit(10)
    ).all()
    active_events = [
        {
            "id": r.id,
            "template_id": r.template_id,
            "template_label": i18n.template_label(r.template_id),
            "location_id": r.location_id,
            "location_label": i18n.location_label(r.location_id),
            "summary": (loads(r.payload_json) or {}).get("summary", ""),
        }
        for r in rows
    ]

    return {
        "tick": world.tick,
        "day": world.day,
        "hour": world.hour,
        "tension": world.director.tension,
        "season": world.season,
        "season_label": i18n.season_label(world.season),
        "weather": world.weather,
        "weather_label": i18n.weather_label(world.weather),
        "locations": locations,
        "paths": paths,
        "npcs": npc_positions,
        "active_events": active_events,
    }
'''

# ================================================================
# server/i18n.py
# ================================================================

FILES["server/i18n.py"] = r'''"""中文本地化字典。"""

from __future__ import annotations

TRAIT_LABELS: dict[str, str] = {
    "openness": "开放性",
    "conscientiousness": "尽责性",
    "extraversion": "外向性",
    "agreeableness": "宜人性",
    "neuroticism": "神经质",
}

NEED_LABELS: dict[str, str] = {
    "hunger": "饥饿", "safety": "安全",
    "social": "社交", "wealth": "财富", "curiosity": "好奇",
}

GENDER_LABELS: dict[str, str] = {
    "male": "男", "female": "女", "unknown": "未知",
}

SEASON_LABELS: dict[str, str] = {
    "spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬",
}

WEATHER_LABELS: dict[str, str] = {
    "clear": "晴", "rain": "雨", "fog": "雾",
    "snow": "雪", "storm": "暴风雨",
}

TEMPLATE_LABELS: dict[str, str] = {
    "missing_person": "失踪事件", "merchant_arrives": "行商到访",
    "bandit_raid": "强盗袭击", "lovers_quarrel": "恋人争吵",
    "harvest_festival": "丰收庆典", "mysterious_stranger": "神秘陌生人",
    "illness_outbreak": "疫病爆发", "treasure_rumor": "宝藏传闻",
    "political_intrigue": "权力斗争", "natural_disaster": "自然灾害",
    "traveling_bard": "流浪诗人", "lost_child": "走失的孩子",
    "wedding": "村中婚礼", "funeral": "送葬", "drought": "久旱",
    "plague_rats": "鼠患", "stolen_harvest": "收成失窃",
    "romance_blooms": "情愫暗生", "broken_promise": "背弃承诺",
    "old_letter": "旧信", "apprentice_seeks_master": "学徒求师",
    "strange_dream": "怪梦", "wolves_at_night": "狼群夜袭",
    "market_dispute": "市场争执", "found_treasure_map": "发现藏宝图",
    "poisoning_suspected": "疑似下毒", "village_election": "村长选举",
    "wandering_merchant_caravan": "商队途经", "birth_of_child": "添丁之喜",
    "execution": "公开处刑",
}

LOCATION_LABELS: dict[str, str] = {
    "village_square": "村庄广场", "market": "市场", "tavern": "酒馆",
    "home": "住处", "forest": "森林", "village_edge": "村庄边缘",
    "village_hall": "村公所",
}

REWARD_KIND_LABELS: dict[str, str] = {
    "item": "物品", "relationship": "关系", "info": "情报",
    "reputation": "声望", "skill": "技能", "story": "剧情",
}

STATE_LABELS: dict[str, str] = {
    "pending": "待触发", "active": "进行中", "awaiting_player": "等待你",
    "resolved": "已完成", "expired": "已错过", "rejected": "已拒绝",
}


def trait_label(k: str) -> str: return TRAIT_LABELS.get(k, k)
def need_label(k: str) -> str: return NEED_LABELS.get(k, k)
def gender_label(k: str) -> str: return GENDER_LABELS.get(k, k)
def season_label(k: str) -> str: return SEASON_LABELS.get(k, k)
def weather_label(k: str) -> str: return WEATHER_LABELS.get(k, k)
def template_label(k: str) -> str: return TEMPLATE_LABELS.get(k, k)
def location_label(k: str) -> str: return LOCATION_LABELS.get(k, k)
def reward_kind_label(k: str) -> str: return REWARD_KIND_LABELS.get(k, k)
def state_label(k: str) -> str: return STATE_LABELS.get(k, k)


def all_labels() -> dict[str, dict[str, str]]:
    return {
        "traits": TRAIT_LABELS, "needs": NEED_LABELS,
        "genders": GENDER_LABELS, "seasons": SEASON_LABELS,
        "weathers": WEATHER_LABELS, "templates": TEMPLATE_LABELS,
        "locations": LOCATION_LABELS, "reward_kinds": REWARD_KIND_LABELS,
        "states": STATE_LABELS,
    }
'''

# ================================================================
# server/main.py
# ================================================================

FILES["server/main.py"] = r'''"""FastAPI 入口。"""

from __future__ import annotations

import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

from server import i18n
from server.api import routes_dialogue, routes_review
from server.config import settings
from server.core import director
from server.core.event_flow import check_timeouts, resolve_event, run_event_cycle
from server.core.map_view import build_map_data
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.db.session import engine, ensure_schema
from server.models.db import EventRow, ItemRow, MemoryRow, RewardRow, dumps, loads
from server.models.schemas import Event, NPC, Reward, World
from server.systems import inventory, item_use, relationship
from server.systems.chronicle import generate_chronicle, list_chronicles
from server.systems.embedding import get_embedding, serialize
from server.systems.social import maybe_social_dialogue


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
        "version": "1.0.0",
        "docs": "/docs",
        "embedding_enabled": settings.embedding_enabled,
        "endpoints": [
            "/health", "/i18n", "/map",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/npc/{npc_id}/items", "/npc/{npc_id}/memories",
            "/event", "/event/pending", "/event/trigger",
            "/event/{event_id}/resolve",
            "/reward", "/item", "/item/{item_id}",
            "/item/{item_id}/give", "/item/{item_id}/take",
            "/item/{item_id}/use",
            "/chronicle", "/chronicle/generate",
            "/memory/backfill", "/review/latest",
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
    if not settings.embedding_enabled:
        raise HTTPException(400, "embedding not enabled")
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


@app.get("/world/state")
def world_state() -> dict:
    with get_session() as s:
        world = load_world(s)
        return {
            "id": world.id, "tick": world.tick,
            "day": world.day, "hour": world.hour, "seed": world.seed,
            "season": world.season,
            "season_label": i18n.season_label(world.season),
            "weather": world.weather,
            "weather_label": i18n.weather_label(world.weather),
            "tension": world.director.tension,
            "last_event_tick": world.director.last_event_tick,
            "total_currency": world.economy.total_currency,
        }


@app.post("/world/tick")
def world_tick() -> dict:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        save_world(s, world)
        return {
            "tick": world.tick, "day": world.day, "hour": world.hour,
            "season": world.season, "weather": world.weather,
            "tension": world.director.tension,
        }


@app.post("/world/step")
async def world_step() -> dict:
    with get_session() as s:
        world = load_world(s)
        tick(s, world)
        await check_timeouts(s, world)

        npcs = load_npcs(s)
        rng = random.Random(world.seed * 1000003 + world.tick * 7)
        social = await maybe_social_dialogue(s, world, npcs, rng)

        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)
        save_world(s, world)

        return {
            "tick": world.tick, "day": world.day, "hour": world.hour,
            "tension": world.director.tension,
            "season": world.season,
            "season_label": i18n.season_label(world.season),
            "weather": world.weather,
            "weather_label": i18n.weather_label(world.weather),
            "event": event.id if event else None,
            "event_summary": event.payload.get("summary") if event else None,
            "event_template": event.template_id if event else None,
            "template_label": i18n.template_label(event.template_id) if event else None,
            "awaiting_player": event.state == "awaiting_player" if event else False,
            "social_dialogue": social,
        }


def _npc_to_display(npc: NPC) -> dict:
    return {
        "id": npc.id, "name": npc.name, "age": npc.age,
        "gender": npc.gender,
        "gender_label": i18n.gender_label(npc.gender),
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
                "from_npc": r.from_npc, "to_npc": r.to_npc,
                "other_id": other_id,
                "other_name": npcs.get(other_id, other_id),
                "trust": r.trust, "affection": r.affection,
                "fear": r.fear, "debt": r.debt,
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
            select(MemoryRow).where(MemoryRow.npc_id == npc_id)
            .order_by(MemoryRow.timestamp.desc()).limit(limit)
        ).all()
        return [
            {
                "id": r.id, "event_id": r.event_id,
                "summary": r.summary,
                "emotion": loads(r.emotion_json) or {},
                "timestamp": r.timestamp,
                "has_embedding": bool(r.embedding_json and r.embedding_json != "[]"),
            }
            for r in rows
        ]


def _row_to_event(r: EventRow, npc_names: dict[str, str]) -> dict:
    payload = loads(r.payload_json) or {}
    participants = loads(r.participants_json) or []
    participant_names = [npc_names.get(pid, pid) for pid in participants]
    choices = payload.get("choices") or []
    interactive = bool(payload.get("interactive", True))

    return {
        "id": r.id, "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": participants, "participant_names": participant_names,
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state, "state_label": i18n.state_label(r.state),
        "awaiting_player": r.state == "awaiting_player",
        "interactive": interactive, "payload": payload,
        "summary": payload.get("summary") or "",
        "narrative": payload.get("narrative") or "",
        "choices": choices,
        "choice_made": payload.get("choice_made") or "",
        "choice_label": payload.get("choice_label") or "",
        "outcome": payload.get("outcome") or "",
        "item_id": payload.get("item_id") or "",
        "item_owner": payload.get("item_owner") or "",
        "created_at": r.created_at, "resolved_at": r.resolved_at,
    }


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()
        return [_row_to_event(r, npc_names) for r in rows]


@app.get("/event/pending")
def list_pending_events() -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow).where(EventRow.state == "awaiting_player")
            .order_by(EventRow.created_at.desc())
        ).all()
        return [_row_to_event(r, npc_names) for r in rows]


@app.post("/event/trigger")
async def trigger_event() -> dict:
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered")
        npc_names = {n.id: n.name for n in load_npcs(s)}
        row = s.get(EventRow, event.id)
        return _row_to_event(row, npc_names)


class ResolveRequest(BaseModel):
    choice_id: str


@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(event_id: str, req: ResolveRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await resolve_event(s, world, event_id, req.choice_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "resolve failed"))
        return result


# ---------- Chronicle ----------

@app.get("/chronicle")
def get_chronicles(limit: int = 20) -> list[dict]:
    with get_session() as s:
        return list_chronicles(s, limit=limit)


class ChronicleRequest(BaseModel):
    title_hint: str = ""


@app.post("/chronicle/generate")
async def make_chronicle(req: ChronicleRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        result = await generate_chronicle(
            s, from_tick=max(0, world.tick - 200),
            to_tick=world.tick, title_hint=req.title_hint,
        )
        if result is None:
            raise HTTPException(500, "chronicle generation failed")
        return result


# ---------- Reward ----------

@app.get("/reward")
def list_rewards(limit: int = 20) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(RewardRow).order_by(RewardRow.id.desc()).limit(limit)
        ).all()
        return [
            {
                "id": r.id, "event_id": r.event_id,
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
        "id": r.id, "reward_id": r.reward_id, "event_id": r.event_id,
        "name": r.name, "kind": r.kind,
        "affixes": loads(r.affixes_json) or [],
        "story": r.story, "value": r.value,
        "owner_id": owner_id, "owner_label": owner_label,
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
            s, world, item_id=item_id,
            user_id="player", target_npc_id=req.target_npc_id,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "use failed"))
        return result
'''

# ================================================================
# client/api.gd
# ================================================================

FILES["client/api.gd"] = r'''class_name GameApi
extends Node

const BASE_URL := "http://127.0.0.1:8000"

signal i18n_received(data: Dictionary)
signal world_state_received(data: Dictionary)
signal npc_list_received(data: Array)
signal npc_detail_received(data: Dictionary)
signal npc_items_received(data: Array)
signal dialogue_received(data: Dictionary)
signal event_triggered(data: Dictionary)
signal event_list_received(data: Array)
signal event_resolved(data: Dictionary)
signal relationships_received(data: Array)
signal reward_list_received(data: Array)
signal item_list_received(data: Array)
signal item_action_done(action: String, data: Dictionary)
signal map_received(data: Dictionary)
signal chronicle_list_received(data: Array)
signal chronicle_generated(data: Dictionary)
signal request_failed(endpoint: String, error: String)


func fetch_i18n() -> void: _request("GET", "/i18n", {}, "i18n_received")
func fetch_world_state() -> void: _request("GET", "/world/state", {}, "world_state_received")
func step_world() -> void: _request("POST", "/world/step", {}, "event_triggered")
func trigger_event() -> void: _request("POST", "/event/trigger", {}, "event_triggered")
func fetch_npcs() -> void: _request("GET", "/npc", {}, "npc_list_received")
func fetch_npc_detail(npc_id: String) -> void: _request("GET", "/npc/%s" % npc_id, {}, "npc_detail_received")
func fetch_relationships(npc_id: String) -> void: _request("GET", "/npc/%s/relationships" % npc_id, {}, "relationships_received")
func fetch_npc_items(npc_id: String) -> void: _request("GET", "/npc/%s/items" % npc_id, {}, "npc_items_received")
func send_dialogue(npc_id: String, player_input: String) -> void:
	_request("POST", "/npc/%s/dialogue" % npc_id, {"player_input": player_input}, "dialogue_received")
func fetch_events(limit: int = 20) -> void: _request("GET", "/event?limit=%d" % limit, {}, "event_list_received")
func fetch_rewards(limit: int = 20) -> void: _request("GET", "/reward?limit=%d" % limit, {}, "reward_list_received")
func fetch_items(limit: int = 100) -> void: _request("GET", "/item?limit=%d" % limit, {}, "item_list_received")
func fetch_map() -> void: _request("GET", "/map", {}, "map_received")
func fetch_chronicles(limit: int = 20) -> void: _request("GET", "/chronicle?limit=%d" % limit, {}, "chronicle_list_received")
func generate_chronicle(title_hint: String = "") -> void:
	_request("POST", "/chronicle/generate", {"title_hint": title_hint}, "chronicle_generated")
func take_item(item_id: String) -> void: _item_request("POST", "/item/%s/take" % item_id, {}, "take")
func drop_item(item_id: String) -> void: _item_request("POST", "/item/%s/drop" % item_id, {}, "drop")
func give_item(item_id: String, owner_id: String) -> void:
	_item_request("POST", "/item/%s/give" % item_id, {"owner_id": owner_id}, "give")
func use_item(item_id: String, target_npc_id: String) -> void:
	_item_request("POST", "/item/%s/use" % item_id, {"target_npc_id": target_npc_id}, "use")
func resolve_event(event_id: String, choice_id: String) -> void:
	_request("POST", "/event/%s/resolve" % event_id, {"choice_id": choice_id}, "event_resolved")


func _item_request(method: String, path: String, body: Dictionary, action_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)
	http.request_completed.connect(_on_item_response.bind(http, action_name))
	var url := BASE_URL + path
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err: int
	if method == "GET":
		err = http.request(url, headers, HTTPClient.METHOD_GET)
	else:
		err = http.request(url, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		request_failed.emit(action_name, "request failed: %d" % err)


func _on_item_response(
	result: int, response_code: int,
	_headers: PackedStringArray, body: PackedByteArray,
	http: HTTPRequest, action_name: String
) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(action_name, "transport error")
		return
	var text := body.get_string_from_utf8()
	var data: Variant = JSON.parse_string(text)
	if response_code < 200 or response_code >= 300:
		var msg := "HTTP %d" % response_code
		if data is Dictionary and data.has("detail"):
			msg += ": " + str(data["detail"])
		request_failed.emit(action_name, msg)
		return
	item_action_done.emit(action_name, data if data is Dictionary else {})


func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)
	http.request_completed.connect(_on_response.bind(http, signal_name))
	var url := BASE_URL + path
	var headers := PackedStringArray([
		"Content-Type: application/json",
		"Accept: application/json",
	])
	var err: int
	if method == "GET":
		err = http.request(url, headers, HTTPClient.METHOD_GET)
	else:
		err = http.request(url, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		request_failed.emit(signal_name, "request failed: %d" % err)


func _on_response(
	result: int, response_code: int,
	_headers: PackedStringArray, body: PackedByteArray,
	http: HTTPRequest, signal_name: String
) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(signal_name, "transport error: %d" % result)
		return
	var text := body.get_string_from_utf8()
	var data: Variant = JSON.parse_string(text)
	if response_code < 200 or response_code >= 300:
		var msg := "HTTP %d" % response_code
		if data is Dictionary and data.has("detail"):
			msg += ": " + str(data["detail"])
		request_failed.emit(signal_name, msg)
		return
	if data == null:
		request_failed.emit(signal_name, "JSON parse failed")
		return
	emit_signal(signal_name, data)
'''

# ================================================================
# client/map_view.gd
# ================================================================

FILES["client/map_view.gd"] = r'''class_name MapView
extends Control

var locations: Array = []
var paths: Array = []
var npcs: Array = []
var active_events: Array = []
var world_hour: int = 12
var world_day: int = 0
var season: String = "spring"
var weather: String = "clear"

var hovered_npc_id: String = ""
var selected_npc_id: String = ""

signal npc_clicked(npc_id: String)

const MARGIN := 20.0
const NPC_DOT_RADIUS := 5.0
const NPC_HOVER_RADIUS := 11.0
const BG_SPRING := Color("#1f2a1f")
const BG_SUMMER := Color("#243321")
const BG_AUTUMN := Color("#33291f")
const BG_WINTER := Color("#232b35")
const BG_NIGHT := Color("#0d1220")
const BORDER_COLOR := Color("#3a5a3a")
const GRID_COLOR := Color(1, 1, 1, 0.05)
const PATH_COLOR := Color(0.65, 0.55, 0.35, 0.55)
const PATH_WIDTH := 2.0
const MOVE_DURATION := 0.75

var _npc_animations: Dictionary = {}
var font: Font
var font_size := 12
var _weather_t: float = 0.0


func _ready() -> void:
	font = ThemeDB.fallback_font
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_exited.connect(_on_mouse_exited)
	set_process(true)


func set_data(data: Dictionary) -> void:
	var new_npcs: Array = data.get("npcs", [])
	_sync_npc_animations(new_npcs)
	locations = data.get("locations", [])
	paths = data.get("paths", [])
	npcs = new_npcs
	active_events = data.get("active_events", [])
	world_hour = int(data.get("hour", 12))
	world_day = int(data.get("day", 0))
	season = str(data.get("season", "spring"))
	weather = str(data.get("weather", "clear"))
	queue_redraw()


func set_selected(npc_id: String) -> void:
	selected_npc_id = npc_id
	queue_redraw()


func _sync_npc_animations(new_npcs: Array) -> void:
	var next_anim: Dictionary = {}
	for npc in new_npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		var to_x := float(npc.get("x", 0.5))
		var to_y := float(npc.get("y", 0.5))
		if _npc_animations.has(npc_id):
			var prev: Dictionary = _npc_animations[npc_id]
			var cur_x := float(prev.get("current_x", to_x))
			var cur_y := float(prev.get("current_y", to_y))
			var old_to_x := float(prev.get("to_x", to_x))
			var old_to_y := float(prev.get("to_y", to_y))
			if abs(to_x - old_to_x) > 0.001 or abs(to_y - old_to_y) > 0.001:
				next_anim[npc_id] = {
					"from_x": cur_x, "from_y": cur_y,
					"to_x": to_x, "to_y": to_y,
					"current_x": cur_x, "current_y": cur_y, "t": 0.0,
				}
			else:
				next_anim[npc_id] = prev
		else:
			next_anim[npc_id] = {
				"from_x": to_x, "from_y": to_y,
				"to_x": to_x, "to_y": to_y,
				"current_x": to_x, "current_y": to_y, "t": 1.0,
			}
	_npc_animations = next_anim


func _process(delta: float) -> void:
	_weather_t += delta
	var needs_redraw := false
	for npc_id in _npc_animations.keys():
		var anim: Dictionary = _npc_animations[npc_id]
		if float(anim["t"]) >= 1.0:
			continue
		var t: float = min(1.0, float(anim["t"]) + delta / MOVE_DURATION)
		anim["t"] = t
		var e: float = t * t * (3.0 - 2.0 * t)
		anim["current_x"] = lerp(float(anim["from_x"]), float(anim["to_x"]), e)
		anim["current_y"] = lerp(float(anim["from_y"]), float(anim["to_y"]), e)
		needs_redraw = true
	# 天气动画始终重绘
	if weather != "clear" and weather != "fog":
		needs_redraw = true
	if needs_redraw:
		queue_redraw()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_update_hover(event.position)
	elif event is InputEventMouseButton:
		if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_update_hover(event.position)
			if hovered_npc_id != "":
				npc_clicked.emit(hovered_npc_id)


func _on_mouse_exited() -> void:
	hovered_npc_id = ""
	queue_redraw()


func _update_hover(mouse_pos: Vector2) -> void:
	var canvas_rect := _canvas_rect()
	var closest_id := ""
	var closest_dist := NPC_HOVER_RADIUS
	for npc in npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		var p := _npc_screen_pos(npc_id, canvas_rect)
		var d := p.distance_to(mouse_pos)
		if d < closest_dist:
			closest_dist = d
			closest_id = npc_id
	if closest_id != hovered_npc_id:
		hovered_npc_id = closest_id
		queue_redraw()


func _canvas_rect() -> Rect2:
	var w := size.x - MARGIN * 2
	var h := size.y - MARGIN * 2
	return Rect2(MARGIN, MARGIN, w, h)


func _norm_to_screen(nx: float, ny: float, rect: Rect2) -> Vector2:
	return Vector2(rect.position.x + nx * rect.size.x, rect.position.y + ny * rect.size.y)


func _npc_screen_pos(npc_id: String, rect: Rect2) -> Vector2:
	if _npc_animations.has(npc_id):
		var anim: Dictionary = _npc_animations[npc_id]
		return _norm_to_screen(float(anim["current_x"]), float(anim["current_y"]), rect)
	for npc in npcs:
		if str(npc.get("id", "")) == npc_id:
			return _norm_to_screen(float(npc.get("x", 0.5)), float(npc.get("y", 0.5)), rect)
	return Vector2.ZERO


func _ambient_overlay() -> Color:
	var h := world_hour
	if h >= 6 and h < 8:
		var t := float(h - 6) / 2.0
		return Color(1.0, 0.55, 0.3, 0.35 * (1.0 - t))
	elif h >= 8 and h < 17:
		return Color(0, 0, 0, 0)
	elif h >= 17 and h < 20:
		var t := float(h - 17) / 3.0
		return Color(1.0, 0.45, 0.2, 0.4 * t)
	else:
		return Color(0.08, 0.12, 0.32, 0.55)


func _bg_color() -> Color:
	var base := BG_SPRING
	if season == "summer":
		base = BG_SUMMER
	elif season == "autumn":
		base = BG_AUTUMN
	elif season == "winter":
		base = BG_WINTER
	var overlay := _ambient_overlay()
	return base.lerp(BG_NIGHT, overlay.a * 1.4)


func _draw() -> void:
	var rect := _canvas_rect()
	draw_rect(rect, _bg_color(), true)

	# 网格
	var grid_step := rect.size.x / 10.0
	var x := rect.position.x
	while x <= rect.position.x + rect.size.x:
		draw_line(Vector2(x, rect.position.y), Vector2(x, rect.position.y + rect.size.y), GRID_COLOR, 1.0)
		x += grid_step
	var y := rect.position.y
	while y <= rect.position.y + rect.size.y:
		draw_line(Vector2(rect.position.x, y), Vector2(rect.position.x + rect.size.x, y), GRID_COLOR, 1.0)
		y += grid_step

	# 道路
	for p in paths:
		if not p is Dictionary:
			continue
		var a := _norm_to_screen(float(p.get("from_x", 0.0)), float(p.get("from_y", 0.0)), rect)
		var b := _norm_to_screen(float(p.get("to_x", 0.0)), float(p.get("to_y", 0.0)), rect)
		draw_line(a, b, Color(PATH_COLOR.r, PATH_COLOR.g, PATH_COLOR.b, 0.15), PATH_WIDTH + 3.0)
		draw_line(a, b, PATH_COLOR, PATH_WIDTH)

	# 地点
	for loc in locations:
		if not loc is Dictionary:
			continue
		var lx := float(loc.get("x", 0.5))
		var ly := float(loc.get("y", 0.5))
		var radius := float(loc.get("radius", 0.05))
		var center := _norm_to_screen(lx, ly, rect)
		var px_radius := radius * rect.size.x
		var base_color := _parse_color(str(loc.get("color", "#888888")))
		draw_circle(center, px_radius, Color(base_color.r, base_color.g, base_color.b, 0.22))
		draw_arc(center, px_radius, 0.0, TAU, 48, base_color, 1.6, true)

	# 活跃事件
	for ev in active_events:
		if not ev is Dictionary:
			continue
		var loc_id := str(ev.get("location_id", ""))
		for loc in locations:
			if str(loc.get("id", "")) == loc_id:
				var center := _norm_to_screen(float(loc.get("x", 0.5)), float(loc.get("y", 0.5)), rect)
				var radius := float(loc.get("radius", 0.05)) * rect.size.x + 6
				draw_arc(center, radius, 0.0, TAU, 64, Color(1.0, 0.8, 0.3, 0.75), 2.2, true)
				break

	# NPC
	for npc in npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		var p := _npc_screen_pos(npc_id, rect)
		var fill_color := Color(0.9, 0.9, 0.98, 0.95)
		var outline_color := Color(0.1, 0.1, 0.15, 1.0)
		if npc_id == selected_npc_id:
			fill_color = Color(1.0, 0.9, 0.3, 1.0)
			outline_color = Color(0.5, 0.35, 0.0, 1.0)
			draw_circle(p, NPC_DOT_RADIUS + 3.0, Color(1.0, 0.9, 0.3, 0.25))
		elif npc_id == hovered_npc_id:
			fill_color = Color(0.7, 1.0, 1.0, 1.0)
			outline_color = Color(0.2, 0.5, 0.6, 1.0)
		draw_circle(p, NPC_DOT_RADIUS, fill_color)
		draw_arc(p, NPC_DOT_RADIUS, 0.0, TAU, 24, outline_color, 1.5, true)

	# 环境光
	draw_rect(rect, _ambient_overlay(), true)

	# 天气层
	_draw_weather(rect)

	# 文字层
	for loc in locations:
		if not loc is Dictionary:
			continue
		var center := _norm_to_screen(float(loc.get("x", 0.5)), float(loc.get("y", 0.5)), rect)
		var px_radius := float(loc.get("radius", 0.05)) * rect.size.x
		var label: String = str(loc.get("label", loc.get("id", "")))
		var text_pos := Vector2(center.x - _text_width(label, font_size) / 2.0, center.y - px_radius - 6)
		draw_string(font, text_pos + Vector2(1, 1), label,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0, 0, 0, 0.75))
		draw_string(font, text_pos, label,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.95, 0.95, 0.9))

	for npc in npcs:
		if not npc is Dictionary:
			continue
		var npc_id := str(npc.get("id", ""))
		if npc_id != hovered_npc_id and npc_id != selected_npc_id:
			continue
		var p := _npc_screen_pos(npc_id, rect)
		var name: String = str(npc.get("name", "?"))
		var tw := _text_width(name, font_size)
		var bg_rect := Rect2(p.x - tw / 2.0 - 5, p.y - NPC_DOT_RADIUS - 22, tw + 10, 17)
		draw_rect(bg_rect, Color(0, 0, 0, 0.8), true)
		draw_string(font, Vector2(bg_rect.position.x + 5, bg_rect.position.y + 13),
			name, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 1, 1))


func _draw_weather(rect: Rect2) -> void:
	if weather == "clear":
		return
	if weather == "rain":
		draw_rect(rect, Color(0.3, 0.4, 0.7, 0.18), true)
		var count := 80
		for i in range(count):
			var seed_x := fmod(float(i) * 53.7, rect.size.x)
			var seed_y := fmod(float(i) * 91.3 + _weather_t * 600.0, rect.size.y)
			var px := rect.position.x + seed_x
			var py := rect.position.y + seed_y
			draw_line(Vector2(px, py), Vector2(px - 3.0, py + 12.0), Color(0.7, 0.8, 1.0, 0.5), 1.0)
	elif weather == "fog":
		draw_rect(rect, Color(0.75, 0.75, 0.8, 0.35), true)
	elif weather == "snow":
		draw_rect(rect, Color(0.85, 0.9, 1.0, 0.12), true)
		var count := 100
		for i in range(count):
			var px := rect.position.x + fmod(float(i) * 37.1 + sin(_weather_t + float(i)) * 15.0, rect.size.x)
			var py := rect.position.y + fmod(float(i) * 73.9 + _weather_t * 40.0, rect.size.y)
			draw_circle(Vector2(px, py), 1.8, Color(1, 1, 1, 0.75))
	elif weather == "storm":
		draw_rect(rect, Color(0.15, 0.2, 0.35, 0.30), true)
		var count := 120
		for i in range(count):
			var px := rect.position.x + fmod(float(i) * 61.3, rect.size.x)
			var py := rect.position.y + fmod(float(i) * 89.7 + _weather_t * 900.0, rect.size.y)
			draw_line(Vector2(px, py), Vector2(px - 5.0, py + 16.0), Color(0.7, 0.8, 1.0, 0.6), 1.2)
		# 闪电
		if fmod(_weather_t, 4.0) < 0.12:
			draw_rect(rect, Color(1, 1, 1, 0.35), true)


func _parse_color(hex_str: String) -> Color:
	var s := hex_str.strip_edges()
	if s.begins_with("#"):
		s = s.substr(1)
	if s.length() == 6:
		var r := ("0x" + s.substr(0, 2)).hex_to_int()
		var g := ("0x" + s.substr(2, 2)).hex_to_int()
		var b := ("0x" + s.substr(4, 2)).hex_to_int()
		return Color(r / 255.0, g / 255.0, b / 255.0, 1.0)
	return Color(0.5, 0.5, 0.5, 1.0)


func _text_width(text: String, size_px: int) -> float:
	return font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x
'''

# ================================================================
# client/main.gd
# ================================================================

FILES["client/main.gd"] = r'''extends Control

var api: GameApi

var i18n_traits: Dictionary = {}
var i18n_needs: Dictionary = {}
var i18n_templates: Dictionary = {}
var i18n_locations: Dictionary = {}
var i18n_reward_kinds: Dictionary = {}
var i18n_states: Dictionary = {}
var i18n_seasons: Dictionary = {}
var i18n_weathers: Dictionary = {}

var status_label: Label
var loading_label: Label
var npc_list: ItemList
var npc_detail: RichTextLabel
var npc_items_label: RichTextLabel
var relationship_label: RichTextLabel
var dialogue_log: RichTextLabel
var dialogue_input: LineEdit
var event_log: RichTextLabel
var event_action_panel: VBoxContainer
var reward_log: RichTextLabel
var item_list: ItemList
var item_detail: RichTextLabel
var use_btn: Button
var give_btn: Button
var take_btn: Button
var drop_btn: Button
var map_view: MapView
var chronicle_log: RichTextLabel
var chronicle_title_input: LineEdit

var trigger_btn: Button
var step_btn: Button
var step24_btn: Button
var refresh_btn: Button
var loading_timer: Timer
var loading_started_ms: int = 0
var loading_message: String = ""
var is_step_24_running: bool = false
var step_24_done: int = 0

var current_npc_id: String = ""
var current_event_id: String = ""
var npc_data: Dictionary = {}
var npc_order: Array[String] = []
var pending_events_by_id: Dictionary = {}

var items: Array = []
var item_order: Array[String] = []
var current_item_id: String = ""

var map_poll_timer: Timer


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	api.fetch_i18n()

	map_poll_timer = Timer.new()
	map_poll_timer.wait_time = 1.2
	map_poll_timer.autostart = true
	map_poll_timer.timeout.connect(func(): api.fetch_map())
	add_child(map_poll_timer)


func _connect_signals() -> void:
	api.i18n_received.connect(_on_i18n_received)
	api.world_state_received.connect(_on_world_state)
	api.npc_list_received.connect(_on_npc_list)
	api.npc_detail_received.connect(_on_npc_detail)
	api.npc_items_received.connect(_on_npc_items)
	api.dialogue_received.connect(_on_dialogue)
	api.event_triggered.connect(_on_event_triggered)
	api.event_list_received.connect(_on_event_list)
	api.event_resolved.connect(_on_event_resolved)
	api.relationships_received.connect(_on_relationships)
	api.reward_list_received.connect(_on_reward_list)
	api.item_list_received.connect(_on_item_list)
	api.item_action_done.connect(_on_item_action_done)
	api.map_received.connect(_on_map_received)
	api.chronicle_list_received.connect(_on_chronicle_list)
	api.chronicle_generated.connect(_on_chronicle_generated)
	api.request_failed.connect(_on_request_failed)


func _safe_str(v) -> String:
	if v == null:
		return ""
	return str(v)


func _build_ui() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	add_child(margin)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 8)
	margin.add_child(root)

	_build_top_bar(root)

	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_theme_constant_override("separation", 8)
	root.add_child(split)

	_build_left_panel(split)
	_build_middle_panel(split)
	_build_right_panel(split)


func _build_top_bar(root: VBoxContainer) -> void:
	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 12)
	root.add_child(top)

	status_label = Label.new()
	status_label.text = "加载中..."
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(status_label)

	loading_label = Label.new()
	loading_label.text = ""
	loading_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	top.add_child(loading_label)

	step_btn = Button.new()
	step_btn.text = "推进一 tick"
	step_btn.pressed.connect(_on_step_once)
	top.add_child(step_btn)

	step24_btn = Button.new()
	step24_btn.text = "推进 24 tick"
	step24_btn.pressed.connect(_on_step_24)
	top.add_child(step24_btn)

	trigger_btn = Button.new()
	trigger_btn.text = "触发事件"
	trigger_btn.pressed.connect(_on_trigger_event)
	top.add_child(trigger_btn)

	refresh_btn = Button.new()
	refresh_btn.text = "刷新"
	refresh_btn.pressed.connect(_refresh_all)
	top.add_child(refresh_btn)

	loading_timer = Timer.new()
	loading_timer.wait_time = 0.5
	loading_timer.autostart = false
	loading_timer.timeout.connect(_on_loading_tick)
	add_child(loading_timer)


func _set_loading(msg: String) -> void:
	loading_message = msg
	if msg == "":
		loading_label.text = ""
		loading_timer.stop()
		trigger_btn.disabled = false
		step_btn.disabled = false
		step24_btn.disabled = false
		refresh_btn.disabled = false
	else:
		loading_started_ms = Time.get_ticks_msec()
		loading_label.text = "⏳ " + msg + " (0.0s)"
		loading_timer.start()
		trigger_btn.disabled = true
		step_btn.disabled = true
		if not is_step_24_running:
			step24_btn.disabled = true
		refresh_btn.disabled = true


func _on_loading_tick() -> void:
	if loading_message == "":
		loading_timer.stop()
		return
	var elapsed := (Time.get_ticks_msec() - loading_started_ms) / 1000.0
	loading_label.text = "⏳ %s (%.1fs)" % [loading_message, elapsed]


func _on_step_once() -> void:
	_set_loading("正在推进...")
	api.step_world()


func _on_trigger_event() -> void:
	_set_loading("正在生成事件（调用 LLM，请稍候）...")
	api.trigger_event()


func _on_step_24() -> void:
	is_step_24_running = true
	step_24_done = 0
	step24_btn.disabled = true
	_set_loading("推进 24 tick (0/24)")
	_step_24_recursive(24)


func _step_24_recursive(remaining: int) -> void:
	if remaining <= 0:
		is_step_24_running = false
		step_24_done = 0
		_set_loading("")
		_refresh_all()
		return
	api.step_world()
	await get_tree().create_timer(0.3).timeout
	_step_24_recursive(remaining - 1)


func _build_left_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(240, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var title := Label.new()
	title.text = "居民"
	panel.add_child(title)

	npc_list = ItemList.new()
	npc_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	npc_list.item_selected.connect(_on_npc_selected)
	panel.add_child(npc_list)


func _build_middle_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(500, 0)
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(panel)

	var tabs := TabContainer.new()
	tabs.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(tabs)

	# 地图
	var map_tab := VBoxContainer.new()
	map_tab.name = "地图"
	tabs.add_child(map_tab)
	map_view = MapView.new()
	map_view.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_view.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_view.npc_clicked.connect(_on_map_npc_clicked)
	map_tab.add_child(map_view)

	# 档案
	var profile_tab := VBoxContainer.new()
	profile_tab.name = "档案"
	profile_tab.add_theme_constant_override("separation", 6)
	tabs.add_child(profile_tab)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 160)
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	profile_tab.add_child(detail_scroll)

	npc_detail = RichTextLabel.new()
	npc_detail.bbcode_enabled = true
	npc_detail.fit_content = true
	npc_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	npc_detail.text = "从左侧选择一位居民"
	detail_scroll.add_child(npc_detail)

	npc_items_label = RichTextLabel.new()
	npc_items_label.bbcode_enabled = true
	npc_items_label.fit_content = true
	npc_items_label.custom_minimum_size = Vector2(0, 60)
	profile_tab.add_child(npc_items_label)

	relationship_label = RichTextLabel.new()
	relationship_label.bbcode_enabled = true
	relationship_label.fit_content = true
	relationship_label.custom_minimum_size = Vector2(0, 60)
	profile_tab.add_child(relationship_label)

	var dlg_title := Label.new()
	dlg_title.text = "对话"
	profile_tab.add_child(dlg_title)

	var dlg_scroll := ScrollContainer.new()
	dlg_scroll.custom_minimum_size = Vector2(0, 120)
	dlg_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	profile_tab.add_child(dlg_scroll)

	dialogue_log = RichTextLabel.new()
	dialogue_log.bbcode_enabled = true
	dialogue_log.fit_content = true
	dialogue_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dlg_scroll.add_child(dialogue_log)

	var dlg_input_row := HBoxContainer.new()
	dlg_input_row.add_theme_constant_override("separation", 6)
	profile_tab.add_child(dlg_input_row)

	dialogue_input = LineEdit.new()
	dialogue_input.placeholder_text = "说点什么..."
	dialogue_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dialogue_input.text_submitted.connect(_on_dialogue_submit)
	dlg_input_row.add_child(dialogue_input)

	var send_btn := Button.new()
	send_btn.text = "发送"
	send_btn.pressed.connect(func(): _on_dialogue_submit(dialogue_input.text))
	dlg_input_row.add_child(send_btn)


func _build_right_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(420, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var tabs := TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(tabs)

	# 编年史
	var ev_tab := VBoxContainer.new()
	ev_tab.name = "编年史"
	ev_tab.add_theme_constant_override("separation", 6)
	tabs.add_child(ev_tab)

	var ev_scroll := ScrollContainer.new()
	ev_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	ev_tab.add_child(ev_scroll)

	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	event_log.meta_clicked.connect(_on_event_meta_clicked)
	ev_scroll.add_child(event_log)

	event_action_panel = VBoxContainer.new()
	event_action_panel.add_theme_constant_override("separation", 4)
	ev_tab.add_child(event_action_panel)

	# 史册
	var chr_tab := VBoxContainer.new()
	chr_tab.name = "史册"
	chr_tab.add_theme_constant_override("separation", 6)
	tabs.add_child(chr_tab)

	var chr_scroll := ScrollContainer.new()
	chr_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	chr_tab.add_child(chr_scroll)

	chronicle_log = RichTextLabel.new()
	chronicle_log.bbcode_enabled = true
	chronicle_log.fit_content = true
	chronicle_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chr_scroll.add_child(chronicle_log)

	var chr_ctrl := HBoxContainer.new()
	chr_ctrl.add_theme_constant_override("separation", 6)
	chr_tab.add_child(chr_ctrl)

	chronicle_title_input = LineEdit.new()
	chronicle_title_input.placeholder_text = "标题（可空）"
	chronicle_title_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chr_ctrl.add_child(chronicle_title_input)

	var chr_btn := Button.new()
	chr_btn.text = "生成史册"
	chr_btn.pressed.connect(_on_generate_chronicle)
	chr_ctrl.add_child(chr_btn)

	# 奖励
	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.name = "奖励"
	tabs.add_child(rwd_scroll)
	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)

	# 物品
	var item_tab := VBoxContainer.new()
	item_tab.name = "物品"
	item_tab.add_theme_constant_override("separation", 6)
	tabs.add_child(item_tab)

	item_list = ItemList.new()
	item_list.custom_minimum_size = Vector2(0, 200)
	item_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	item_list.item_selected.connect(_on_item_selected)
	item_tab.add_child(item_list)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 140)
	item_tab.add_child(detail_scroll)

	item_detail = RichTextLabel.new()
	item_detail.bbcode_enabled = true
	item_detail.fit_content = true
	item_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	item_detail.text = "选中一件物品查看详情"
	detail_scroll.add_child(item_detail)

	var item_buttons := HBoxContainer.new()
	item_buttons.add_theme_constant_override("separation", 6)
	item_tab.add_child(item_buttons)

	use_btn = Button.new()
	use_btn.text = "使用"
	use_btn.pressed.connect(_on_use_pressed)
	item_buttons.add_child(use_btn)

	give_btn = Button.new()
	give_btn.text = "给予"
	give_btn.pressed.connect(_on_give_pressed)
	item_buttons.add_child(give_btn)

	take_btn = Button.new()
	take_btn.text = "拿回"
	take_btn.pressed.connect(_on_take_pressed)
	item_buttons.add_child(take_btn)

	drop_btn = Button.new()
	drop_btn.text = "丢弃"
	drop_btn.pressed.connect(_on_drop_pressed)
	item_buttons.add_child(drop_btn)

	_set_item_buttons_enabled(false)


func _set_item_buttons_enabled(enabled: bool) -> void:
	if not enabled:
		use_btn.disabled = true
		give_btn.disabled = true
		take_btn.disabled = true
		drop_btn.disabled = true


func _refresh_all() -> void:
	api.fetch_world_state()
	api.fetch_npcs()
	api.fetch_events(20)
	api.fetch_rewards(20)
	api.fetch_items(100)
	api.fetch_map()
	api.fetch_chronicles(10)


func _on_i18n_received(data: Dictionary) -> void:
	i18n_traits = data.get("traits", {})
	i18n_needs = data.get("needs", {})
	i18n_templates = data.get("templates", {})
	i18n_locations = data.get("locations", {})
	i18n_reward_kinds = data.get("reward_kinds", {})
	i18n_states = data.get("states", {})
	i18n_seasons = data.get("seasons", {})
	i18n_weathers = data.get("weathers", {})
	_refresh_all()


func _on_world_state(data: Dictionary) -> void:
	var season_zh: String = str(data.get("season_label", ""))
	var weather_zh: String = str(data.get("weather_label", ""))
	status_label.text = "第 %d 天  %02d:00   %s · %s   Tick %d   张力 %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		season_zh, weather_zh,
		int(data.get("tick", 0)),
		float(data.get("tension", 0.0)),
	]


func _on_map_received(data: Dictionary) -> void:
	if map_view:
		map_view.set_data(data)
		map_view.set_selected(current_npc_id)


func _on_map_npc_clicked(npc_id: String) -> void:
	for i in range(npc_order.size()):
		if npc_order[i] == npc_id:
			npc_list.select(i)
			_on_npc_selected(i)
			break


func _on_npc_list(data: Array) -> void:
	npc_data.clear()
	npc_order.clear()
	npc_list.clear()
	for npc in data:
		if not npc is Dictionary:
			continue
		var id: String = str(npc.get("id", ""))
		var name: String = str(npc.get("name", "?"))
		var gz: String = str(npc.get("gender_label", ""))
		var loc: String = str(npc.get("location_label", ""))
		npc_data[id] = npc
		npc_order.append(id)
		npc_list.add_item("%s %s @ %s" % [name, gz, loc])


func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	api.fetch_npc_items(current_npc_id)
	if map_view:
		map_view.set_selected(current_npc_id)
	var name: String = str(npc_data[current_npc_id].get("name", "?"))
	dialogue_log.text = "[i]你走近 %s...[/i]" % name


func _on_npc_detail(data: Dictionary) -> void:
	var lines: Array[String] = []
	var gender_zh: String = str(data.get("gender_label", ""))
	if gender_zh == "":
		gender_zh = "未知"
	lines.append("[b][color=yellow]%s[/color][/b]   %s   %d 岁" % [
		str(data.get("name", "?")), gender_zh, int(data.get("age", 0)),
	])
	lines.append("所在地：%s" % str(data.get("location_label", "")))
	lines.append("")
	lines.append("[b]性格[/b]")
	for t in data.get("traits", []):
		if t is Dictionary:
			lines.append("   %s：%.2f" % [str(t.get("label", "?")), float(t.get("value", 0))])
	lines.append("")
	lines.append("[b]需求[/b]")
	for n in data.get("needs", []):
		if n is Dictionary:
			lines.append("   %s：%.2f" % [str(n.get("label", "?")), float(n.get("value", 0))])
	lines.append("")
	lines.append("[b]目标[/b]")
	for g in data.get("goals", []):
		lines.append("   · %s" % str(g))
	npc_detail.text = "\n".join(lines)


func _on_npc_items(data: Array) -> void:
	if data.is_empty():
		npc_items_label.text = "[b]持有物[/b]\n   （空）"
		return
	var lines: Array[String] = ["[b]持有物[/b]"]
	for it in data:
		if it is Dictionary:
			lines.append("   · %s（%s）" % [
				str(it.get("name", "?")), str(it.get("kind", "")),
			])
	npc_items_label.text = "\n".join(lines)


func _on_relationships(data: Array) -> void:
	if data.is_empty():
		relationship_label.text = "[b]关系[/b]\n   （暂无）"
		return
	var lines: Array[String] = ["[b]关系[/b]"]
	for r in data:
		if not r is Dictionary:
			continue
		lines.append("   %s  信任 %+.2f  好感 %+.2f" % [
			str(r.get("other_name", "?")),
			float(r.get("trust", 0)),
			float(r.get("affection", 0)),
		])
	relationship_label.text = "\n".join(lines)


func _on_dialogue_submit(text: String) -> void:
	text = text.strip_edges()
	if text == "" or current_npc_id == "":
		return
	dialogue_log.append_text("\n[b]你：[/b]%s" % text)
	dialogue_input.text = ""
	api.send_dialogue(current_npc_id, text)


func _on_dialogue(data: Dictionary) -> void:
	var name: String = str(data.get("npc_name", "NPC"))
	var reply: String = str(data.get("reply", ""))
	dialogue_log.append_text("\n[b][color=cyan]%s：[/color][/b]%s\n" % [name, reply])


func _on_event_triggered(data: Dictionary) -> void:
	if is_step_24_running:
		step_24_done += 1
		_set_loading("推进 24 tick (%d/24)" % step_24_done)
	else:
		_set_loading("")

	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		var tpl_label: String = str(data.get("template_label", ""))
		if summary != "":
			event_log.append_text("\n[color=orange]→[/color] [b]%s[/b] %s" % [tpl_label, summary])

	if data.has("social_dialogue") and data.get("social_dialogue") != null:
		var sd = data.get("social_dialogue")
		if sd is Dictionary:
			_render_social(sd)

	api.fetch_events(20)
	api.fetch_rewards(20)
	api.fetch_items(100)
	api.fetch_map()
	api.fetch_world_state()
	api.fetch_npcs()
	if current_npc_id != "":
		api.fetch_npc_items(current_npc_id)


func _render_social(sd: Dictionary) -> void:
	var a_name := str(sd.get("a_name", "?"))
	var b_name := str(sd.get("b_name", "?"))
	var loc := str(sd.get("location_label", ""))
	var topic := str(sd.get("topic", ""))
	var lines: Array = sd.get("lines", [])

	event_log.append_text("\n[color=cyan]·[/color] [b]%s[/b]（%s，%s，%s）\n" % [
		"闲谈", a_name, b_name, loc,
	])
	for line in lines:
		if line is Dictionary:
			event_log.append_text("    [b]%s[/b]：%s\n" % [
				str(line.get("speaker", "")), str(line.get("text", "")),
			])
	event_log.append_text("\n")


func _on_event_list(data: Array) -> void:
	event_log.clear()
	pending_events_by_id.clear()

	var awaiting: Array = []
	for e in data:
		if e is Dictionary and bool(e.get("awaiting_player", false)):
			awaiting.append(e)
			pending_events_by_id[str(e.get("id", ""))] = e

	if not awaiting.is_empty():
		event_log.append_text("[b][color=orange]=== 等待你的决定 ===[/color][/b]\n\n")
		for e in awaiting:
			_render_event_entry(e, true)
		event_log.append_text("\n[b]历史事件[/b]\n\n")

	for e in data:
		if not e is Dictionary:
			continue
		if bool(e.get("awaiting_player", false)):
			continue
		_render_event_entry(e, false)

	_refresh_event_action_panel()


func _render_event_entry(e: Dictionary, pending: bool) -> void:
	var eid: String = _safe_str(e.get("id", ""))
	var state: String = str(e.get("state", ""))
	var state_zh: String = str(e.get("state_label", state))
	var color := "white"
	if state == "resolved":
		color = "lightgreen"
	elif state == "rejected":
		color = "gray"
	elif state == "expired":
		color = "darkgray"
	elif state == "awaiting_player":
		color = "orange"

	var tpl_label: String = _safe_str(e.get("template_label", e.get("template_id", "?")))
	var loc_label: String = _safe_str(e.get("location_label", ""))
	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			ns.append(_safe_str(n))
		names_str = "（" + "、".join(ns) + "）"

	var summary: String = _safe_str(e.get("summary", ""))
	var narrative: String = _safe_str(e.get("narrative", ""))
	var outcome: String = _safe_str(e.get("outcome", ""))
	var choice_label: String = _safe_str(e.get("choice_label", ""))

	if pending:
		event_log.append_text("[color=%s]·[/color] [url=%s][b]%s[/b] %s（%s，%s）[/url]\n" % [
			color, eid, tpl_label, names_str, loc_label, state_zh,
		])
		if narrative != "":
			event_log.append_text("    [i]%s[/i]\n" % narrative)
		event_log.append_text("    [color=orange]点此做出选择[/color]\n\n")
	else:
		event_log.append_text("[color=%s]·[/color] [b]%s[/b] %s（%s，%s）\n" % [
			color, tpl_label, names_str, loc_label, state_zh,
		])
		if summary != "":
			event_log.append_text("    %s\n" % summary)
		if choice_label != "" and choice_label != "<null>":
			event_log.append_text("    [i]你的选择：%s[/i]\n" % choice_label)
		if outcome != "" and outcome != "<null>":
			event_log.append_text("    [color=lightgreen]%s[/color]\n" % outcome)
		event_log.append_text("\n")


func _on_event_meta_clicked(meta) -> void:
	var eid := str(meta)
	if eid == "" or not pending_events_by_id.has(eid):
		return
	current_event_id = eid
	_refresh_event_action_panel()


func _refresh_event_action_panel() -> void:
	if event_action_panel == null:
		return
	for child in event_action_panel.get_children():
		child.queue_free()

	if current_event_id == "" or not pending_events_by_id.has(current_event_id):
		var hint := Label.new()
		hint.text = "（点击上方橙色事件做出选择）"
		hint.add_theme_font_size_override("font_size", 12)
		event_action_panel.add_child(hint)
		return

	var e: Dictionary = pending_events_by_id[current_event_id]
	var title := Label.new()
	title.text = "你打算怎么做？ —— %s" % str(e.get("template_label", ""))
	event_action_panel.add_child(title)

	var choices: Array = e.get("choices", [])
	if choices.is_empty():
		var hint := Label.new()
		hint.text = "（此事件没有选项，稍后会自动结算）"
		event_action_panel.add_child(hint)
		return

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	event_action_panel.add_child(row)

	for c in choices:
		if not c is Dictionary:
			continue
		var btn := Button.new()
		btn.text = str(c.get("label", "?"))
		var cid := str(c.get("id", ""))
		var eid := current_event_id
		btn.pressed.connect(func(): _on_event_choice_pressed(eid, cid))
		row.add_child(btn)


func _on_event_choice_pressed(event_id: String, choice_id: String) -> void:
	_set_loading("正在结算（调用 LLM）...")
	for child in event_action_panel.get_children():
		_disable_recursive(child)
	api.resolve_event(event_id, choice_id)


func _disable_recursive(node: Node) -> void:
	if node is Button:
		(node as Button).disabled = true
	for child in node.get_children():
		_disable_recursive(child)


func _on_event_resolved(data: Dictionary) -> void:
	_set_loading("")
	current_event_id = ""
	_refresh_all()


func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	for r in data:
		if not r is Dictionary:
			continue
		var kind_label: String = str(r.get("kind_label", r.get("kind", "?")))
		reward_log.append_text("[b]%s[/b]  %.2f  %s\n" % [
			kind_label, float(r.get("value", 0)), str(r.get("description", "")),
		])


func _on_item_list(data: Array) -> void:
	items = data
	item_order.clear()
	item_list.clear()
	for it in data:
		if not it is Dictionary:
			continue
		var id: String = str(it.get("id", ""))
		var name: String = str(it.get("name", "?"))
		var kind: String = str(it.get("kind", ""))
		var owner_label: String = str(it.get("owner_label", ""))
		item_order.append(id)
		item_list.add_item("%s (%s) —— %s" % [name, kind, owner_label])
	if current_item_id != "":
		for i in range(item_order.size()):
			if item_order[i] == current_item_id:
				item_list.select(i)
				_render_item_detail(current_item_id)
				break


func _on_item_selected(index: int) -> void:
	if index < 0 or index >= item_order.size():
		return
	current_item_id = item_order[index]
	_render_item_detail(current_item_id)


func _render_item_detail(item_id: String) -> void:
	for it in items:
		if str(it.get("id", "")) != item_id:
			continue
		var name: String = str(it.get("name", "?"))
		var kind: String = str(it.get("kind", ""))
		var affixes: Array = it.get("affixes", [])
		var story: String = str(it.get("story", ""))
		var value: float = float(it.get("value", 0))
		var owner_label: String = str(it.get("owner_label", ""))

		var lines: Array[String] = []
		lines.append("[b][color=gold]%s[/color][/b]  [i](%s)[/i]" % [name, kind])
		lines.append("持有者：%s" % owner_label)
		if not affixes.is_empty():
			var affix_strs: Array[String] = []
			for a in affixes:
				affix_strs.append(str(a))
			lines.append("词缀：%s" % ", ".join(affix_strs))
		if story != "":
			lines.append("[color=lightgray]%s[/color]" % story)
		lines.append("价值：%.2f" % value)
		item_detail.text = "\n".join(lines)

		var owner_id: String = str(it.get("owner_id", ""))
		var is_player := owner_id == "player"
		var is_npc := owner_id != "" and owner_id != "player"
		use_btn.disabled = not is_player
		give_btn.disabled = not is_player
		drop_btn.disabled = not is_player
		take_btn.disabled = not is_npc
		return


func _on_item_action_done(action: String, data: Dictionary) -> void:
	if action == "use":
		var effect: String = str(data.get("effect", ""))
		var consumed: bool = bool(data.get("consumed", false))
		item_detail.append_text("\n\n[b][color=cyan]使用效果：[/color][/b]%s" % effect)
		if consumed:
			item_detail.append_text("\n[i]（物品已消耗）[/i]")
	_refresh_all()


func _on_take_pressed() -> void:
	if current_item_id != "":
		api.take_item(current_item_id)


func _on_drop_pressed() -> void:
	if current_item_id != "":
		api.drop_item(current_item_id)


func _on_give_pressed() -> void:
	if current_item_id == "":
		return
	_show_target_picker("给予给谁？", func(target_id: String):
		if target_id != "":
			api.give_item(current_item_id, target_id)
	)


func _on_use_pressed() -> void:
	if current_item_id == "":
		return
	_show_target_picker("对谁使用？（可无目标）", func(target_id: String):
		api.use_item(current_item_id, target_id)
	)


func _show_target_picker(title: String, on_confirm: Callable) -> void:
	var popup := PopupPanel.new()
	add_child(popup)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.custom_minimum_size = Vector2(280, 0)
	popup.add_child(vbox)

	var label := Label.new()
	label.text = title
	vbox.add_child(label)

	var option := OptionButton.new()
	option.add_item("（无目标）")
	for npc_id in npc_order:
		option.add_item(str(npc_data[npc_id].get("name", "?")))
	vbox.add_child(option)

	var btns := HBoxContainer.new()
	btns.add_theme_constant_override("separation", 8)
	vbox.add_child(btns)

	var ok_btn := Button.new()
	ok_btn.text = "确认"
	btns.add_child(ok_btn)

	var cancel_btn := Button.new()
	cancel_btn.text = "取消"
	btns.add_child(cancel_btn)

	ok_btn.pressed.connect(func():
		var sel := option.selected
		var target := ""
		if sel > 0 and sel - 1 < npc_order.size():
			target = npc_order[sel - 1]
		on_confirm.call(target)
		popup.queue_free()
	)
	cancel_btn.pressed.connect(func(): popup.queue_free())

	popup.popup_centered(Vector2i(300, 140))


func _on_chronicle_list(data: Array) -> void:
	chronicle_log.clear()
	if data.is_empty():
		chronicle_log.text = "[i]还没有史册。点击下方按钮生成一份。[/i]"
		return
	for c in data:
		if not c is Dictionary:
			continue
		chronicle_log.append_text("[b][color=gold]%s[/color][/b]\n" % str(c.get("title", "?")))
		chronicle_log.append_text("[color=lightgray]%s[/color]\n\n" % str(c.get("body", "")))
		chronicle_log.append_text("[i]——  记录于第 %d tick[/i]\n\n" % int(c.get("created_at", 0)))


func _on_generate_chronicle() -> void:
	var hint: String = chronicle_title_input.text.strip_edges()
	_set_loading("正在编纂史册（调用 LLM）...")
	api.generate_chronicle(hint)


func _on_chronicle_generated(data: Dictionary) -> void:
	_set_loading("")
	chronicle_title_input.text = ""
	api.fetch_chronicles(10)


func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error
	if is_step_24_running:
		is_step_24_running = false
		step_24_done = 0
	_set_loading("")
'''

# ================================================================
# tests
# ================================================================

FILES["tests/test_weather.py"] = r'''import random

from server.models.schemas import World
from server.systems import weather


def test_season_for_day_cycles():
    assert weather.season_for_day(0) == "spring"
    assert weather.season_for_day(7) == "summer"
    assert weather.season_for_day(14) == "autumn"
    assert weather.season_for_day(21) == "winter"
    assert weather.season_for_day(28) == "spring"


def test_update_weather_changes_season():
    world = World(id="w", seed=1, day=0, season="spring")
    rng = random.Random(1)
    weather.update_weather(world, rng)
    assert world.season == "spring"
    world.day = 7
    weather.update_weather(world, rng)
    assert world.season == "summer"


def test_update_weather_picks_from_season_pool():
    world = World(id="w", seed=1, day=7, season="summer", tick=100)
    world.weather_changed_tick = 0
    rng = random.Random(1)
    weather.update_weather(world, rng)
    allowed = set(weather.WEATHER_WEIGHTS["summer"].keys())
    assert world.weather in allowed
'''

FILES["tests/test_social.py"] = r'''import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_npc, save_world
from server.models.schemas import NPC
from server.systems import social


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_social_respects_daily_cap(monkeypatch):
    from server.systems import social as sm

    class FakeLLM:
        async def text_json(self, prompt):
            return {"topic": "闲聊", "lines": [
                {"speaker": "A", "text": "你好"},
                {"speaker": "B", "text": "你也好"},
            ]}

    monkeypatch.setattr(sm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 100
        world.social_count_today = social.MAX_SOCIAL_PER_DAY
        save_world(s, world)
        npcs = [NPC(id="n%d" % i, name="N%d" % i, age=20, location_id="tavern") for i in range(3)]
        for n in npcs:
            save_npc(s, n)
        result = await social.maybe_social_dialogue(s, world, npcs, random.Random(1))
        assert result is None


@pytest.mark.asyncio
async def test_social_generates_dialogue(monkeypatch):
    from server.systems import social as sm

    class FakeLLM:
        async def text_json(self, prompt):
            return {"topic": "旧事", "lines": [
                {"speaker": "A", "text": "还记得那年么"},
                {"speaker": "B", "text": "当然记得"},
            ]}

    monkeypatch.setattr(sm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=7)
        world.tick = 100
        world.social_count_today = 0
        world.last_social_tick = -999
        save_world(s, world)
        npcs = [NPC(id="n1", name="A", age=20, location_id="tavern"),
                NPC(id="n2", name="B", age=20, location_id="tavern")]
        for n in npcs:
            save_npc(s, n)
        # 用固定 rng 触发：多次尝试直到成功
        for seed in range(50):
            world.social_count_today = 0
            world.last_social_tick = -999
            result = await social.maybe_social_dialogue(s, world, npcs, random.Random(seed))
            if result is not None:
                assert "lines" in result
                assert len(result["lines"]) == 2
                return
        pytest.fail("50 次尝试都没触发 social")
'''

FILES["tests/test_chronicle.py"] = r'''import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_event, save_world
from server.models.schemas import Event
from server.systems import chronicle


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_chronicle_fallback_when_llm_fails(monkeypatch):
    from server.systems import chronicle as cm

    class FakeLLM:
        async def text(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(cm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 50
        save_world(s, world)
        for i in range(3):
            evt = Event(
                id="e%d" % i, template_id="market_dispute",
                participants=[], location_id="market",
                state="resolved", payload={"summary": "事%d" % i},
                created_at=i * 10, resolved_at=i * 10 + 1,
            )
            save_event(s, evt)

        result = await chronicle.generate_chronicle(s, from_tick=0, to_tick=50)
        assert result is not None
        assert result["body"] != ""


@pytest.mark.asyncio
async def test_chronicle_list(monkeypatch):
    from server.systems import chronicle as cm

    class FakeLLM:
        async def text(self, prompt):
            return "今日无大事。"

    monkeypatch.setattr(cm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 50
        save_world(s, world)
        await chronicle.generate_chronicle(s, 0, 50)
        await chronicle.generate_chronicle(s, 50, 100)
        rows = chronicle.list_chronicles(s, limit=10)
        assert len(rows) == 2
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()

    written = 0
    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print("[skip]  " + rel)
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print("[write] " + rel)
        written += 1

    print("\nPart 18 done. written=%d" % written)
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. uvicorn server.main:app --reload")
    print("  3. Godot 按 F5")


if __name__ == '__main__':
    main()