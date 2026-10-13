"""FastAPI 入口。"""

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
from server.core.world import load_npcs, load_world, save_event, save_world
from server.db.session import engine, ensure_schema
from server.models.db import EventRow, ItemRow, MemoryRow, RewardRow, dumps, loads
from server.models.schemas import (
    ATTRIBUTE_META, DEFAULT_ATTRIBUTES, Event, NPC, Player, Reward, World,
)
from server.systems import inventory, item_use, relationship
from server.systems import player as player_sys
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
        "version": "1.1.0",
        "docs": "/docs",
        "embedding_enabled": settings.embedding_enabled,
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/i18n")
def i18n_endpoint() -> dict:
    return i18n.all_labels()


# ---------- Player ----------

@app.get("/player/attributes")
def get_attribute_defs() -> dict:
    return {"attributes": ATTRIBUTE_META, "defaults": DEFAULT_ATTRIBUTES}


def _player_to_response(session, p) -> dict:
    """把 Player 转成带 known_locations 的响应 dict。"""
    from server.map_layout import LOCATION_LAYOUT
    data = p.model_dump()

    world = load_world(session)
    discovered = list(world.location_ids or [])
    if "village_square" not in discovered:
        discovered.append("village_square")
    known = []
    for loc_id, layout in LOCATION_LAYOUT.items():
        is_hidden = bool(layout.get("hidden", False))
        if (not is_hidden) or loc_id in discovered:
            known.append({
                "id": loc_id,
                "label": i18n.location_label(loc_id),
                "current": loc_id == p.location_id,
            })
    data["known_locations"] = known
    return data


@app.get("/player")
def get_player() -> dict:
    with get_session() as s:
        p = player_sys.load_player(s)
        if p is None:
            return {"created": False}
        return _player_to_response(s, p)


class CreatePlayerRequest(BaseModel):
    name: str
    gender: str = "unknown"
    background: str = ""


@app.post("/player")
def create_player_endpoint(req: CreatePlayerRequest) -> dict:
    with get_session() as s:
        existing = player_sys.load_player(s)
        if existing is not None and existing.created:
            raise HTTPException(400, "player already created")
        p = player_sys.create_player(
            s, name=req.name, gender=req.gender, background=req.background,
        )
        return p.model_dump()


class AllocateRequest(BaseModel):
    attribute: str
    count: int = 1


@app.post("/player/allocate")
def allocate(req: AllocateRequest) -> dict:
    with get_session() as s:
        ok, err, p = player_sys.allocate_point(s, req.attribute, req.count)
        if not ok or p is None:
            raise HTTPException(400, err or "allocate failed")
        return _player_to_response(s, p)


# ---------- World ----------

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


def _npc_to_display(npc: NPC, npc_names: dict[str, str] | None = None) -> dict:
    names = npc_names or {}
    fam = npc.family
    family_info = {
        "spouse_id": fam.spouse,
        "spouse_name": names.get(fam.spouse, "") if fam.spouse else "",
        "children_ids": list(fam.children),
        "children_names": [names.get(c, c) for c in fam.children],
        "parents_ids": list(fam.parents),
        "parents_names": [names.get(p, p) for p in fam.parents],
        "siblings_ids": list(fam.siblings),
        "siblings_names": [names.get(s, s) for s in fam.siblings],
    }
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
        "family": family_info,
    }


@app.get("/npc")
def list_npcs() -> list[dict]:
    with get_session() as s:
        npcs = load_npcs(s)
        names = {n.id: n.name for n in npcs}
        return [_npc_to_display(n, names) for n in npcs]


@app.get("/npc/{npc_id}")
def get_npc(npc_id: str) -> dict:
    with get_session() as s:
        all_npcs = load_npcs(s)
        names = {n.id: n.name for n in all_npcs}
        npcs = {n.id: n for n in all_npcs}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return _npc_to_display(npcs[npc_id], names)


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


def _event_tags(template_id: str, payload: dict) -> list:
    """从 payload 或模板缓存里取 tags。"""
    payload_tags = payload.get("tpl_tags")
    if isinstance(payload_tags, list) and payload_tags:
        return list(payload_tags)

    # 从 director 的模板缓存里查
    try:
        from server.core import director
        for tpl in director.load_templates():
            if tpl.id == template_id:
                return list(tpl.tags)
    except Exception:
        pass

    # 玩家行动
    if template_id in ("explore", "gather", "hunt", "train", "socialize", "travel"):
        return ["action"]

    return []


def _row_to_event(r: EventRow, npc_names: dict[str, str]) -> dict:
    payload = loads(r.payload_json) or {}
    participants = loads(r.participants_json) or []
    participant_names = [npc_names.get(pid, pid) for pid in participants]
    choices = payload.get("choices") or []
    interactive = bool(payload.get("interactive", True))
    as_message = bool(payload.get("as_message", False))

    return {
        "id": r.id, "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": participants, "participant_names": participant_names,
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state, "state_label": i18n.state_label(r.state),
        "awaiting_player": r.state == "awaiting_player",
        "interactive": interactive, "payload": payload,
        "as_message": as_message,
        "summary": payload.get("summary") or "",
        "narrative": payload.get("narrative") or "",
        "choices": choices,
        "choice_made": payload.get("choice_made") or "",
        "choice_label": payload.get("choice_label") or "",
        "outcome": payload.get("outcome") or "",
        "check": payload.get("check") or {},
        "exp_gain": payload.get("exp_gain", 0),
        "rep_gain": payload.get("rep_gain", 0),
        "item_id": payload.get("item_id") or "",
        "item_owner": payload.get("item_owner") or "",
        "relevance_score": payload.get("relevance_score", 0.0),
        "tags": _event_tags(r.template_id, payload),
        "created_at": r.created_at, "resolved_at": r.resolved_at,
    }


@app.post("/explore")
async def explore_endpoint() -> dict:
    """探索一次：尝试发现新地点。"""
    from server.systems import explore as explore_sys

    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")

        # 推进 1 tick（探索消耗时间）
        tick(s, world)
        await check_timeouts(s, world)

        result = await explore_sys.explore_once(s, world, player)

        # 生成一条探索事件记录
        try:
            from server.models.schemas import Event as EventModel
            evt_id = "evt_exp_%s" % __import__("uuid").uuid4().hex[:8]
            summary = "你离开村庄四处探寻"
            if result.get("found_location"):
                summary = "你发现了【%s】" % str(result.get("target_label", ""))
            elif result.get("kind") == "no_more":
                summary = "附近的地界你已经走遍了"
            else:
                summary = "你四处探寻，但一无所获"

            evt = EventModel(
                id=evt_id,
                template_id="explore",
                participants=["player"],
                location_id=result.get("target_id", player.location_id),
                state="resolved",
                payload={
                    "summary": summary,
                    "narrative": str(result.get("flavor", "")),
                    "outcome": str(result.get("message", "")),
                    "check": result.get("check") or {},
                    "exp_gain": int(result.get("exp_gain", 0)),
                    "interactive": False,
                    "as_message": True,
                },
                created_at=world.tick,
                resolved_at=world.tick,
            )
            save_event(s, evt)
        except Exception as e:
            print("[explore] 事件记录失败：%s" % e)

        # 处理物品入库
        item_data = result.get("found_item")
        if item_data is not None:
            from server.models.db import ItemRow
            row = ItemRow(
                id=item_data["id"],
                reward_id="",
                event_id="",
                name=item_data.get("name", ""),
                kind=item_data.get("kind", ""),
                affixes_json=dumps(item_data.get("affixes", [])),
                story=item_data.get("story", ""),
                value=float(item_data.get("value", 0.0)),
                owner_id="player",
                consumed=False,
            )
            s.add(row)
            s.commit()

        save_world(s, world)
        result["tick"] = world.tick
        result["day"] = world.day
        result["hour"] = world.hour

        # 刷新的 player
        p2 = player_sys.load_player(s)
        if p2 is not None:
            result["player"] = p2.model_dump()

        return result


class ActionRequest(BaseModel):
    action: str


@app.post("/action")
async def action_endpoint(req: ActionRequest) -> dict:
    """执行一个玩家行动，同时推进世界 1 tick。"""
    from server.systems import actions as actions_sys
    import uuid as _uuid

    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")

        # 1. 玩家行动
        action_result = await actions_sys.do_action(s, world, player, req.action)

        # 2. 推进世界 1 tick
        tick(s, world)
        await check_timeouts(s, world)

        # 3. NPC 闲谈
        npcs = load_npcs(s)
        rng = random.Random(world.seed * 1000003 + world.tick * 7)
        social = await maybe_social_dialogue(s, world, npcs, rng)

        # 4. 世界事件
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=False)

        # 5. 记录玩家行动到 event 表
        try:
            from server.models.schemas import Event as EventModel
            evt_id = "evt_act_%s" % _uuid.uuid4().hex[:8]
            evt = EventModel(
                id=evt_id,
                template_id=req.action,
                participants=["player"],
                location_id=action_result.get("target_id") or player.location_id,
                state="resolved",
                payload={
                    "summary": action_result.get("summary", ""),
                    "narrative": action_result.get("flavor", ""),
                    "outcome": action_result.get("message", ""),
                    "check": action_result.get("check") or {},
                    "exp_gain": int(action_result.get("exp_gain", 0)),
                    "interactive": False,
                    "as_message": True,
                    "is_player_action": True,
                    "tpl_tags": ["action"],
                },
                created_at=world.tick,
                resolved_at=world.tick,
            )
            save_event(s, evt)
        except Exception as e:
            print("[action] 事件记录失败：%s" % e)

        # 6. 物品入库
        item_data = action_result.get("found_item")
        if item_data is not None:
            from server.models.db import ItemRow
            row = ItemRow(
                id=item_data["id"], reward_id="", event_id="",
                name=item_data.get("name", ""),
                kind=item_data.get("kind", ""),
                affixes_json=dumps(item_data.get("affixes", [])),
                story=item_data.get("story", ""),
                value=float(item_data.get("value", 0.0)),
                owner_id="player", consumed=False,
            )
            s.add(row)
            s.commit()

        save_world(s, world)

        p2 = player_sys.load_player(s)
        action_result["player"] = _player_to_response(s, p2) if p2 else {}
        action_result["tick"] = world.tick
        action_result["day"] = world.day
        action_result["hour"] = world.hour
        action_result["world_event"] = {
            "id": event.id,
            "summary": event.payload.get("summary"),
            "template_label": i18n.template_label(event.template_id),
            "awaiting_player": event.state == "awaiting_player",
        } if event else None
        action_result["social"] = social

        return action_result


class TravelRequest(BaseModel):
    location_id: str


@app.post("/travel")
async def travel_endpoint(req: TravelRequest) -> dict:
    """玩家移动到已发现的地点，消耗 1 tick。"""
    from server.map_layout import LOCATION_LAYOUT

    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")

        if req.location_id not in LOCATION_LAYOUT:
            raise HTTPException(400, "unknown location: %s" % req.location_id)

        layout = LOCATION_LAYOUT[req.location_id]
        is_visible = not layout.get("hidden", False)
        discovered = list(world.location_ids or [])
        if not is_visible and req.location_id not in discovered:
            raise HTTPException(400, "location not discovered: %s" % req.location_id)

        old_loc = player.location_id
        if old_loc == req.location_id:
            raise HTTPException(400, "already at that location")

        player.location_id = req.location_id
        player_sys.save_player(s, player)

        tick(s, world)
        await check_timeouts(s, world)

        # 记录到 event
        try:
            from server.models.schemas import Event as EventModel
            evt_id = "evt_go_%s" % _uuid.uuid4().hex[:8]
            evt = EventModel(
                id=evt_id,
                template_id="travel",
                participants=["player"],
                location_id=req.location_id,
                state="resolved",
                payload={
                    "summary": "你从%s前往%s" % (
                        i18n.location_label(old_loc),
                        i18n.location_label(req.location_id),
                    ),
                    "narrative": "",
                    "outcome": "",
                    "interactive": False,
                    "as_message": True,
                    "is_player_action": True,
                },
                created_at=world.tick,
                resolved_at=world.tick,
            )
            save_event(s, evt)
        except Exception as e:
            import traceback
            print("[travel] 事件记录失败：%s" % e)
            traceback.print_exc()

        save_world(s, world)
        p2 = player_sys.load_player(s)

        return {
            "ok": True,
            "from_id": old_loc,
            "from_label": i18n.location_label(old_loc),
            "to_id": req.location_id,
            "to_label": i18n.location_label(req.location_id),
            "player": _player_to_response(s, p2) if p2 else {},
            "tick": world.tick,
            "day": world.day,
            "hour": world.hour,
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
