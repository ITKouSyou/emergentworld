r"""EmergentWorld scaffold - Part 7: 中文本地化。

运行：
    python scaffold_7_i18n.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ i18n

FILES["server/i18n.py"] = r'''"""中文本地化字典。所有显示层的英文 key → 中文标签映射。

未来加英文支持时，把这里的 value 换成多语言字典即可。
"""

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
    "resolved": "已完成",
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

# ================================================================ 覆盖 event.py

FILES["server/generators/event.py"] = r'''"""事件生成器：模板 + LLM 填充 + 规则兜底。"""

from __future__ import annotations

import random
import uuid

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label, template_label
from server.models.schemas import Event, EventTemplate, NPC, World


def _pick_participants(tpl: EventTemplate, npcs: list[NPC], rng: random.Random) -> list[str]:
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _fallback_payload(tpl: EventTemplate, location: str, participants: list[NPC]) -> dict:
    names = "、".join(p.name for p in participants) or "无人"
    loc_zh = location_label(location)
    tpl_zh = template_label(tpl.id)
    return {
        "summary": "在%s发生了%s，涉及%s。" % (loc_zh, tpl_zh, names),
        "narrative": "（LLM 未返回，使用模板兜底。）",
    }


async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
) -> Event:
    participants_ids = _pick_participants(tpl, npcs, rng)
    participants = [n for n in npcs if n.id in participants_ids]
    location = tpl.params.get("location", "village_square")

    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        template_label=template_label(tpl.id),
        prompt=tpl.prompt,
        participants=", ".join("%s(%s)" % (p.name, p.id) for p in participants) or "无",
        location=location,
        location_label=location_label(location),
        day=world.day,
    )
    fallback = _fallback_payload(tpl, location, participants)

    payload = fallback
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            candidate = raw.get("payload") if "payload" in raw else raw
            if isinstance(candidate, dict) and candidate.get("summary"):
                payload = {
                    "summary": str(candidate.get("summary", ""))[:300],
                    "narrative": str(candidate.get("narrative", ""))[:800],
                }
    except Exception:
        payload = fallback

    return Event(
        id="evt_%s" % uuid.uuid4().hex[:8],
        template_id=tpl.id,
        participants=participants_ids,
        location_id=location,
        state="pending",
        payload=payload,
        created_at=world.tick,
    )
'''

# ================================================================ 覆盖 reward.py

FILES["server/generators/reward.py"] = r'''"""奖励生成器：预算约束下的中文描述。"""

from __future__ import annotations

import uuid

from server.i18n import template_label
from server.models.schemas import Event, Reward, World


def compute_budget(event: Event, world: World, difficulty: float = 0.5) -> float:
    base = 0.3 + difficulty * 0.5
    return base * world.economy.reward_budget_multiplier


async def generate_reward(event: Event, world: World) -> Reward:
    budget = compute_budget(event, world)
    value = min(budget, 1.0)
    tpl_zh = template_label(event.template_id)

    # 优先用事件 summary 里已有的信息做描述
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
        payload={},
    )
'''

# ================================================================ 覆盖 prompt

FILES["server/prompts/event_fill.md"] = r'''你是游戏事件填充器。给定一个事件模板与世界上下文，生成事件细节。

**重要：所有输出必须使用简体中文，不要用英文。**

规则：
- 输出必须是合法 JSON
- 顶层键为 payload，payload 内含 summary 与 narrative
- summary：一句话概述，不超过 40 字
- narrative：2-4 句细节描述，符合世界氛围，用中文
- 不要改变参与者与地点
- 不要输出 markdown

模板 ID：{template_id}
模板名称：{template_label}
模板提示：{prompt}
参与者：{participants}
地点：{location}（{location_label}）
当前天数：{day}
'''

# ================================================================ 覆盖 main.py（加 /i18n）

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
from server.models.db import EventRow, RewardRow, dumps, loads
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
        "version": "0.3.0",
        "docs": "/docs",
        "endpoints": [
            "/health", "/i18n",
            "/world/state", "/world/tick", "/world/step",
            "/npc", "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue", "/npc/{npc_id}/relationships",
            "/event", "/event/trigger",
            "/reward", "/review/latest",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/i18n")
def i18n_endpoint() -> dict:
    """返回所有中文标签映射，供客户端显示层使用。"""
    return i18n.all_labels()


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
        }


# ---------- NPC ----------

def _npc_to_display(npc: NPC) -> dict:
    """把 NPC 转成客户端友好的结构，附带中文标签。"""
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
        "raw": {
            "traits": npc.traits,
            "needs": npc.needs,
            "behavior_profile": npc.behavior_profile,
            "asset_params": npc.asset_params,
        },
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


# ---------- 事件 ----------

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
        return {
            "id": event.id,
            "template_id": event.template_id,
            "template_label": i18n.template_label(event.template_id),
            "participants": event.participants,
            "location_id": event.location_id,
            "location_label": i18n.location_label(event.location_id),
            "state": event.state,
            "state_label": i18n.state_label(event.state),
            "payload": event.payload,
            "summary": event.payload.get("summary", ""),
            "narrative": event.payload.get("narrative", ""),
            "created_at": event.created_at,
            "resolved_at": event.resolved_at,
        }


# ---------- 奖励 ----------

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
'''

# ================================================================ 覆盖 client/main.gd

FILES["client/main.gd"] = r'''extends Control

var api: GameApi

# i18n 字典（启动时从后端拉取）
var i18n_traits: Dictionary = {}
var i18n_needs: Dictionary = {}
var i18n_templates: Dictionary = {}
var i18n_locations: Dictionary = {}
var i18n_reward_kinds: Dictionary = {}
var i18n_states: Dictionary = {}
var i18n_loaded: bool = false

var status_label: Label
var npc_list: ItemList
var npc_detail: RichTextLabel
var relationship_label: RichTextLabel
var dialogue_log: RichTextLabel
var dialogue_input: LineEdit
var event_log: RichTextLabel
var reward_log: RichTextLabel

var current_npc_id: String = ""
var npc_data: Dictionary = {}
var npc_order: Array[String] = []


func _ready() -> void:
	api = GameApi.new()
	add_child(api)
	_connect_signals()
	_build_ui()
	# 先拉 i18n，再拉数据
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
	api.request_failed.connect(_on_request_failed)


func _tr(dict: Dictionary, key: String) -> String:
	# 从 i18n 字典取值，没有就用原 key
	if dict.has(key):
		return str(dict[key])
	return key


func _trait(k: String) -> String:
	return _tr(i18n_traits, k)


func _need(k: String) -> String:
	return _tr(i18n_needs, k)


func _template(k: String) -> String:
	return _tr(i18n_templates, k)


func _location(k: String) -> String:
	return _tr(i18n_locations, k)


func _reward_kind(k: String) -> String:
	return _tr(i18n_reward_kinds, k)


func _state(k: String) -> String:
	return _tr(i18n_states, k)


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
	panel.custom_minimum_size = Vector2(400, 0)
	panel.add_theme_constant_override("separation", 6)
	split.add_child(panel)

	var title := Label.new()
	title.text = "编年史"
	panel.add_child(title)

	var ev_scroll := ScrollContainer.new()
	ev_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(ev_scroll)

	event_log = RichTextLabel.new()
	event_log.bbcode_enabled = true
	event_log.fit_content = true
	event_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ev_scroll.add_child(event_log)

	var rwd_title := Label.new()
	rwd_title.text = "最近奖励"
	panel.add_child(rwd_title)

	var rwd_scroll := ScrollContainer.new()
	rwd_scroll.custom_minimum_size = Vector2(0, 120)
	panel.add_child(rwd_scroll)

	reward_log = RichTextLabel.new()
	reward_log.bbcode_enabled = true
	reward_log.fit_content = true
	reward_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rwd_scroll.add_child(reward_log)


func _refresh_all() -> void:
	api.fetch_world_state()
	api.fetch_npcs()
	api.fetch_events(20)
	api.fetch_rewards(10)


func _on_i18n_received(data: Dictionary) -> void:
	i18n_traits = data.get("traits", {})
	i18n_needs = data.get("needs", {})
	i18n_templates = data.get("templates", {})
	i18n_locations = data.get("locations", {})
	i18n_reward_kinds = data.get("reward_kinds", {})
	i18n_states = data.get("states", {})
	i18n_loaded = true
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
	api.fetch_world_state()
	api.fetch_events(20)
	api.fetch_rewards(10)
	api.fetch_npcs()


func _on_event_list(data: Array) -> void:
	event_log.clear()
	for e in data:
		if not e is Dictionary:
			continue
		var state: String = str(e.get("state", ""))
		var state_zh: String = str(e.get("state_label", _state(state)))
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
		var kind_label: String = str(r.get("kind_label", _reward_kind(str(r.get("kind", "?")))))
		reward_log.append_text("[b]%s[/b]  %.2f  %s\n" % [
			kind_label,
			float(r.get("value", 0)),
			str(r.get("description", "")),
		])


func _on_request_failed(endpoint: String, error: String) -> void:
	push_warning("Request failed: %s -> %s" % [endpoint, error])
	status_label.text = "[color=red]错误：%s[/color]" % error
'''

# ================================================================ client/api.gd 加 i18n

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

# ================================================================ test

FILES["tests/test_i18n.py"] = r'''from server import i18n


def test_trait_labels_cover_default_keys():
    from server.generators.npc import TRAIT_KEYS, NEED_KEYS
    for k in TRAIT_KEYS:
        assert k in i18n.TRAIT_LABELS, "missing trait label: " + k
    for k in NEED_KEYS:
        assert k in i18n.NEED_LABELS, "missing need label: " + k


def test_template_labels_cover_templates():
    import yaml
    from pathlib import Path
    for p in Path("content/templates/events").glob("*.yaml"):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        tid = data.get("id", "")
        assert tid in i18n.TEMPLATE_LABELS, "missing template label: " + tid


def test_all_labels_returns_all_buckets():
    labels = i18n.all_labels()
    for key in ["traits", "needs", "templates", "locations", "reward_kinds", "states"]:
        assert key in labels
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

    print("\nPart 7 done. written=%d skipped=%d" % (written, skipped))
    print()
    print("下一步：")
    print("  1. pytest -v")
    print("  2. 重启后端 uvicorn server.main:app --reload")
    print("  3. Godot 中按 F5 重启客户端")


if globals().get('__name__') == '__main__':
    main()