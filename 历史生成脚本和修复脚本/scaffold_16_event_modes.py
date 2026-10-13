r"""EmergentWorld scaffold - Part 16: 事件模式 + 防重复。

改动：
    - EventTemplate 加 interactive 字段（默认 True）
    - 存在 awaiting_player 事件时：
        * 总数达到上限（3）则不再触发任何事件
        * 同一模板已在等待中则跳过
    - 非 interactive 模板生成后直接 resolved（"小道消息"）
    - 一批日常模板标记为 interactive: false
    - /event 返回 interactive 字段

运行：
    python scaffold_16_event_modes.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ schemas 覆盖

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
    # 新字段：是否需要玩家抉择
    #   True  = 事件生成后等待玩家选择（主线/卷入型）
    #   False = 事件生成后立即结算，玩家只是旁观（消息/背景型）
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

# ================================================================ director 覆盖

FILES["server/core/director.py"] = r'''"""事件导演：条件求值 + 张力曲线 + 权重衰减 + 节奏 + 防重复。"""

from __future__ import annotations

import math
import random
import re
from functools import lru_cache
from pathlib import Path

import yaml

from server.models.schemas import Event, EventTemplate, NPC, World


TAG_TENSION_CENTER: dict[str, float] = {
    "conflict":     0.75,
    "combat":       0.80,
    "survival":     0.65,
    "mystery":      0.50,
    "investigation": 0.50,
    "plot":         0.55,
    "political":    0.55,
    "adventure":    0.50,
    "social":       0.35,
    "daily":        0.30,
    "romance":      0.35,
    "celebration":  0.25,
    "ritual":       0.40,
    "trade":        0.35,
}

TAG_SIGMA = 0.28


_COND_RE = re.compile(r"^\s*([\w\.]+)\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*$")


def _resolve_path(ctx: dict, path: str):
    parts = path.split(".")
    cur = ctx
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _parse_rhs(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _eval_condition(expr: str, ctx: dict) -> bool:
    m = _COND_RE.match(expr)
    if not m:
        return True
    path, op, rhs_raw = m.groups()
    lhs = _resolve_path(ctx, path)
    if lhs is None:
        return True
    rhs = _parse_rhs(rhs_raw)
    try:
        if op == ">":  return bool(lhs > rhs)
        if op == "<":  return bool(lhs < rhs)
        if op == ">=": return bool(lhs >= rhs)
        if op == "<=": return bool(lhs <= rhs)
        if op == "==": return bool(lhs == rhs)
        if op == "!=": return bool(lhs != rhs)
    except TypeError:
        return True
    return True


def conditions_ok(tpl: EventTemplate, ctx: dict) -> bool:
    for cond in tpl.conditions:
        if not _eval_condition(cond, ctx):
            return False
    return True


def build_context(world: World, npcs: list[NPC]) -> dict:
    by_loc: dict[str, int] = {}
    for npc in npcs:
        by_loc[npc.location_id] = by_loc.get(npc.location_id, 0) + 1
    max_people = max(by_loc.values()) if by_loc else 0
    gap = world.tick - world.director.last_event_tick

    return {
        "world": {"tick": world.tick, "day": world.day, "hour": world.hour},
        "director": {
            "tension": world.director.tension,
            "last_event_tick": world.director.last_event_tick,
            "event_count": len(world.director.event_history),
            "ticks_since_last": gap,
        },
        "npc": {"count": len(npcs)},
        "location": {"has_people": len(npcs), "max_people": max_people},
        "tension": world.director.tension,
        "tick": world.tick,
        "hour": world.hour,
        "npc_count": len(npcs),
    }


def _gauss(x: float, mu: float, sigma: float) -> float:
    d = x - mu
    return math.exp(-(d * d) / (2 * sigma * sigma))


def fit_tension(tpl: EventTemplate, tension: float) -> float:
    if not tpl.tags:
        return 0.5
    scores: list[float] = []
    for tag in tpl.tags:
        mu = TAG_TENSION_CENTER.get(tag)
        scores.append(0.5 if mu is None else _gauss(tension, mu, TAG_SIGMA))
    scores.sort(reverse=True)
    top = scores[:2]
    return sum(top) / len(top)


def recent_penalty(tpl_id: str, world: World, window: int = 20) -> float:
    recent = world.director.event_history[-window:]
    count = recent.count(tpl_id)
    return 1.0 / (1.0 + count * 0.6)


def rhythm_factor(world: World) -> float:
    gap = world.tick - world.director.last_event_tick
    if gap >= 30:  return 1.5
    if gap <= 1:   return 0.4
    if gap <= 3:   return 0.7
    return 1.0


@lru_cache(maxsize=1)
def _load_templates_cached(template_dir: str) -> tuple[EventTemplate, ...]:
    tpls: list[EventTemplate] = []
    for path in sorted(Path(template_dir).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data:
            tpls.append(EventTemplate(**data))
    return tuple(tpls)


def load_templates(template_dir: str = "content/templates/events") -> list[EventTemplate]:
    return list(_load_templates_cached(str(template_dir)))


def cooldown_ok(tpl: EventTemplate, world: World) -> bool:
    last = world.director.last_event_tick
    return (world.tick - last) >= tpl.cooldown


def should_trigger(world: World, rng: random.Random) -> bool:
    gap = world.tick - world.director.last_event_tick
    if gap < 3:
        return False
    if gap >= 20:
        return True
    base = 0.03 + world.director.tension * 0.10
    if gap < 8:
        base *= 0.5
    elif gap >= 12:
        base *= 1.6
    return rng.random() < base


def pick_template(
    templates: list[EventTemplate],
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    ignore_cooldown: bool = False,
    pending_template_ids: set[str] | None = None,
    want_interactive: bool | None = None,
) -> EventTemplate | None:
    """从模板池里挑一个。

    pending_template_ids: 已在 awaiting_player 的模板 id 集合，会被跳过
    want_interactive: 只挑 interactive 值为该值（或 None 表示不限）
    """
    ctx = build_context(world, npcs)
    rhythm = rhythm_factor(world)
    tension = world.director.tension

    candidates: list[tuple[float, EventTemplate]] = []
    for tpl in templates:
        # 防重复：等待中的模板不再挑
        if pending_template_ids and tpl.id in pending_template_ids:
            continue

        if not ignore_cooldown and not cooldown_ok(tpl, world):
            continue
        if not ignore_cooldown and not conditions_ok(tpl, ctx):
            continue

        if want_interactive is not None and tpl.interactive != want_interactive:
            continue

        fit = fit_tension(tpl, tension)
        if fit < 0.05:
            continue

        diversity = recent_penalty(tpl.id, world)
        score = tpl.weight * fit * diversity * rhythm
        if score <= 0:
            continue
        candidates.append((score, tpl))

    if not candidates:
        return None

    total = sum(s for s, _ in candidates)
    r = rng.random() * total
    acc = 0.0
    for score, tpl in candidates:
        acc += score
        if r <= acc:
            return tpl
    return candidates[-1][1]


_TAG_TENSION_DELTA: dict[str, float] = {
    "conflict":     0.12,
    "combat":       0.15,
    "survival":     0.08,
    "mystery":      0.03,
    "investigation": 0.03,
    "plot":         0.02,
    "political":    0.05,
    "adventure":    0.02,
    "social":      -0.08,
    "daily":       -0.08,
    "romance":     -0.06,
    "celebration": -0.10,
    "ritual":      -0.03,
    "trade":       -0.06,
}


def update_tension_after_event(world: World, event: Event, tpl: EventTemplate) -> None:
    if tpl.tags:
        deltas = [_TAG_TENSION_DELTA.get(t, 0.0) for t in tpl.tags]
        avg = sum(deltas) / len(deltas)
    else:
        avg = 0.0
    world.director.tension = max(0.0, min(1.0, world.director.tension + avg))
    world.director.last_event_tick = world.tick
    world.director.event_history.append(event.id)
    if len(world.director.event_history) > 200:
        world.director.event_history = world.director.event_history[-200:]


def decay_tension(world: World) -> None:
    world.director.tension = max(0.0, world.director.tension - 0.003)
'''

# ================================================================ event_flow 覆盖

FILES["server/core/event_flow.py"] = r'''"""事件流程：串起 Director + Generator + Evaluator + 记忆 + 关系 + 物品。

事件有两种模式（由模板的 interactive 字段决定）：

    interactive = True（默认）
        事件生成后 state = "awaiting_player"，等玩家选择后结算。

    interactive = False
        事件生成后立即 resolved，玩家只是旁观者。
        适合"小道消息"式的背景事件。

防重复：
    - awaiting_player 事件总数达到 MAX_PENDING 时，不再触发新事件
    - 已有 awaiting 的模板，不会再被 pick_template 选中
"""

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


def _apply_initial_effects(
    session: Session,
    world: World,
    event: Event,
    tpl: EventTemplate,
    rng: random.Random,
) -> None:
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


def _pending_rows(session: Session) -> list[EventRow]:
    return list(session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all())


async def _emit_reward_and_item(
    session: Session,
    world: World,
    event: Event,
    rng: random.Random,
    value_multiplier: float = 1.0,
    item_to_player: bool = False,
) -> tuple[str | None, str | None, str | None]:
    """生成奖励与物品，返回 (reward_id, item_id, item_owner)。"""
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
        if item_to_player:
            item_owner = "player"
        else:
            item_owner = _pick_owner(event, rng)
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

    # 1. 已有等待中的事件数量检查
    pending = _pending_rows(session)
    if len(pending) >= MAX_PENDING:
        return None

    # 2. 触发概率检查
    if not force and not director.should_trigger(world, rng):
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    pending_template_ids = {r.template_id for r in pending}

    # 3. 挑选模板
    tpl = director.pick_template(
        templates, world, npcs, rng,
        ignore_cooldown=force,
        pending_template_ids=pending_template_ids,
    )
    if tpl is None:
        # 如果 interactive 都被占用，退而求其次找个消息类模板
        if pending_template_ids:
            tpl = director.pick_template(
                templates, world, npcs, rng,
                ignore_cooldown=False,
                pending_template_ids=pending_template_ids,
                want_interactive=False,
            )
        if tpl is None:
            return None

    # 4. 生成事件
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

    # ============================================================
    # 分支 A：非交互事件 —— 直接结算，玩家只是旁观
    # ============================================================
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

    # ============================================================
    # 分支 B：交互事件 —— 等待玩家
    # ============================================================
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
        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng,
            value_multiplier=float(spec["reward_multiplier"]),
            item_to_player=bool(spec["gave_item"]),
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

# ================================================================ main.py patch（_row_to_event 加字段）

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
        "version": "0.9.0",
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
            "interactive": bool(event.payload.get("interactive", True)) if event else False,
        }


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


def _row_to_event(r: EventRow, npc_names: dict[str, str]) -> dict:
    payload = loads(r.payload_json) or {}
    participants = loads(r.participants_json) or []
    participant_names = [npc_names.get(pid, pid) for pid in participants]
    choices = payload.get("choices") or []
    interactive = bool(payload.get("interactive", True))

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
        "interactive": interactive,
        "payload": payload,
        "summary": payload.get("summary") or "",
        "narrative": payload.get("narrative") or "",
        "choices": choices,
        "choice_made": payload.get("choice_made") or "",
        "choice_label": payload.get("choice_label") or "",
        "outcome": payload.get("outcome") or "",
        "item_id": payload.get("item_id") or "",
        "item_owner": payload.get("item_owner") or "",
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
            raise HTTPException(
                400,
                "no event triggered (all templates busy / no valid candidates)",
            )
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

# ================================================================ 给一批模板加 interactive: false

# 小道消息型（生成即结算，玩家旁观）
MESSAGE_TEMPLATES = {
    "traveling_bard": "ordinary",
    "strange_dream": "ordinary",
    "drought": "ordinary",
    "plague_rats": "ordinary",
    "wandering_merchant_caravan": "ordinary",
    "market_dispute": "ordinary",
}


def _build_yaml(tid: str, tags: list[str], cooldown: int, weight: float,
                conditions: list[str], params: dict, prompt: str,
                evaluator: dict, interactive: bool) -> str:
    def _list(items: list[str], indent: int = 2) -> str:
        pad = " " * indent
        return "\n".join("%s- %s" % (pad, x) for x in items) if items else pad + "[]"

    tag_str = "[" + ", ".join(tags) + "]"
    params_str = "\n".join("  %s: %s" % (k, v) for k, v in params.items())
    prompt_str = "\n".join("  " + line for line in prompt.splitlines())
    eval_str = "\n".join("  %s: %s" % (k, v) for k, v in evaluator.items())

    return (
        "id: %s\n" % tid
        + "tags: %s\n" % tag_str
        + "cooldown: %d\n" % cooldown
        + "weight: %s\n" % weight
        + "interactive: %s\n" % ("true" if interactive else "false")
        + "conditions:\n" + _list(conditions) + "\n"
        + "params:\n" + params_str + "\n"
        + "prompt: |\n" + prompt_str + "\n"
        + "evaluator:\n" + eval_str + "\n"
    )


# 已有的 6 个日常事件改成 interactive: false
FILES["content/templates/events/traveling_bard.yaml"] = _build_yaml(
    "traveling_bard", ["social", "celebration", "daily"], 7, 1.1,
    ["director.tension < 0.6"],
    {"participant_count": 3, "location": "tavern"},
    "一位流浪诗人来到酒馆，弹唱关于远方与旧事的歌谣。\n歌词里隐含着某个 NPC 的秘密或渴望。",
    {"require": "[bard, song_theme, listener]", "max_reward": 0.2},
    interactive=False,
)

FILES["content/templates/events/strange_dream.yaml"] = _build_yaml(
    "strange_dream", ["mystery", "daily"], 4, 1.4,
    ["director.tension < 0.7"],
    {"participant_count": 2, "location": "home"},
    "一名 NPC 做了怪梦，醒来后心神不宁。\n梦里的场景似乎在预言某件事。",
    {"require": "[dreamer, dream_image, omen]", "max_reward": 0.15},
    interactive=False,
)

FILES["content/templates/events/drought.yaml"] = _build_yaml(
    "drought", ["survival", "conflict"], 25, 0.7,
    ["director.tension > 0.5"],
    {"participant_count": 4, "location": "village_square"},
    "久旱无雨，井水渐枯，村民开始焦虑。\n至少一名 NPC 提出极端建议。",
    {"require": [1, 2, 3], "max_reward": 0.5},
    interactive=False,
)

FILES["content/templates/events/plague_rats.yaml"] = _build_yaml(
    "plague_rats", ["survival", "conflict", "investigation"], 22, 0.75,
    ["director.tension > 0.4"],
    {"participant_count": 3, "location": "home"},
    "有人在谷仓发现大量死鼠，疑似瘟疫先兆。\n参与者对是否声张产生分歧。",
    {"require": [1, 2, 3], "max_reward": 0.45},
    interactive=False,
)

FILES["content/templates/events/wandering_merchant_caravan.yaml"] = _build_yaml(
    "wandering_merchant_caravan", ["trade", "daily", "social"], 8, 1.1,
    ["director.tension < 0.6"],
    {"participant_count": 3, "location": "market"},
    "一支商队抵达村口，带来稀有货物与远方消息。\n消息中有一条与某位村民或某件旧事直接相关。",
    {"require": [1, 2, 3], "max_reward": 0.25},
    interactive=False,
)

FILES["content/templates/events/market_dispute.yaml"] = _build_yaml(
    "market_dispute", ["conflict", "daily", "trade"], 3, 1.5,
    ["director.tension < 0.8"],
    {"participant_count": 2, "location": "market"},
    "买卖双方因价格或成色争执，引得旁人围观。\n争执背后可能有更深的旧怨。",
    {"require": [1, 2, 3], "max_reward": 0.15},
    interactive=False,
)

# ================================================================ 新测试

FILES["tests/test_interactive.py"] = r'''"""事件模式与防重复测试。"""
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from server.core import director
from server.core.world import create_world, load_npcs, save_event, save_npc, save_world
from server.models.db import EventRow
from server.models.schemas import Event, EventTemplate, NPC


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def _tpl(id_: str, tags: list[str] | None = None, interactive: bool = True) -> EventTemplate:
    return EventTemplate(
        id=id_, tags=tags or ["daily"], weight=1.0, cooldown=0,
        interactive=interactive, params={"participant_count": 2},
    )


def test_template_interactive_default_true():
    tpl = EventTemplate(id="x")
    assert tpl.interactive is True


def test_pick_template_skips_pending():
    world = World = create_world("t", seed=1)
    world.tick = 100
    world.director.last_event_tick = -999

    from server.models.schemas import World
    world = World(id="w", seed=1)
    world.tick = 100
    world.director.last_event_tick = -999

    tpls = [_tpl("a"), _tpl("b")]
    npcs = [NPC(id="n1", name="N1", age=20), NPC(id="n2", name="N2", age=20)]

    import random
    # 全部被占用 → 返回 None
    picked = director.pick_template(
        tpls, world, npcs, random.Random(1),
        pending_template_ids={"a", "b"},
    )
    assert picked is None

    # 只有 a 被占用 → 只能选到 b
    picked = director.pick_template(
        tpls, world, npcs, random.Random(1),
        pending_template_ids={"a"},
    )
    assert picked is not None
    assert picked.id == "b"


def test_pick_template_want_interactive():
    from server.models.schemas import World
    world = World(id="w", seed=1)
    world.tick = 100
    world.director.last_event_tick = -999
    world.director.tension = 0.4

    tpls = [_tpl("msg", interactive=False), _tpl("quest", interactive=True)]
    npcs = [NPC(id="n1", name="N1", age=20), NPC(id="n2", name="N2", age=20)]

    import random
    picked = director.pick_template(
        tpls, world, npcs, random.Random(1), want_interactive=False,
    )
    assert picked is not None
    assert picked.id == "msg"

    picked = director.pick_template(
        tpls, world, npcs, random.Random(1), want_interactive=True,
    )
    assert picked is not None
    assert picked.id == "quest"


@pytest.mark.asyncio
async def test_non_interactive_event_auto_resolves(monkeypatch):
    """非交互事件生成后直接 resolved。"""
    from server.core import event_flow
    from server.models.schemas import Reward

    async def fake_fill(tpl, world, npcs, rng):
        return Event(
            id="evt_auto",
            template_id=tpl.id,
            participants=[n.id for n in npcs[:2]],
            location_id="village_square",
            state="pending",
            payload={"summary": "消息事件", "narrative": ""},
            created_at=world.tick,
        )

    async def fake_reward(event, world):
        return Reward(
            id="rwd_x", event_id=event.id, kind="item",
            value=0.1, description="x", payload={},
        )

    monkeypatch.setattr(event_flow, "fill_event", fake_fill)
    monkeypatch.setattr(event_flow, "generate_reward", fake_reward)

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 10
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20))

        tpl = EventTemplate(
            id="msg_tpl", tags=["daily"], weight=1.0, cooldown=0,
            interactive=False, params={"participant_count": 2},
        )
        evt = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert evt is not None
        assert evt.state == "resolved"
        assert evt.payload.get("interactive") is False


@pytest.mark.asyncio
async def test_pending_events_cap(monkeypatch):
    """已有 MAX_PENDING 个等待事件时，不再触发。"""
    from server.core import event_flow

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 100
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20))

        # 造 3 个 waiting 事件
        for i in range(event_flow.MAX_PENDING):
            evt = Event(
                id="evt_%d" % i, template_id="x_%d" % i,
                participants=[], location_id="village_square",
                state="awaiting_player", payload={"summary": "x"},
                created_at=world.tick - 1,
            )
            save_event(s, evt)

        tpl = EventTemplate(id="y", tags=["daily"], weight=1.0, cooldown=0)
        result = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert result is None
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

    print("\nPart 16 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()