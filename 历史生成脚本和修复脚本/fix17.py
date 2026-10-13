"""EmergentWorld Part 17 修复（单文件版）。"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

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


def ensure_schema() -> None:
    with engine.begin() as conn:
        if not _has_column(conn, "item", "owner_id"):
            conn.execute(text(
                "ALTER TABLE item ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''"
            ))
        if not _has_column(conn, "item", "consumed"):
            conn.execute(text(
                "ALTER TABLE item ADD COLUMN consumed INTEGER NOT NULL DEFAULT 0"
            ))
        if not _has_column(conn, "memory", "embedding_json"):
            conn.execute(text(
                "ALTER TABLE memory ADD COLUMN embedding_json TEXT NOT NULL DEFAULT '[]'"
            ))
        if not _has_column(conn, "npc", "gender"):
            conn.execute(text(
                "ALTER TABLE npc ADD COLUMN gender TEXT NOT NULL DEFAULT 'unknown'"
            ))
'''

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

FILES["server/generators/npc.py"] = r'''"""NPC 生成器：LLM 生成属性 + 规则兜底。"""

from __future__ import annotations

import random
import uuid

from server.core.evaluator import evaluate_npc
from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC

TRAIT_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
NEED_KEYS = ["hunger", "safety", "social", "wealth", "curiosity"]

GENDER_ZH = {"male": "男", "female": "女", "unknown": "未知"}


def gender_zh(gender: str) -> str:
    return GENDER_ZH.get(gender, "未知")


def _default_npc(npc_id: str, seed_name: str, gender: str = "unknown") -> NPC:
    rng = random.Random(hash(npc_id) & 0xFFFF)
    traits = {k: round(rng.uniform(0.25, 0.75), 2) for k in TRAIT_KEYS}
    needs = {k: round(rng.uniform(0.3, 0.7), 2) for k in NEED_KEYS}
    return NPC(
        id=npc_id,
        name=seed_name,
        age=rng.randint(18, 55),
        gender=gender,
        traits=traits,
        needs=needs,
        goals=["安稳度日", "照顾好家人"],
        behavior_profile={k: 0.5 for k in NEED_KEYS},
        asset_params={"hair": "short", "outfit": "plain", "palette": "neutral"},
    )


async def generate_npc(
    seed_name: str,
    context: str = "",
    gender: str = "unknown",
) -> NPC:
    npc_id = "npc_%s" % uuid.uuid4().hex[:8]
    fallback = _default_npc(npc_id, seed_name, gender)

    prompt = load_prompt("npc_gen.md").format(
        name=seed_name,
        gender=gender_zh(gender),
        context=context,
    )
    npc = await get_llm().json(prompt, NPC, fallback=fallback)
    npc.id = npc_id
    npc.name = npc.name or seed_name
    if gender != "unknown":
        npc.gender = gender

    ok, _ = evaluate_npc(npc)
    if not ok:
        return fallback
    return npc
'''

FILES["server/prompts/npc_gen.md"] = r'''你是游戏 NPC 生成器。根据给定的名字与上下文，生成一个 NPC。

**重要：所有文本字段必须使用简体中文。**

规则：
- 输出必须是合法 JSON，符合 NPC Schema
- **name 必须使用给定名字**：{name}（不要改成英文）
- **gender 必须是 "male" 或 "female"**
- traits 使用大五人格：openness, conscientiousness, extraversion, agreeableness, neuroticism
- **traits 每个维度必须是 0 到 1 之间的不同数值**，不要都填 0.5
- needs 使用：hunger, safety, social, wealth, curiosity
- **goals 至少 2 条，用中文写**，一条短期，一条长期
- behavior_profile 与 needs 同键，值 0-1
- asset_params 包含 hair, outfit, palette 三个键，值用英文短词
- age 在 18 到 70 之间
- 不要输出 markdown，不要输出解释

名字：{name}
性别提示：{gender}
上下文：{context}
'''

FILES["tools/seed_world.py"] = r'''"""初始化世界：生成 NPC、加载模板、写入数据库。"""

from __future__ import annotations

import argparse
import asyncio
import random

from sqlmodel import Session, SQLModel, create_engine

from server.config import settings
from server.core.director import load_templates
from server.core.world import create_world, save_npc, save_world
from server.generators.npc import generate_npc

MALE_NAMES = [
    "张铁柱", "李大山", "王二狗", "赵石", "陈望",
    "刘长河", "孙远", "周慎", "吴越", "郑屠",
    "冯舟", "褚守", "卫风", "蒋平", "沈墨",
]
FEMALE_NAMES = [
    "李秀兰", "王桂花", "赵小梅", "陈阿娇", "刘翠",
    "孙玉", "周盼", "吴侬", "郑蓉", "冯素",
    "褚莲", "卫婵", "蒋薇", "沈烟", "秦娥",
]


def pick_name_pool(n: int, rng: random.Random) -> list[tuple[str, str]]:
    males = [("male", name) for name in MALE_NAMES]
    females = [("female", name) for name in FEMALE_NAMES]
    pool = males + females
    rng.shuffle(pool)
    return [(name, gender) for (gender, name) in pool[:n]]


async def seed(n: int, seed_value: int) -> None:
    rng = random.Random(seed_value)
    engine = create_engine(f"sqlite:///{settings.db_path}")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        world = create_world("default", seed=seed_value)
        save_world(session, world)
        picks = pick_name_pool(n, rng)
        for name, gender in picks:
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            save_npc(session, npc)
            print("created npc %s %s (%s)" % (npc.id, npc.name, npc.gender))

    templates = load_templates()
    print("loaded %d event templates" % len(templates))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npc", type=int, default=8)
    parser.add_argument("--seed", type=int, default=settings.seed)
    args = parser.parse_args()
    asyncio.run(seed(args.npc, args.seed))


if __name__ == "__main__":
    main()
'''

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
    "hunger": "饥饿",
    "safety": "安全",
    "social": "社交",
    "wealth": "财富",
    "curiosity": "好奇",
}

GENDER_LABELS: dict[str, str] = {
    "male": "男",
    "female": "女",
    "unknown": "未知",
}

TEMPLATE_LABELS: dict[str, str] = {
    "missing_person": "失踪事件",
    "merchant_arrives": "行商到访",
    "bandit_raid": "强盗袭击",
    "lovers_quarrel": "恋人争吵",
    "harvest_festival": "丰收庆典",
    "mysterious_stranger": "神秘陌生人",
    "illness_outbreak": "疫病爆发",
    "treasure_rumor": "宝藏传闻",
    "political_intrigue": "权力斗争",
    "natural_disaster": "自然灾害",
    "traveling_bard": "流浪诗人",
    "lost_child": "走失的孩子",
    "wedding": "村中婚礼",
    "funeral": "送葬",
    "drought": "久旱",
    "plague_rats": "鼠患",
    "stolen_harvest": "收成失窃",
    "romance_blooms": "情愫暗生",
    "broken_promise": "背弃承诺",
    "old_letter": "旧信",
    "apprentice_seeks_master": "学徒求师",
    "strange_dream": "怪梦",
    "wolves_at_night": "狼群夜袭",
    "market_dispute": "市场争执",
    "found_treasure_map": "发现藏宝图",
    "poisoning_suspected": "疑似下毒",
    "village_election": "村长选举",
    "wandering_merchant_caravan": "商队途经",
    "birth_of_child": "添丁之喜",
    "execution": "公开处刑",
}

LOCATION_LABELS: dict[str, str] = {
    "village_square": "村庄广场",
    "market": "市场",
    "tavern": "酒馆",
    "home": "住处",
    "forest": "森林",
    "village_edge": "村庄边缘",
    "village_hall": "村公所",
}

REWARD_KIND_LABELS: dict[str, str] = {
    "item": "物品",
    "relationship": "关系",
    "info": "情报",
    "reputation": "声望",
    "skill": "技能",
    "story": "剧情",
}

STATE_LABELS: dict[str, str] = {
    "pending": "待触发",
    "active": "进行中",
    "awaiting_player": "等待你",
    "resolved": "已完成",
    "expired": "已错过",
    "rejected": "已拒绝",
}


def trait_label(key: str) -> str:
    return TRAIT_LABELS.get(key, key)


def need_label(key: str) -> str:
    return NEED_LABELS.get(key, key)


def gender_label(key: str) -> str:
    return GENDER_LABELS.get(key, key)


def template_label(key: str) -> str:
    return TEMPLATE_LABELS.get(key, key)


def location_label(key: str) -> str:
    return LOCATION_LABELS.get(key, key)


def reward_kind_label(key: str) -> str:
    return REWARD_KIND_LABELS.get(key, key)


def state_label(key: str) -> str:
    return STATE_LABELS.get(key, key)


def all_labels() -> dict[str, dict[str, str]]:
    return {
        "traits": TRAIT_LABELS,
        "needs": NEED_LABELS,
        "genders": GENDER_LABELS,
        "templates": TEMPLATE_LABELS,
        "locations": LOCATION_LABELS,
        "reward_kinds": REWARD_KIND_LABELS,
        "states": STATE_LABELS,
    }
'''

FILES["server/core/event_flow.py"] = r'''"""事件流程：物品归属由玩家选择决定。"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session, select

from server.core import director
from server.core.choices import build_choices, get_choice_spec
from server.core.evaluator import evaluate_event, evaluate_reward, log_evaluation
from server.core.world import load_npcs, save_event, save_world
from server.generators.base import get_llm, load_prompt
from server.generators.event import fill_event
from server.generators.reward import compute_budget, generate_reward
from server.models.db import EventRow, ItemRow, RewardRow, dumps
from server.models.schemas import Event, EventTemplate, Reward, World
from server.systems import relationship

PLAYER_TIMEOUT_TICKS = 8
MAX_PENDING = 3


def _save_reward(session: Session, reward: Reward) -> None:
    row = RewardRow(
        id=reward.id,
        event_id=reward.event_id,
        kind=reward.kind,
        value=reward.value,
        description=reward.description,
        payload_json=dumps({k: v for k, v in reward.payload.items() if k != "item"}),
    )
    session.add(row)
    session.commit()


def _save_item(
    session: Session,
    reward_id: str,
    event_id: str,
    item_data: dict,
    owner_id: str,
) -> None:
    row = ItemRow(
        id=item_data["id"],
        reward_id=reward_id,
        event_id=event_id,
        name=item_data.get("name", ""),
        kind=item_data.get("kind", ""),
        affixes_json=dumps(item_data.get("affixes", [])),
        story=item_data.get("story", ""),
        value=float(item_data.get("value", 0.0)),
        owner_id=owner_id,
        consumed=False,
    )
    session.add(row)
    session.commit()


def _apply_initial_effects(
    session: Session,
    world: World,
    event: Event,
    tpl: EventTemplate,
    rng: random.Random,
) -> None:
    summary = event.payload.get("summary", "") or ("发生了 %s" % tpl.id)
    relationship.npc_effects_from_event(
        session=session,
        participants=event.participants,
        event_id=event.id,
        summary=summary,
        timestamp=world.tick,
        rng=rng,
    )
    relationship.apply_event_effects(
        session=session,
        participants=event.participants,
        tags=tpl.tags,
        rng=rng,
    )


def _pending_rows(session: Session) -> list[EventRow]:
    return list(session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all())


def _resolve_item_owner(event: Event, choice_id: str, rng: random.Random) -> str:
    if choice_id == "oppose":
        return "player"
    if choice_id == "help":
        if event.participants:
            return event.participants[0]
        return ""
    if event.participants and rng.random() < 0.8:
        return rng.choice(event.participants)
    return "player"


async def _emit_reward_and_item(
    session: Session,
    world: World,
    event: Event,
    rng: random.Random,
    value_multiplier: float = 1.0,
    owner_hint: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    budget = compute_budget(event, world) * value_multiplier
    reward = await generate_reward(event, world)
    reward.value = min(reward.value * value_multiplier, 1.0)

    reward_ok, reward_errors = evaluate_reward(reward, budget)
    log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)
    if not reward_ok:
        return None, None, None

    _save_reward(session, reward)
    reward_id = reward.id
    item_id = None
    item_owner = None

    item_data = reward.payload.get("item")
    if isinstance(item_data, dict) and item_data.get("id"):
        if owner_hint is None:
            item_owner = _resolve_item_owner(event, "observe", rng)
        else:
            item_owner = owner_hint
        _save_item(session, reward.id, event.id, item_data, item_owner)
        item_id = item_data["id"]

    return reward_id, item_id, item_owner


async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick)

    pending = _pending_rows(session)
    if len(pending) >= MAX_PENDING:
        return None

    if not force and not director.should_trigger(world, rng):
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    pending_template_ids = {r.template_id for r in pending}

    tpl = director.pick_template(
        templates, world, npcs, rng,
        ignore_cooldown=force,
        pending_template_ids=pending_template_ids,
    )
    if tpl is None:
        if pending_template_ids:
            tpl = director.pick_template(
                templates, world, npcs, rng,
                ignore_cooldown=False,
                pending_template_ids=pending_template_ids,
                want_interactive=False,
            )
        if tpl is None:
            return None

    event = await fill_event(tpl, world, npcs, rng)
    event.payload["interactive"] = bool(tpl.interactive)

    npc_ids = {n.id for n in npcs}
    max_reward = float(tpl.evaluator.get("max_reward", 1.0)) if tpl.evaluator else 1.0
    ok, errors = evaluate_event(event, world, npc_ids, budget=max_reward)
    log_evaluation(session, "event", event.id, ok, errors)

    if not ok:
        event.state = "rejected"
        save_event(session, event)
        director.update_tension_after_event(world, event, tpl)
        save_world(session, world)
        return None

    if not tpl.interactive:
        event.state = "active"
        save_event(session, event)
        _apply_initial_effects(session, world, event, tpl, rng)
        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng, value_multiplier=1.0,
        )
        event.payload["reward_id"] = reward_id
        event.payload["item_id"] = item_id
        event.payload["item_owner"] = item_owner
        event.state = "resolved"
        event.resolved_at = world.tick
        save_event(session, event)
        director.update_tension_after_event(world, event, tpl)
        save_world(session, world)
        return event

    event.payload["choices"] = build_choices(tpl)
    event.payload["choice_made"] = None
    event.payload["tpl_tags"] = list(tpl.tags)
    event.payload["max_reward"] = max_reward
    event.payload["difficulty"] = 0.5

    event.state = "awaiting_player"
    save_event(session, event)

    _apply_initial_effects(session, world, event, tpl, rng)

    save_world(session, world)
    return event


async def _generate_outcome_text(
    event: Event,
    choice_id: str,
    choice_label: str,
) -> str:
    prompt = load_prompt("event_resolve.md").format(
        summary=event.payload.get("summary", ""),
        narrative=event.payload.get("narrative", ""),
        choice_id=choice_id,
        choice_label=choice_label,
    )
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            outcome = str(raw.get("outcome", "")).strip()
            epilogue = str(raw.get("epilogue", "")).strip()
            if outcome:
                return (outcome + " " + epilogue).strip() if epilogue else outcome
    except Exception:
        pass
    return "%s——你选择了%s。" % (
        event.payload.get("summary", ""),
        choice_label,
    )


async def resolve_event(
    session: Session,
    world: World,
    event_id: str,
    choice_id: str,
) -> dict:
    row = session.get(EventRow, event_id)
    if row is None:
        return {"ok": False, "error": "event not found"}
    if row.state != "awaiting_player":
        return {"ok": False, "error": "event not awaiting player (state=%s)" % row.state}

    spec = get_choice_spec(choice_id)
    if spec is None:
        return {"ok": False, "error": "unknown choice: %s" % choice_id}

    from server.models.db import loads as _loads

    payload = _loads(row.payload_json) or {}
    event = Event(
        id=row.id,
        template_id=row.template_id,
        participants=_loads(row.participants_json) or [],
        location_id=row.location_id,
        state="awaiting_player",  # type: ignore[arg-type]
        payload=payload,
        created_at=row.created_at,
        resolved_at=None,
    )

    rng = random.Random(world.seed * 100003 + world.tick)

    choice_label = spec["label"]
    for c in payload.get("choices", []):
        if isinstance(c, dict) and c.get("id") == choice_id:
            choice_label = str(c.get("label", choice_label))
            break

    outcome_text = await _generate_outcome_text(event, choice_id, choice_label)

    for npc_id in event.participants:
        relationship.adjust(
            session,
            from_npc=npc_id,
            to_npc="player",
            trust=float(spec["relation_delta"].get("trust", 0.0)),
            affection=float(spec["relation_delta"].get("affection", 0.0)),
            fear=float(spec["relation_delta"].get("fear", 0.0)),
            debt=float(spec["relation_delta"].get("debt", 0.0)),
        )

    world.director.tension = max(
        0.0,
        min(1.0, world.director.tension + float(spec["tension_delta"])),
    )

    reward_id = None
    item_id = None
    item_owner = None

    if choice_id != "observe":
        owner_hint = _resolve_item_owner(event, choice_id, rng)
        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng,
            value_multiplier=float(spec["reward_multiplier"]),
            owner_hint=owner_hint,
        )

    payload["choice_made"] = choice_id
    payload["choice_label"] = choice_label
    payload["outcome"] = outcome_text
    payload["reward_id"] = reward_id
    payload["item_id"] = item_id
    payload["item_owner"] = item_owner

    row.state = "resolved"
    row.resolved_at = world.tick
    row.payload_json = dumps(payload)
    session.add(row)
    session.commit()

    save_world(session, world)

    return {
        "ok": True,
        "event_id": event_id,
        "choice_id": choice_id,
        "choice_label": choice_label,
        "outcome": outcome_text,
        "reward_id": reward_id,
        "item_id": item_id,
        "item_owner": item_owner,
    }


async def check_timeouts(session: Session, world: World) -> int:
    from server.models.db import loads as _loads

    rows = session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all()

    count = 0
    for row in rows:
        if world.tick - row.created_at < PLAYER_TIMEOUT_TICKS:
            continue
        try:
            payload = _loads(row.payload_json) or {}
            payload["choice_made"] = "observe"
            payload["choice_label"] = "静观其变（超时）"
            payload["outcome"] = "%s——你没有介入，事件自行落幕。" % (
                payload.get("summary", "事件")
            )
            payload["timeout"] = True
            row.state = "expired"
            row.resolved_at = world.tick
            row.payload_json = dumps(payload)
            session.add(row)
            count += 1
        except Exception:
            continue

    if count:
        session.commit()
    return count
'''

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
signal request_failed(endpoint: String, error: String)


func fetch_i18n() -> void:
	_request("GET", "/i18n", {}, "i18n_received")

func fetch_world_state() -> void:
	_request("GET", "/world/state", {}, "world_state_received")

func step_world() -> void:
	_request("POST", "/world/step", {}, "event_triggered")

func trigger_event() -> void:
	_request("POST", "/event/trigger", {}, "event_triggered")

func fetch_npcs() -> void:
	_request("GET", "/npc", {}, "npc_list_received")

func fetch_npc_detail(npc_id: String) -> void:
	_request("GET", "/npc/%s" % npc_id, {}, "npc_detail_received")

func fetch_relationships(npc_id: String) -> void:
	_request("GET", "/npc/%s/relationships" % npc_id, {}, "relationships_received")

func fetch_npc_items(npc_id: String) -> void:
	_request("GET", "/npc/%s/items" % npc_id, {}, "npc_items_received")

func send_dialogue(npc_id: String, player_input: String) -> void:
	_request("POST", "/npc/%s/dialogue" % npc_id, {"player_input": player_input}, "dialogue_received")

func fetch_events(limit: int = 20) -> void:
	_request("GET", "/event?limit=%d" % limit, {}, "event_list_received")

func fetch_rewards(limit: int = 20) -> void:
	_request("GET", "/reward?limit=%d" % limit, {}, "reward_list_received")

func fetch_items(limit: int = 100) -> void:
	_request("GET", "/item?limit=%d" % limit, {}, "item_list_received")

func take_item(item_id: String) -> void:
	_item_request("POST", "/item/%s/take" % item_id, {}, "take")

func drop_item(item_id: String) -> void:
	_item_request("POST", "/item/%s/drop" % item_id, {}, "drop")

func give_item(item_id: String, owner_id: String) -> void:
	_item_request("POST", "/item/%s/give" % item_id, {"owner_id": owner_id}, "give")

func use_item(item_id: String, target_npc_id: String) -> void:
	_item_request("POST", "/item/%s/use" % item_id, {"target_npc_id": target_npc_id}, "use")

func resolve_event(event_id: String, choice_id: String) -> void:
	_request("POST", "/event/%s/resolve" % event_id, {"choice_id": choice_id}, "event_resolved")

func fetch_map() -> void:
	_request("GET", "/map", {}, "map_received")


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
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray,
	http: HTTPRequest,
	action_name: String
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
	result: int,
	response_code: int,
	_headers: PackedStringArray,
	body: PackedByteArray,
	http: HTTPRequest,
	signal_name: String
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

FILES["tests/test_npc_gender.py"] = r'''from server.generators.npc import _default_npc, gender_zh
from server.models.schemas import NPC


def test_gender_zh_mapping():
    assert gender_zh("male") == "男"
    assert gender_zh("female") == "女"
    assert gender_zh("unknown") == "未知"
    assert gender_zh("other") == "未知"


def test_default_npc_has_gender_and_varied_traits():
    npc = _default_npc("npc_x", "张铁柱", "male")
    assert npc.gender == "male"
    assert npc.name == "张铁柱"
    values = list(npc.traits.values())
    assert len(set(round(v, 2) for v in values)) > 1


def test_npc_schema_gender_default():
    npc = NPC(id="x", name="y", age=30)
    assert npc.gender == "unknown"
'''

FILES["tests/test_item_ownership.py"] = r'''import random

from server.core.event_flow import _resolve_item_owner
from server.models.schemas import Event


def test_oppose_item_goes_to_player():
    evt = Event(id="e", template_id="t", participants=["npc_a", "npc_b"])
    owner = _resolve_item_owner(evt, "oppose", random.Random(1))
    assert owner == "player"


def test_help_item_goes_to_first_participant():
    evt = Event(id="e", template_id="t", participants=["npc_a", "npc_b"])
    owner = _resolve_item_owner(evt, "help", random.Random(1))
    assert owner == "npc_a"


def test_help_no_participants_returns_empty():
    evt = Event(id="e", template_id="t", participants=[])
    owner = _resolve_item_owner(evt, "help", random.Random(1))
    assert owner == ""
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

    print("\nDone. written=%d" % written)


if __name__ == "__main__":
    main()