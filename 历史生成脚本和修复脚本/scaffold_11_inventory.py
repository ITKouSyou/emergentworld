r"""EmergentWorld scaffold - Part 11: 物品归属 + 物品使用。

运行：
    python scaffold_11_inventory.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ db.py 覆盖

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
    owner_id: str = Field(default="", index=True)   # "" | "player" | npc_id
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

# ================================================================ session.py 覆盖（加 schema 升级）

FILES["server/db/session.py"] = r'''"""数据库会话工厂 + 老库 schema 升级。"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, create_engine

from server.config import settings

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


def get_session() -> Session:
    return Session(engine)


def ensure_schema() -> None:
    """对已有数据库做增量列升级（SQLite 不支持 IF NOT EXISTS 加列）。"""
    with engine.begin() as conn:
        # item 表
        rows = conn.execute(text("PRAGMA table_info(item)")).fetchall()
        if rows:
            cols = {r[1] for r in rows}
            if "owner_id" not in cols:
                conn.execute(text(
                    "ALTER TABLE item ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''"
                ))
            if "consumed" not in cols:
                conn.execute(text(
                    "ALTER TABLE item ADD COLUMN consumed INTEGER NOT NULL DEFAULT 0"
                ))
'''

# ================================================================ inventory

FILES["server/systems/inventory.py"] = r'''"""物品归属系统：给予 / 拿回 / 查询。"""

from __future__ import annotations

from sqlmodel import Session, select

from server.models.db import ItemRow, loads


PLAYER_OWNER = "player"
NO_OWNER = ""


def get_item_row(session: Session, item_id: str) -> ItemRow | None:
    return session.get(ItemRow, item_id)


def give_item(session: Session, item_id: str, owner_id: str) -> ItemRow | None:
    row = session.get(ItemRow, item_id)
    if row is None:
        return None
    row.owner_id = owner_id
    session.add(row)
    session.commit()
    return row


def drop_item(session: Session, item_id: str) -> ItemRow | None:
    """丢弃：设为无主。"""
    return give_item(session, item_id, NO_OWNER)


def consume_item(session: Session, item_id: str) -> ItemRow | None:
    row = session.get(ItemRow, item_id)
    if row is None:
        return None
    row.consumed = True
    session.add(row)
    session.commit()
    return row


def list_items_by_owner(
    session: Session,
    owner_id: str,
    include_consumed: bool = False,
) -> list[ItemRow]:
    stmt = select(ItemRow).where(ItemRow.owner_id == owner_id)
    if not include_consumed:
        stmt = stmt.where(ItemRow.consumed == False)  # noqa: E712
    return list(session.exec(stmt).all())


def list_all_items(session: Session, include_consumed: bool = False) -> list[ItemRow]:
    stmt = select(ItemRow)
    if not include_consumed:
        stmt = stmt.where(ItemRow.consumed == False)  # noqa: E712
    return list(session.exec(stmt).all())


def row_to_dict(row: ItemRow) -> dict:
    return {
        "id": row.id,
        "reward_id": row.reward_id,
        "event_id": row.event_id,
        "name": row.name,
        "kind": row.kind,
        "affixes": loads(row.affixes_json) or [],
        "story": row.story,
        "value": row.value,
        "owner_id": row.owner_id,
        "consumed": row.consumed,
    }
'''

# ================================================================ item_use

FILES["server/systems/item_use.py"] = r'''"""物品使用：LLM 生成效果 + 关系/需求调整 + 可消耗。"""

from __future__ import annotations

import json
import random
import uuid

from sqlmodel import Session

from server.core.world import load_npcs
from server.generators.base import get_llm, load_prompt
from server.models.db import ItemUseRow, dumps
from server.models.schemas import World
from server.systems import inventory, relationship


def _fallback_effect(item_name: str, target_name: str) -> dict:
    if target_name:
        text = "%s收下了%s，神色略显动容。" % (target_name, item_name)
    else:
        text = "你把玩着%s，心绪稍定。" % item_name
    return {
        "effect": text,
        "relationship_change": {},
        "consume": False,
    }


async def use_item(
    session: Session,
    world: World,
    item_id: str,
    user_id: str = "player",
    target_npc_id: str = "",
) -> dict:
    row = inventory.get_item_row(session, item_id)
    if row is None:
        return {"ok": False, "error": "item not found"}
    if row.consumed:
        return {"ok": False, "error": "item already consumed"}

    npcs = load_npcs(session)
    npc_names = {n.id: n.name for n in npcs}
    target_name = npc_names.get(target_npc_id, "")

    prompt = load_prompt("item_use.md").format(
        item_name=row.name,
        item_kind=row.kind,
        item_affixes=", ".join(inventory.loads(row.affixes_json) or []),
        item_story=row.story,
        target_name=target_name or "（无）",
        world_tick=world.tick,
    )
    fallback = _fallback_effect(row.name, target_name)

    effect_data = fallback
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            effect = str(raw.get("effect", "")).strip()[:200]
            rel_change = raw.get("relationship_change", {})
            if not isinstance(rel_change, dict):
                rel_change = {}
            consume = bool(raw.get("consume", False))
            if effect:
                effect_data = {
                    "effect": effect,
                    "relationship_change": rel_change,
                    "consume": consume,
                }
    except Exception:
        pass

    # 应用效果
    if target_npc_id and effect_data.get("relationship_change"):
        rc = effect_data["relationship_change"]
        relationship.adjust(
            session,
            from_npc=target_npc_id,
            to_npc=user_id if user_id != "player" else target_npc_id,
            trust=float(rc.get("trust", 0.0)),
            affection=float(rc.get("affection", 0.0)),
            fear=float(rc.get("fear", 0.0)),
            debt=float(rc.get("debt", 0.0)),
        )

    consumed = bool(effect_data.get("consume", False))
    if consumed:
        inventory.consume_item(session, item_id)

    use_row = ItemUseRow(
        id="use_%s" % uuid.uuid4().hex[:8],
        item_id=item_id,
        user_id=user_id,
        target_npc_id=target_npc_id,
        effect=effect_data["effect"],
        consumed=consumed,
        timestamp=world.tick,
    )
    session.add(use_row)
    session.commit()

    return {
        "ok": True,
        "item_id": item_id,
        "item_name": row.name,
        "target_npc_id": target_npc_id,
        "target_name": target_name,
        "effect": effect_data["effect"],
        "consumed": consumed,
    }
'''

# ================================================================ prompt

FILES["server/prompts/item_use.md"] = r'''你是游戏物品使用效果生成器。

**重要：所有输出必须使用简体中文。**

规则：
- 输出必须是合法 JSON
- 结构：{{"effect": "使用描述（1-3 句，不超过 80 字）", "relationship_change": {{"trust": 0.0, "affection": 0.0, "fear": 0.0, "debt": 0.0}}, "consume": true|false}}
- effect：生动描述使用后的场景
- relationship_change：如果目标 NPC 在场，可以调整关系值，范围 -0.3 到 0.3，没变化就留空 {{}}
- consume：物品是否被消耗（送出去的礼物一定消耗；把玩的物品不一定）
- 不要输出 markdown，不要输出解释

物品名称：{item_name}
物品类别：{item_kind}
物品词缀：{item_affixes}
物品来历：{item_story}
使用目标：{target_name}
当前世界 tick：{world_tick}
'''

# ================================================================ event_flow 覆盖（物品归属）

FILES["server/core/event_flow.py"] = r'''"""事件流程：串起 Director + Generator + Evaluator + 记忆 + 关系 + 物品。"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session

from server.core import director
from server.core.evaluator import evaluate_event, evaluate_reward, log_evaluation
from server.core.world import load_npcs, save_event, save_world
from server.generators.event import fill_event
from server.generators.reward import compute_budget, generate_reward
from server.models.db import ItemRow, RewardRow, dumps
from server.models.schemas import Event, EventTemplate, Reward, World
from server.systems import relationship


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


def _apply_effects(
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


async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick)

    if not force and not director.should_trigger(world, rng):
        return None

    tpl = director.pick_template(templates, world, rng, ignore_cooldown=force)
    if tpl is None:
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
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

    event.state = "active"
    save_event(session, event)

    _apply_effects(session, world, event, tpl, rng)

    budget = compute_budget(event, world)
    reward = await generate_reward(event, world)
    reward_ok, reward_errors = evaluate_reward(reward, budget)
    log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)

    if reward_ok:
        _save_reward(session, reward)
        event.payload["reward_id"] = reward.id

        item_data = reward.payload.get("item")
        if isinstance(item_data, dict) and item_data.get("id"):
            owner = _pick_owner(event, rng)
            _save_item(session, reward.id, event.id, item_data, owner)
            event.payload["item_id"] = item_data["id"]
            event.payload["item_owner"] = owner

    event.state = "resolved"
    event.resolved_at = world.tick
    save_event(session, event)

    director.update_tension_after_event(world, event, tpl)
    save_world(session, world)

    return event
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
from server.core.event_flow import run_event_cycle
from server.core.map_view import build_map_data
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.db.session import engine, ensure_schema
from server.models.db import EventRow, ItemRow, RewardRow, dumps, loads
from server.models.schemas import Event, NPC, Reward, World
from server.systems import inventory, item_use, relationship


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
        "version": "0.6.0",
        "docs": "/docs",
        "endpoints": [
            "/health", "/i18n", "/map",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/npc/{npc_id}/items",
            "/event", "/event/trigger",
            "/reward",
            "/item", "/item/{item_id}",
            "/item/{item_id}/give", "/item/{item_id}/take",
            "/item/{item_id}/use",
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
        result = []
        for r in rows:
            payload = loads(r.payload_json) or {}
            result.append({
                "id": r.id,
                "event_id": r.event_id,
                "kind": r.kind,
                "kind_label": i18n.reward_kind_label(r.kind),
                "value": r.value,
                "description": r.description,
                "payload": payload,
            })
        return result


# ---------- Item ----------

class GiveRequest(BaseModel):
    owner_id: str


class UseRequest(BaseModel):
    target_npc_id: str = ""


def _row_to_item(r: ItemRow, npc_names: dict[str, str]) -> dict:
    owner_id = r.owner_id or ""
    owner_label = ""
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

FILES["tests/test_inventory.py"] = r'''from sqlmodel import Session, SQLModel, create_engine

from server.models.db import ItemRow, dumps
from server.systems import inventory


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def _mk_item(session, item_id: str, owner: str = "") -> ItemRow:
    row = ItemRow(
        id=item_id,
        reward_id="rwd_x",
        event_id="evt_x",
        name="旧怀表",
        kind="饰物",
        affixes_json=dumps(["磨损的"]),
        story="x",
        value=0.3,
        owner_id=owner,
    )
    session.add(row)
    session.commit()
    return row


def test_give_and_list():
    engine = _engine()
    with Session(engine) as s:
        _mk_item(s, "itm_1", owner="")
        inventory.give_item(s, "itm_1", "npc_a")
        rows = inventory.list_items_by_owner(s, "npc_a")
        assert len(rows) == 1
        assert rows[0].id == "itm_1"


def test_take_item_to_player():
    engine = _engine()
    with Session(engine) as s:
        _mk_item(s, "itm_2", owner="npc_b")
        inventory.give_item(s, "itm_2", "player")
        rows = inventory.list_items_by_owner(s, "player")
        assert len(rows) == 1


def test_consume_hides_item():
    engine = _engine()
    with Session(engine) as s:
        _mk_item(s, "itm_3", owner="player")
        inventory.consume_item(s, "itm_3")
        rows = inventory.list_items_by_owner(s, "player")
        assert len(rows) == 0
        rows_all = inventory.list_items_by_owner(s, "player", include_consumed=True)
        assert len(rows_all) == 1
'''

FILES["tests/test_item_use.py"] = r'''import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_npc, save_world
from server.models.db import ItemRow, dumps
from server.models.schemas import NPC
from server.systems import item_use


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def _setup(s):
    world = create_world("test", seed=1)
    world.tick = 10
    save_world(s, world)
    save_npc(s, NPC(id="npc_a", name="Alden", age=30, goals=["g"]))
    row = ItemRow(
        id="itm_1",
        reward_id="rwd_1",
        event_id="evt_1",
        name="护身符",
        kind="信物",
        affixes_json=dumps(["粗糙的"]),
        story="护身",
        value=0.4,
        owner_id="player",
    )
    s.add(row)
    s.commit()
    return world


@pytest.mark.asyncio
async def test_use_item_fallback(monkeypatch):
    from server.systems import item_use as mod

    class FakeLLM:
        async def text_json(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(mod, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = _setup(s)
        result = await item_use.use_item(s, world, "itm_1", "player", "npc_a")
        assert result["ok"] is True
        assert "Alden" in result["effect"]


@pytest.mark.asyncio
async def test_use_consumes_when_llm_says(monkeypatch):
    from server.systems import item_use as mod

    class FakeLLM:
        async def text_json(self, prompt):
            return {
                "effect": "Alden 收下了护身符。",
                "relationship_change": {"trust": 0.2},
                "consume": True,
            }

    monkeypatch.setattr(mod, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = _setup(s)
        result = await item_use.use_item(s, world, "itm_1", "player", "npc_a")
        assert result["ok"] is True
        assert result["consumed"] is True

        from server.systems import inventory
        rows = inventory.list_items_by_owner(s, "player")
        assert len(rows) == 0
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

    print("\nPart 11 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()