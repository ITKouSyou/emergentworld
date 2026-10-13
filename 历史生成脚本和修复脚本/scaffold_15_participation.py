r"""EmergentWorld scaffold - Part 15: 玩家参与事件。

- 事件状态机：awaiting_player / resolved / expired
- 玩家选项：出手相助 / 静观其变 / 暗中阻挠
- 奖励延后：玩家 resolve 时才发
- 超时：8 tick 自动按"旁观"结算
- prompt 要求 LLM 写到关键时刻停住

运行：
    python scaffold_15_participation.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ schemas 覆盖（加状态）

FILES["server/models/schemas.py"] = r'''"""所有 Pydantic 数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NPC(BaseModel):
    id: str
    name: str
    age: int = Field(ge=0, le=200)
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
    "pending",
    "active",
    "awaiting_player",
    "resolved",
    "expired",
    "rejected",
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

# ================================================================ choices

FILES["server/core/choices.py"] = r'''"""玩家对事件的三个选项：出手相助 / 静观其变 / 暗中阻挠。"""

from __future__ import annotations

from server.models.schemas import Event, EventTemplate


# 通用三选项。每个选项定义：
#   id: 唯一标识
#   label: 前端显示
#   tension_delta: 事件后张力变化
#   relation_delta: 参与者对玩家的关系变化
#   reward_multiplier: 影响奖励价值（1.0 为基准）
#   gave_item: 是否可能生成物品
CHOICES: dict[str, dict] = {
    "help": {
        "id": "help",
        "label": "出手相助",
        "tension_delta": -0.05,
        "relation_delta": {"trust": 0.12, "affection": 0.10},
        "reward_multiplier": 1.0,
        "gave_item": False,
    },
    "observe": {
        "id": "observe",
        "label": "静观其变",
        "tension_delta": 0.0,
        "relation_delta": {},
        "reward_multiplier": 0.5,
        "gave_item": False,
    },
    "oppose": {
        "id": "oppose",
        "label": "暗中阻挠",
        "tension_delta": 0.08,
        "relation_delta": {"trust": -0.15, "fear": 0.10, "affection": -0.08},
        "reward_multiplier": 1.2,
        "gave_item": True,
    },
}


# 不同 tags 下用不同措辞，让三选项读起来更贴合情境
LABEL_OVERRIDES: dict[str, dict[str, str]] = {
    "conflict":   {"help": "挺身而出", "observe": "作壁上观", "oppose": "站在强势一方"},
    "romance":    {"help": "乐见其成", "observe": "不置可否", "oppose": "从中作梗"},
    "investigation": {"help": "协助查案", "observe": "静观其变", "oppose": "隐瞒线索"},
    "trade":      {"help": "促成交易", "observe": "不插手", "oppose": "从中抬价"},
    "political":  {"help": "支持一方", "observe": "保持中立", "oppose": "暗中捣乱"},
    "survival":   {"help": "伸出援手", "observe": "先顾自己", "oppose": "趁乱取利"},
    "celebration": {"help": "共襄盛举", "observe": "远远看着", "oppose": "扫兴而去"},
    "mystery":    {"help": "追查到底", "observe": "按兵不动", "oppose": "掩盖痕迹"},
    "plot":       {"help": "卷入其中", "observe": "暂不表态", "oppose": "搅乱局势"},
    "adventure":  {"help": "结伴同行", "observe": "婉言谢绝", "oppose": "抢先一步"},
    "social":     {"help": "从中调解", "observe": "旁观不语", "oppose": "推波助澜"},
    "daily":      {"help": "帮一把手", "observe": "不闻不问", "oppose": "从中作梗"},
    "combat":     {"help": "并肩作战", "observe": "退到一旁", "oppose": "背后偷袭"},
}


def build_choices(tpl: EventTemplate) -> list[dict]:
    """根据模板 tags 生成玩家选项列表。"""
    override: dict[str, str] = {}
    for tag in tpl.tags:
        if tag in LABEL_OVERRIDES:
            override = LABEL_OVERRIDES[tag]
            break

    result: list[dict] = []
    for cid in ("help", "observe", "oppose"):
        base = CHOICES[cid]
        result.append({
            "id": cid,
            "label": override.get(cid, base["label"]),
        })
    return result


def get_choice_spec(choice_id: str) -> dict | None:
    return CHOICES.get(choice_id)
'''

# ================================================================ prompts 覆盖

FILES["server/prompts/event_fill.md"] = r'''你是游戏事件填充器。给定一个事件模板与世界上下文，生成事件细节。

**重要：所有输出必须使用简体中文，不要用英文。**

规则：
- 输出必须是合法 JSON
- 顶层键为 payload，payload 内含 summary 与 narrative
- summary：一句话概述，**必须提到所有参与者名字**，不超过 45 字
- narrative：2-4 句细节描述，写到**关键时刻停住**，制造悬念
  - 最后一句话应该是暗示"玩家需要做出选择"的收尾
  - 例如："……现在他们都看向了你。" 或 "……剑已出鞘，你打算怎么办？"
- **必须使用参与者真实名字**（不要写"某人"、"一名 NPC"）
- 不要改变参与者与地点
- 不要输出 markdown

模板 ID：{template_id}
模板名称：{template_label}
模板提示：{prompt}
参与者（**请使用这些名字**）：{participants}
地点：{location}（{location_label}）
当前天数：{day}
'''

FILES["server/prompts/event_resolve.md"] = r'''你是游戏事件结算器。玩家对事件做出了选择，请生成结算文本。

**重要：所有输出必须使用简体中文。**

规则：
- 输出必须是合法 JSON：{{"outcome": "结算描述（1-2 句，不超过 60 字）", "epilogue": "后续影响暗示（可选，1 句）"}}
- outcome 描述玩家的选择带来的直接结果
- epilogue 暗示这件事的长远影响
- 不要输出 markdown，不要输出解释

原事件：{summary}
事件叙述：{narrative}
玩家选择：{choice_label}
玩家选择的行为：{choice_id}
'''

# ================================================================ event_flow 覆盖

FILES["server/core/event_flow.py"] = r'''"""事件流程：串起 Director + Generator + Evaluator + 记忆 + 关系 + 物品。

玩家参与模式：
    - 事件生成后 state = "awaiting_player"
    - 玩家调用 /event/{id}/resolve 提交选择
    - 若 8 tick 内未响应，自动按 observe 结算（expired）
"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session

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


# ============================================================
# 保存工具
# ============================================================

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


def _pick_owner(event: Event, rng: random.Random) -> str:
    if not event.participants:
        return "player"
    if rng.random() < 0.5:
        return "player"
    return rng.choice(event.participants)


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


# ============================================================
# 事件生成
# ============================================================

def _apply_initial_effects(
    session: Session,
    world: World,
    event: Event,
    tpl: EventTemplate,
    rng: random.Random,
) -> None:
    """事件发生时的即时影响（参与者互相之间的记忆与关系变化）。"""
    summary = event.payload.get("summary", "") or "发生了 %s" % tpl.id
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


async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick)

    if not force and not director.should_trigger(world, rng):
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    tpl = director.pick_template(templates, world, npcs, rng, ignore_cooldown=force)
    if tpl is None:
        return None

    event = await fill_event(tpl, world, npcs, rng)

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

    # 生成玩家选项
    event.payload["choices"] = build_choices(tpl)
    event.payload["choice_made"] = None
    event.payload["tpl_tags"] = list(tpl.tags)
    event.payload["max_reward"] = max_reward
    event.payload["difficulty"] = 0.5

    # 状态：等待玩家
    event.state = "awaiting_player"
    save_event(session, event)

    # 参与者之间的即时影响（不需要玩家参与就已发生）
    _apply_initial_effects(session, world, event, tpl, rng)

    save_world(session, world)
    return event


# ============================================================
# 玩家响应
# ============================================================

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
                if epilogue:
                    return outcome + " " + epilogue
                return outcome
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
    """玩家对事件做出选择，结算奖励与关系。"""
    row = session.get(EventRow, event_id)
    if row is None:
        return {"ok": False, "error": "event not found"}
    if row.state != "awaiting_player":
        return {"ok": False, "error": "event not awaiting player (state=%s)" % row.state}

    spec = get_choice_spec(choice_id)
    if spec is None:
        return {"ok": False, "error": "unknown choice: %s" % choice_id}

    from server.core.world import load_world as _load_world
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

    # 1. 结算叙事
    choice_label = spec["label"]
    for c in payload.get("choices", []):
        if isinstance(c, dict) and c.get("id") == choice_id:
            choice_label = str(c.get("label", choice_label))
            break

    outcome_text = await _generate_outcome_text(event, choice_id, choice_label)

    # 2. 关系变化：参与者对玩家
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

    # 3. 张力
    world.director.tension = max(
        0.0,
        min(1.0, world.director.tension + float(spec["tension_delta"])),
    )

    # 4. 奖励（除 observe 外都生成）
    reward_id = None
    item_id = None
    item_owner = None

    if choice_id != "observe":
        budget = compute_budget(event, world) * float(spec["reward_multiplier"])
        reward = await generate_reward(event, world)
        reward.value = min(reward.value * float(spec["reward_multiplier"]), 1.0)
        reward.description = "%s：%s" % (choice_label, reward.description)

        reward_ok, reward_errors = evaluate_reward(reward, budget)
        log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)

        if reward_ok:
            _save_reward(session, reward)
            reward_id = reward.id

            item_data = reward.payload.get("item")
            if isinstance(item_data, dict) and item_data.get("id"):
                if spec["gave_item"]:
                    item_owner = "player"
                else:
                    item_owner = _pick_owner(event, rng)
                _save_item(session, reward.id, event.id, item_data, item_owner)
                item_id = item_data["id"]

    # 5. 更新事件
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


# ============================================================
# 超时处理
# ============================================================

async def check_timeouts(session: Session, world: World) -> int:
    """把超过 PLAYER_TIMEOUT_TICKS 未响应的事件按 observe 结算。"""
    from sqlmodel import select
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

# ================================================================ tick 覆盖（超时检查）

FILES["server/core/tick.py"] = r'''"""时间推进。所有实时逻辑同步执行。

事件触发由 event_flow.run_event_cycle() 异步处理，
调用方需要在 tick 之后单独 await 一次事件循环，
并 await 一次超时检查。
"""

from __future__ import annotations

from sqlmodel import Session

from server.core import director
from server.core.world import save_world
from server.models.schemas import World
from server.systems import behavior, economy


def tick(session: Session, world: World) -> None:
    behavior.step(session, world)
    economy.settle(session, world)
    director.decay_tension(world)

    world.hour += 1
    if world.hour >= 24:
        world.hour = 0
        world.day += 1
    world.tick += 1

    save_world(session, world)
'''

# ================================================================ main.py 覆盖

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
from server.core.event_flow import check_timeouts, resolve_event, run_event_cycle
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
        "version": "0.8.0",
        "docs": "/docs",
        "embedding_enabled": settings.embedding_enabled,
        "endpoints": [
            "/health", "/i18n", "/map",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/npc/{npc_id}/items", "/npc/{npc_id}/memories",
            "/event", "/event/trigger",
            "/event/pending", "/event/{event_id}/resolve",
            "/reward", "/item", "/item/{item_id}",
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
        await check_timeouts(s, world)
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
            "awaiting_player": event.state == "awaiting_player" if event else False,
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

def _row_to_event(r: EventRow, npc_names: dict[str, str]) -> dict:
    payload = loads(r.payload_json) or {}
    participants = loads(r.participants_json) or []
    participant_names = [npc_names.get(pid, pid) for pid in participants]

    choices = payload.get("choices") or []
    choice_made = payload.get("choice_made")

    return {
        "id": r.id,
        "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": participants,
        "participant_names": participant_names,
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state,
        "state_label": i18n.state_label(r.state),
        "awaiting_player": r.state == "awaiting_player",
        "payload": payload,
        "summary": payload.get("summary", ""),
        "narrative": payload.get("narrative", ""),
        "choices": choices,
        "choice_made": choice_made,
        "choice_label": payload.get("choice_label"),
        "outcome": payload.get("outcome"),
        "item_id": payload.get("item_id"),
        "item_owner": payload.get("item_owner"),
        "created_at": r.created_at,
        "resolved_at": r.resolved_at,
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
    """只列出等待玩家响应的事件。"""
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow)
            .where(EventRow.state == "awaiting_player")
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
            raise HTTPException(400, "no event triggered (check templates / npcs)")
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

# ================================================================ i18n 覆盖

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
        "templates": TEMPLATE_LABELS,
        "locations": LOCATION_LABELS,
        "reward_kinds": REWARD_KIND_LABELS,
        "states": STATE_LABELS,
    }
'''

# ================================================================ tests

FILES["tests/test_event_participation.py"] = r'''"""玩家参与事件的测试。"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.choices import build_choices, get_choice_spec
from server.core.world import create_world, load_world, save_event, save_npc, save_world
from server.models.db import EventRow
from server.models.schemas import Event, EventTemplate, NPC


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_build_choices_default():
    tpl = EventTemplate(id="x", tags=[])
    choices = build_choices(tpl)
    assert len(choices) == 3
    ids = [c["id"] for c in choices]
    assert ids == ["help", "observe", "oppose"]


def test_build_choices_conflict_labels():
    tpl = EventTemplate(id="x", tags=["conflict"])
    choices = build_choices(tpl)
    labels = {c["id"]: c["label"] for c in choices}
    assert labels["help"] == "挺身而出"
    assert labels["oppose"] == "站在强势一方"


def test_get_choice_spec():
    spec = get_choice_spec("help")
    assert spec is not None
    assert spec["relation_delta"]["trust"] > 0

    spec = get_choice_spec("oppose")
    assert spec["tension_delta"] > 0

    assert get_choice_spec("nonexistent") is None


@pytest.mark.asyncio
async def test_resolve_event_applies_effects(monkeypatch):
    """玩家响应事件后，关系与状态都应更新。"""
    from server.core import event_flow

    class FakeLLM:
        async def text_json(self, prompt):
            return {"outcome": "你挺身而出，众人感激。"}
        async def text(self, prompt):
            return "ok"

    monkeypatch.setattr(event_flow, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 5
        save_world(s, world)

        save_npc(s, NPC(id="npc_a", name="Alden", age=30))
        save_npc(s, NPC(id="npc_b", name="Dain", age=30))

        evt = Event(
            id="evt_1",
            template_id="bandit_raid",
            participants=["npc_a", "npc_b"],
            location_id="village_edge",
            state="awaiting_player",
            payload={
                "summary": "强盗袭击，Alden 与 Dain 奋力抵抗。",
                "narrative": "刀光剑影中，两人背靠背站着。",
                "choices": build_choices(EventTemplate(id="bandit_raid", tags=["conflict"])),
                "max_reward": 0.5,
                "difficulty": 0.5,
                "tpl_tags": ["conflict"],
            },
            created_at=5,
        )
        save_event(s, evt)

        result = await event_flow.resolve_event(s, world, "evt_1", "help")
        assert result["ok"] is True
        assert result["choice_id"] == "help"
        assert "挺身" in result["outcome"] or "感激" in result["outcome"]

        # 状态变成 resolved
        row = s.get(EventRow, "evt_1")
        assert row is not None
        assert row.state == "resolved"

        # 关系提升
        from server.systems.relationship import get_relation_to
        rel = get_relation_to(s, "npc_a", "player")
        assert rel.trust > 0


@pytest.mark.asyncio
async def test_timeout_marks_expired(monkeypatch):
    from server.core import event_flow

    class FakeLLM:
        async def text_json(self, prompt):
            return {"outcome": "ok"}

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 100   # 远超超时阈值
        save_world(s, world)

        evt = Event(
            id="evt_stale",
            template_id="x",
            participants=[],
            location_id="village_square",
            state="awaiting_player",
            payload={"summary": "一件事"},
            created_at=0,   # 100 tick 之前创建
        )
        save_event(s, evt)

        count = await event_flow.check_timeouts(s, world)
        assert count == 1

        row = s.get(EventRow, "evt_stale")
        assert row is not None
        assert row.state == "expired"


def test_event_response_has_participant_names():
    """事件返回应带 participant_names 字段。"""
    from server.main import _row_to_event
    row = EventRow(
        id="evt_x",
        template_id="bandit_raid",
        participants_json='["npc_a", "npc_b"]',
        location_id="village_edge",
        state="awaiting_player",
        payload_json='{"summary": "x", "choices": []}',
        created_at=1,
    )
    npc_names = {"npc_a": "Alden", "npc_b": "Dain"}
    result = _row_to_event(row, npc_names)
    assert result["participant_names"] == ["Alden", "Dain"]
    assert result["awaiting_player"] is True
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

    print("\nPart 15 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()