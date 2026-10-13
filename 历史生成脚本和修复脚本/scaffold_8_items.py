r"""EmergentWorld scaffold - Part 8: 物品系统 + 物品查看 UI。

运行：
    python scaffold_8_items.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ db.py 加 ItemRow

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

# ================================================================ item 生成器

FILES["server/generators/item.py"] = r'''"""物品生成器：根据事件上下文生成实物。"""

from __future__ import annotations

import uuid

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label, template_label
from server.models.schemas import Event, World


def _fallback_item(event: Event, value: float) -> dict:
    tpl_zh = template_label(event.template_id)
    return {
        "id": "itm_%s" % uuid.uuid4().hex[:8],
        "name": "%s纪念品" % tpl_zh,
        "kind": "纪念品",
        "affixes": ["朴素的"],
        "story": "来自%s的纪念物。" % tpl_zh,
        "value": value,
    }


async def generate_item(
    event: Event,
    world: World,
    value: float,
) -> dict:
    """生成一件物品。返回 dict，字段与 Item schema 一致。"""
    summary = str(event.payload.get("summary", "")).strip()
    tpl_zh = template_label(event.template_id)
    loc_zh = location_label(event.location_id)

    prompt = load_prompt("item_gen.md").format(
        template_label=tpl_zh,
        summary=summary or "（无）",
        value=value,
        location_label=loc_zh,
    )

    item_id = "itm_%s" % uuid.uuid4().hex[:8]
    fallback = _fallback_item(event, value)

    try:
        raw = await get_llm().text_json(prompt)
        if not isinstance(raw, dict):
            return fallback

        name = str(raw.get("name", "")).strip()[:16]
        kind = str(raw.get("kind", "")).strip()[:16]
        affixes = raw.get("affixes", [])
        if not isinstance(affixes, list):
            affixes = []
        affixes = [str(a).strip()[:8] for a in affixes][:3]
        story = str(raw.get("story", "")).strip()[:120]

        if not name or not kind:
            return fallback

        return {
            "id": item_id,
            "name": name,
            "kind": kind,
            "affixes": affixes,
            "story": story,
            "value": float(value),
        }
    except Exception:
        return fallback
'''

# ================================================================ reward 覆盖

FILES["server/generators/reward.py"] = r'''"""奖励生成器：预算约束下的模板 + LLM 描述 + 物品。"""

from __future__ import annotations

import uuid

from server.generators.item import generate_item
from server.i18n import template_label
from server.models.schemas import Event, Reward, World


def compute_budget(event: Event, world: World, difficulty: float = 0.5) -> float:
    base = 0.3 + difficulty * 0.5
    return base * world.economy.reward_budget_multiplier


async def generate_reward(event: Event, world: World) -> Reward:
    budget = compute_budget(event, world)
    value = min(budget, 1.0)
    tpl_zh = template_label(event.template_id)

    # item 类型：生成真正的物品实体
    item = await generate_item(event, world, value)

    summary = str(event.payload.get("summary", "")).strip()
    if summary:
        description = "%s 的结局：%s" % (tpl_zh, summary[:40])
    else:
        description = "%s的奖励" % tpl_zh

    return Reward(
        id="rwd_%s" % uuid.uuid4().hex[:8],
        event_id=event.id,
        kind="item",
        value=value,
        description=description,
        payload={"item": item},
    )
'''

# ================================================================ prompt

FILES["server/prompts/item_gen.md"] = r'''你是游戏物品生成器。根据事件背景，生成一件与事件相关的物品。

**重要：所有输出必须使用简体中文。**

规则：
- 输出必须是合法 JSON
- 结构：{{"name": "物品名", "kind": "物品类别", "affixes": ["词缀1", "词缀2"], "story": "一小段来历"}}
- name 不超过 8 字
- kind 用简短类别名，如「信物」「遗物」「书籍」「饰物」「武器」「食物」
- affixes 生成 2-3 个，每个 2-4 字的形容词
- story 不超过 60 字，讲述物品与事件的关联
- 不要输出 markdown，不要输出解释

事件类型：{template_label}
事件摘要：{summary}
发生地点：{location_label}
价值档位：{value}（0-1，越高越珍贵）
'''

# ================================================================ event_flow 覆盖

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


def _save_item(session: Session, reward_id: str, event_id: str, item_data: dict) -> None:
    row = ItemRow(
        id=item_data["id"],
        reward_id=reward_id,
        event_id=event_id,
        name=item_data.get("name", ""),
        kind=item_data.get("kind", ""),
        affixes_json=dumps(item_data.get("affixes", [])),
        story=item_data.get("story", ""),
        value=float(item_data.get("value", 0.0)),
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
            _save_item(session, reward.id, event.id, item_data)
            event.payload["item_id"] = item_data["id"]

    event.state = "resolved"
    event.resolved_at = world.tick
    save_event(session, event)

    director.update_tension_after_event(world, event, tpl)
    save_world(session, world)

    return event
'''

# ================================================================ main.py 覆盖（加 /item）

FILES["server/main.py"] = r'''"""FastAPI 入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, select

from server import i18n
from server.api import routes_dialogue, routes_review
from server.config import settings
from server.core import director
from server.core.event_flow import run_event_cycle
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.db.session import engine
from server.models.db import EventRow, ItemRow, RewardRow, dumps, loads
from server.models.schemas import Event, NPC, Reward, World
from server.systems import relationship


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
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
        "version": "0.4.0",
        "docs": "/docs",
        "endpoints": [
            "/health", "/i18n",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/event", "/event/trigger",
            "/reward", "/item", "/item/{item_id}",
            "/review/latest",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/i18n")
def i18n_endpoint() -> dict:
    return i18n.all_labels()


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

def _row_to_item(r: ItemRow) -> dict:
    return {
        "id": r.id,
        "reward_id": r.reward_id,
        "event_id": r.event_id,
        "name": r.name,
        "kind": r.kind,
        "affixes": loads(r.affixes_json) or [],
        "story": r.story,
        "value": r.value,
    }


@app.get("/item")
def list_items(limit: int = 50) -> list[dict]:
    with get_session() as s:
        rows = s.exec(
            select(ItemRow).order_by(ItemRow.id.desc()).limit(limit)
        ).all()
        return [_row_to_item(r) for r in rows]


@app.get("/item/{item_id}")
def get_item(item_id: str) -> dict:
    with get_session() as s:
        row = s.get(ItemRow, item_id)
        if row is None:
            raise HTTPException(404, "item not found")
        return _row_to_item(row)
'''

# ================================================================ test

FILES["tests/test_item.py"] = r'''import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.generators.item import generate_item
from server.models.db import ItemRow, dumps, loads
from server.models.schemas import Event, World


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_generate_item_fallback(monkeypatch):
    from server.generators import item as item_mod

    class FakeLLM:
        async def text_json(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(item_mod, "get_llm", lambda: FakeLLM())

    event = Event(
        id="evt_1",
        template_id="merchant_arrives",
        participants=[],
        location_id="market",
        payload={"summary": "行商到访"},
    )
    item = await generate_item(event, World(id="w"), 0.5)
    assert item["id"].startswith("itm_")
    assert item["name"]
    assert item["value"] == 0.5


def test_item_row_roundtrip():
    engine = _engine()
    with Session(engine) as s:
        row = ItemRow(
            id="itm_test",
            reward_id="rwd_test",
            event_id="evt_test",
            name="旧怀表",
            kind="饰物",
            affixes_json=dumps(["磨损的", "停在子夜的"]),
            story="某位行商遗落。",
            value=0.42,
        )
        s.add(row)
        s.commit()
        loaded = s.get(ItemRow, "itm_test")
        assert loaded is not None
        assert loaded.name == "旧怀表"
        assert "停在子夜的" in (loads(loaded.affixes_json) or [])
'''

# ================================================================ 客户端主脚本

FILES["client/main.gd"] = r'''extends Control

var api: GameApi

var i18n_traits: Dictionary = {}
var i18n_needs: Dictionary = {}
var i18n_templates: Dictionary = {}
var i18n_locations: Dictionary = {}
var i18n_reward_kinds: Dictionary = {}
var i18n_states: Dictionary = {}

var status_label: Label
var npc_list: ItemList
var npc_detail: RichTextLabel
var relationship_label: RichTextLabel
var dialogue_log: RichTextLabel
var dialogue_input: LineEdit
var event_log: RichTextLabel
var reward_log: RichTextLabel
var item_log: RichTextLabel

var current_npc_id: String = ""
var npc_data: Dictionary = {}
var npc_order: Array[String] = []


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	api.fetch_i18n()


func _connect_signals() -> void:
	api.i18n_received.connect(_on_i18n_received)
	api.world_state_received.connect(_on_world_state)
	api.npc_list_received.connect(_on_npc_list)
	api.npc_detail_received.connect(_on_npc_detail)
	api.dialogue_received.connect(_on_dialogue)
	api.event_triggered.connect(_on_event_triggered)
	api.event_list_received.connect(_on_event_list)
	api.relationships_received.connect(_on_relationships)
	api.reward_list_received.connect(_on_reward_list)
	api.item_list_received.connect(_on_item_list)
	api.request_failed.connect(_on_request_failed)


func _tr(dict: Dictionary, key: String) -> String:
	if dict.has(key):
		return str(dict[key])
	return key


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

	var step_btn := Button.new()
	step_btn.text = "推进一 tick"
	step_btn.pressed.connect(func(): api.step_world())
	top.add_child(step_btn)

	var event_btn := Button.new()
	event_btn.text = "触发事件"
	event_btn.pressed.connect(func(): api.trigger_event())
	top.add_child(event_btn)

	var refresh_btn := Button.new()
	refresh_btn.text = "刷新"
	refresh_btn.pressed.connect(_refresh_all)
	top.add_child(refresh_btn)


func _build_left_panel(split: HSplitContainer) -> void:
	var panel := VBoxContainer.new()
	panel.custom_minimum_size = Vector2(260, 0)
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
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var detail_title := Label.new()
	detail_title.text = "人物档案"
	panel.add_child(detail_title)

	var detail_scroll := ScrollContainer.new()
	detail_scroll.custom_minimum_size = Vector2(0, 220)
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(detail_scroll)

	npc_detail = RichTextLabel.new()
	npc_detail.bbcode_enabled = true
	npc_detail.fit_content = true
	npc_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	npc_detail.text = "从左侧选择一位居民"
	detail_scroll.add_child(npc_detail)

	relationship_label = RichTextLabel.new()
	relationship_label.bbcode_enabled = true
	relationship_label.fit_content = true
	relationship_label.custom_minimum_size = Vector2(0, 80)
	panel.add_child(relationship_label)

	var dlg_title := Label.new()
	dlg_title.text = "对话"
	panel.add_child(dlg_title)

	var dlg_scroll := ScrollContainer.new()
	dlg_scroll.custom_minimum_size = Vector2(0, 140)
	dlg_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(dlg_scroll)

	dialogue_log = RichTextLabel.new()
	dialogue_log.bbcode_enabled = true
	dialogue_log.fit_content = true
	dialogue_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dlg_scroll.add_child(dialogue_log)

	var dlg_input_row := HBoxContainer.new()
	dlg_input_row.add_theme_constant_override("separation", 6)
	panel.add_child(dlg_input_row)

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
	tabs.tab_alignment = TabBar.ALIGNMENT_LEFT
	panel.add_child(tabs)

	# --- Tab 1: 编年史 ---
	var ev_scroll := ScrollContainer.new()
	ev_scroll.name = "编年史"
	tabs.add_child(ev_scroll)
	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ev_scroll.add_child(event_log)

	# --- Tab 2: 奖励 ---
	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.name = "奖励"
	tabs.add_child(rwd_scroll)
	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)

	# --- Tab 3: 物品 ---
	var item_scroll := ScrollContainer.new()
	item_scroll.name = "物品"
	tabs.add_child(item_scroll)
	item_log = RichTextLabel.new()
	item_log.bbcode_enabled = true
	item_log.fit_content = true
	item_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	item_scroll.add_child(item_log)


func _refresh_all() -> void:
	api.fetch_world_state()
	api.fetch_npcs()
	api.fetch_events(20)
	api.fetch_rewards(20)
	api.fetch_items(50)


func _on_i18n_received(data: Dictionary) -> void:
	i18n_traits = data.get("traits", {})
	i18n_needs = data.get("needs", {})
	i18n_templates = data.get("templates", {})
	i18n_locations = data.get("locations", {})
	i18n_reward_kinds = data.get("reward_kinds", {})
	i18n_states = data.get("states", {})
	_refresh_all()


func _on_world_state(data: Dictionary) -> void:
	var director = data.get("director", {})
	var tension: float = 0.0
	if director is Dictionary:
		tension = float(director.get("tension", 0.0))
	status_label.text = "第 %d 天  %02d:00   Tick %d   张力 %.2f" % [
		int(data.get("day", 0)),
		int(data.get("hour", 0)),
		int(data.get("tick", 0)),
		tension,
	]


func _on_npc_list(data: Array) -> void:
	npc_data.clear()
	npc_order.clear()
	npc_list.clear()
	for npc in data:
		if not npc is Dictionary:
			continue
		var id: String = str(npc.get("id", ""))
		var name: String = str(npc.get("name", "?"))
		var loc: String = str(npc.get("location_label", ""))
		npc_data[id] = npc
		npc_order.append(id)
		npc_list.add_item("%s   @ %s" % [name, loc])


func _on_npc_selected(index: int) -> void:
	if index < 0 or index >= npc_order.size():
		return
	current_npc_id = npc_order[index]
	api.fetch_npc_detail(current_npc_id)
	api.fetch_relationships(current_npc_id)
	var name: String = str(npc_data[current_npc_id].get("name", "?"))
	dialogue_log.text = "[i]你走近 %s...[/i]" % name


func _on_npc_detail(data: Dictionary) -> void:
	var lines: Array[String] = []
	lines.append("[b][color=yellow]%s[/color][/b]   %d 岁" % [
		str(data.get("name", "?")),
		int(data.get("age", 0)),
	])
	lines.append("所在地：%s" % str(data.get("location_label", "")))
	lines.append("")

	lines.append("[b]性格[/b]")
	var traits: Array = data.get("traits", [])
	for t in traits:
		if t is Dictionary:
			lines.append("   %s：%.2f" % [
				str(t.get("label", t.get("key", "?"))),
				float(t.get("value", 0)),
			])

	lines.append("")
	lines.append("[b]需求[/b]")
	var needs: Array = data.get("needs", [])
	for n in needs:
		if n is Dictionary:
			lines.append("   %s：%.2f" % [
				str(n.get("label", n.get("key", "?"))),
				float(n.get("value", 0)),
			])

	lines.append("")
	lines.append("[b]目标[/b]")
	var goals: Array = data.get("goals", [])
	for g in goals:
		lines.append("   · %s" % str(g))

	npc_detail.text = "\n".join(lines)


func _on_relationships(data: Array) -> void:
	if data.is_empty():
		relationship_label.text = "[i]（暂无关系记录）[/i]"
		return
	var lines: Array[String] = ["[b]关系[/b]"]
	for r in data:
		if not r is Dictionary:
			continue
		var other_name: String = str(r.get("other_name", r.get("other_id", "?")))
		lines.append("   %s   信任 %+.2f   好感 %+.2f   恐惧 %+.2f   债务 %+.2f" % [
			other_name,
			float(r.get("trust", 0)),
			float(r.get("affection", 0)),
			float(r.get("fear", 0)),
			float(r.get("debt", 0)),
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
	if data.has("event_summary") and data.get("event_summary") != null:
		var summary: String = str(data.get("event_summary", ""))
		var tpl_label: String = str(data.get("template_label", ""))
		if summary != "":
			event_log.append_text("\n[color=orange]→[/color] [b]%s[/b] %s" % [tpl_label, summary])
	_refresh_all()


func _on_event_list(data: Array) -> void:
	event_log.clear()
	for e in data:
		if not e is Dictionary:
			continue
		var state: String = str(e.get("state", ""))
		var state_zh: String = str(e.get("state_label", state))
		var color := "white"
		if state == "resolved":
			color = "lightgreen"
		elif state == "rejected":
			color = "gray"
		elif state == "active":
			color = "yellow"

		var tpl_label: String = str(e.get("template_label", e.get("template_id", "?")))
		var summary: String = str(e.get("summary", ""))
		var loc_label: String = str(e.get("location_label", ""))

		event_log.append_text("[color=%s]·[/color] [b]%s[/b]（%s，%s）\n    %s\n\n" % [
			color, tpl_label, loc_label, state_zh, summary,
		])


func _on_reward_list(data: Array) -> void:
	reward_log.clear()
	for r in data:
		if not r is Dictionary:
			continue
		var kind_label: String = str(r.get("kind_label", r.get("kind", "?")))
		reward_log.append_text("[b]%s[/b]  %.2f  %s\n" % [
			kind_label,
			float(r.get("value", 0)),
			str(r.get("description", "")),
		])


func _on_item_list(data: Array) -> void:
	item_log.clear()
	if data.is_empty():
		item_log.text = "[i]还没有获得任何物品[/i]"
		return
	for it in data:
		if not it is Dictionary:
			continue
		var name: String = str(it.get("name", "?"))
		var kind: String = str(it.get("kind", ""))
		var affixes: Array = it.get("affixes", [])
		var story: String = str(it.get("story", ""))
		var value: float = float(it.get("value", 0))

		var title := "[b][color=gold]%s[/color][/b]" % name
		if kind != "":
			title += "  [i](%s)[/i]" % kind
		item_log.append_text(title + "\n")

		if not affixes.is_empty():
			var affix_strs: Array[String] = []
			for a in affixes:
				affix_strs.append(str(a))
			item_log.append_text("    词缀：%s\n" % ", ".join(affix_strs))

		if story != "":
			item_log.append_text("    [color=lightgray]%s[/color]\n" % story)

		item_log.append_text("    价值：%.2f\n\n" % value)


func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error
'''

# ================================================================ 客户端 api.gd 加 item

FILES["client/api.gd"] = '''class_name GameApi
extends Node

const BASE_URL := "http://127.0.0.1:8000"

signal i18n_received(data: Dictionary)
signal world_state_received(data: Dictionary)
signal npc_list_received(data: Array)
signal npc_detail_received(data: Dictionary)
signal dialogue_received(data: Dictionary)
signal event_triggered(data: Dictionary)
signal event_list_received(data: Array)
signal relationships_received(data: Array)
signal reward_list_received(data: Array)
signal item_list_received(data: Array)
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


func send_dialogue(npc_id: String, player_input: String) -> void:
	_request("POST", "/npc/%s/dialogue" % npc_id, {"player_input": player_input}, "dialogue_received")


func fetch_events(limit: int = 20) -> void:
	_request("GET", "/event?limit=%d" % limit, {}, "event_list_received")


func fetch_rewards(limit: int = 20) -> void:
	_request("GET", "/reward?limit=%d" % limit, {}, "reward_list_received")


func fetch_items(limit: int = 50) -> void:
	_request("GET", "/item?limit=%d" % limit, {}, "item_list_received")


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
		var body_str := JSON.stringify(body)
		err = http.request(url, headers, HTTPClient.METHOD_POST, body_str)

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
	var data = JSON.parse_string(text)

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

    print("\nPart 8 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()