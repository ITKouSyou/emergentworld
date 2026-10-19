"""FastAPI 入口。"""

from __future__ import annotations

import asyncio
import zlib
import struct
import random
import uuid as _uuid
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Body
import asyncio
import random

INIT_STATE = {
    "status": "idle", # idle, generating, done
    "current": 0,
    "total": 14,
    "message": "正在准备..."
}

async def _background_init():
    """后台生成村民，不阻塞服务器启动"""
    from server.generators.npc import generate_npc
    from server.core.world import save_npc, load_world
    from server.systems.family import build_families
    from server.systems.schedule import generate_schedule
    from server.systems.faction import assign_all_factions
    from server.db.session import engine
    from sqlmodel import Session
    
    INIT_STATE["status"] = "generating"
    MALE_NAMES = ["张铁柱", "李大山", "王二狗", "赵石", "陈望", "刘长河", "孙远", "周慎"]
    FEMALE_NAMES = ["李秀兰", "王桂花", "赵小梅", "陈阿娇", "刘翠", "孙玉"]
    
    npcs = []
    total = len(MALE_NAMES) + len(FEMALE_NAMES)
    INIT_STATE["total"] = total
    
    # 生成男的
    for i, name in enumerate(MALE_NAMES):
        INIT_STATE["message"] = f"正在生成村民：{name}..."
        npc = await generate_npc(name, context="一个偏远村庄", gender="male")
        with Session(engine) as session:
            save_npc(session, npc)
            _generate_local_avatar(npc.id, npc.name)
        npcs.append(npc)
        INIT_STATE["current"] += 1
        
    # 生成女的
    for i, name in enumerate(FEMALE_NAMES):
        INIT_STATE["message"] = f"正在生成村民：{name}..."
        npc = await generate_npc(name, context="一个偏远村庄", gender="female")
        with Session(engine) as session:
            save_npc(session, npc)
            _generate_local_avatar(npc.id, npc.name)
        npcs.append(npc)
        INIT_STATE["current"] += 1
        
    INIT_STATE["message"] = "正在建立家庭与派系关系..."
    with Session(engine) as session:
        rng = random.Random(42)
        build_families(session, npcs, rng)
        for npc in npcs:
            npc.schedule = generate_schedule(npc, rng)
            save_npc(session, npc)
        assign_all_factions(session)
        
    INIT_STATE["status"] = "done"
    INIT_STATE["message"] = "世界生成完毕！"


from fastapi.staticfiles import StaticFiles
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


def _generate_local_avatar(npc_id: str, name: str):
    import zlib
    import struct
    import random
    from pathlib import Path
    
    avatar_dir = Path("content/assets/avatars")
    avatar_dir.mkdir(parents=True, exist_ok=True)
    target = avatar_dir / f"{npc_id}.png"
    if target.exists():
        return
        
    # 生成一个 32x32 的像素小人头像
    rng = random.Random(hash(name) & 0xFFFF)
    
    # 色板
    bg_color = (rng.randint(20, 60), rng.randint(20, 60), rng.randint(20, 60))
    skin_color = (rng.randint(220, 255), rng.randint(170, 220), rng.randint(130, 180))
    hair_color = (rng.randint(20, 100), rng.randint(20, 100), rng.randint(20, 100))
    shirt_color = (rng.randint(50, 200), rng.randint(50, 200), rng.randint(50, 200))
    
    size = 32
    raw_data = b''
    for y in range(size):
        raw_data += b'\x00'  # filter type
        for x in range(size):
            # 背景
            color = bg_color
            
            # 衣服 (下半部分)
            if 20 <= y <= 31 and 6 <= x <= 25:
                color = shirt_color
            # 头 (圆形)
            elif (x - 16)**2 + (y - 14)**2 < 64:
                color = skin_color
                # 头发 (上半部分)
                if y < 12:
                    color = hair_color
            # 眼睛
            elif 12 <= y <= 14 and (x == 11 or x == 21):
                color = (0, 0, 0)
                
            raw_data += struct.pack('BBB', *color)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    header = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(raw_data))
    iend = chunk(b'IEND', b'')
    
    target.write_bytes(header + ihdr + idat + iend)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    ensure_schema()
    with Session(engine) as session:
        load_world(session)
        from sqlmodel import select
        from server.models.db import NPCRow
        npc_count = len(session.exec(select(NPCRow)).all())
        
    if npc_count == 0:
        asyncio.create_task(_background_init())
    else:
        INIT_STATE["status"] = "done"
        INIT_STATE["current"] = INIT_STATE["total"]
        
    yield


app = FastAPI(title="EmergentWorld", lifespan=lifespan)

# 静态资源挂载
from pathlib import Path as _Path
_avatar_dir = _Path("content/assets/avatars")
_avatar_dir.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(_avatar_dir)), name="avatars")
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



@app.get("/init/status")
def get_init_status():
    return INIT_STATE

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
    from server.systems import equipment as equip_sys
    data = p.model_dump()
    # 装备加成后的最终属性
    try:
        data["total_attributes"] = equip_sys.compute_total_attributes(session, p.attributes)
        data["equipment_slots"] = equip_sys.equipped_summary(session)
    except Exception as e:
        data["total_attributes"] = p.attributes
        data["equipment_slots"] = []

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
        try:
            event = await asyncio.wait_for(
                run_event_cycle(s, world, templates, force=False),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            print("[world_step] 事件生成超时（60s），跳过本次事件")
            event = None
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


def _impressions_for_npc(session, npc_id: str) -> list:
    try:
        from server.systems import impression as impr_sys
        return impr_sys.describe_for_ui(session, npc_id)
    except Exception:
        return []


def _npc_to_display(npc: NPC, npc_names: dict[str, str] | None = None) -> dict:
    names = npc_names or {}
    fam = npc.family
    from server.systems import schedule as _sched_sys
    schedule_lines = _sched_sys.describe_schedule(npc)
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
    avatar_url = "/avatars/%s.png" % npc.id
    return {
        "id": npc.id, "name": npc.name, "age": npc.age,
        "gender": npc.gender,
        "gender_label": i18n.gender_label(npc.gender),
        "avatar_url": avatar_url,
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
        "schedule": schedule_lines,
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
        result = _npc_to_display(npcs[npc_id], names)
        result["impressions"] = _impressions_for_npc(s, npc_id)
        # 派系
        try:
            from server.systems import faction as faction_sys
            npc = npcs[npc_id]
            if npc.faction and npc.faction != "neutral":
                meta = faction_sys.FACTIONS.get(npc.faction, {})
                result["faction"] = npc.faction
                result["faction_label"] = meta.get("label", npc.faction)
            else:
                result["faction"] = "neutral"
                result["faction_label"] = "中立"
        except Exception:
            pass
        return result


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

        # 5.5 目标记录
        try:
            from server.systems import goal as goal_sys
            goal_sys.ensure_daily_goals(s, world, random.Random(world.seed + world.day))
            goal_sys.ensure_milestones(s, world)

            # 根据行动和结果映射
            action_name = req.action
            found_item = action_result.get("found_item") is not None
            record_action = None
            if action_name == "hunt" and found_item:
                record_action = "hunt_success"
            elif action_name == "gather":
                record_action = "gather"
            elif action_name == "train":
                record_action = "train"
            elif action_name == "socialize":
                record_action = "socialize"
            elif action_name == "explore":
                record_action = "explore"

            if record_action:
                goal_sys.record_action(s, world, player, record_action, 1)
        except Exception as e:
            import traceback
            print("[action] 目标记录失败：%s" % e)
            traceback.print_exc()

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
    import uuid as _uuid
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

        # 检查任务完成
        completed_quests = []
        try:
            from server.systems import quest as quest_sys
            p_for_check = player_sys.load_player(s)
            if p_for_check is not None:
                completed_quests = quest_sys.check_location_completion(s, world, p_for_check)
                quest_sys.check_ready_to_turn_in(s, p_for_check)
        except Exception as e:
            import traceback
            print("[travel] 任务完成检查失败：%s" % e)
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
            "completed_quests": completed_quests,
        }


# ---------- Market ----------

@app.get("/market")
def market_view() -> dict:
    import random as _r
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        rng = _r.Random(world.seed * 77777 + world.tick * 3)
        from server.systems import market as market_sys
        goods = market_sys.get_market_inventory(world, rng, session=s)

        # 玩家可卖物品
        my_items = inventory.list_items_by_owner(s, "player")
        sell_list = []
        for r in my_items:
            price = market_sys.sell_price(r.value, world)
            sell_list.append({
                "id": r.id,
                "name": r.name,
                "kind": r.kind,
                "value": r.value,
                "sell_price": price,
            })

        return {
            "season": world.season,
            "season_label": i18n.season_label(world.season),
            "season_mult": market_sys.SEASON_PRICE_MULT.get(world.season, 1.0),
            "player_money": player.money,
            "goods": goods,
            "sell_list": sell_list,
        }


class SellRequest(BaseModel):
    item_id: str


@app.post("/trade/sell")
def trade_sell(req: SellRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import market as market_sys
        result = market_sys.sell_item(s, world, player, req.item_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "sell failed"))

        # 记录目标
        try:
            from server.systems import goal as goal_sys
            import random as _r
            goal_sys.ensure_daily_goals(s, world, _r.Random(world.seed + world.day))
            goal_sys.ensure_milestones(s, world)
            p2 = player_sys.load_player(s)
            if p2 is not None:
                goal_sys.record_action(s, world, p2, "earn_money",
                                       int(result.get("price", 0)))
        except Exception as e:
            print("[sell] 目标记录失败：%s" % e)

        return result


class BuyRequest(BaseModel):
    name: str
    kind: str
    price: int
    base_value: float


@app.post("/trade/buy")
def trade_buy(req: BuyRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import market as market_sys
        result = market_sys.buy_item(
            s, world, player,
            name=req.name, kind=req.kind,
            price=req.price, base_value=req.base_value,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "buy failed"))
        return result


# ---------- Goals ----------

@app.get("/goal")
def goal_list() -> dict:
    with get_session() as s:
        world = load_world(s)
        from server.systems import goal as goal_sys
        import random as _r
        rng = _r.Random(world.seed + world.day)
        goal_sys.ensure_daily_goals(s, world, rng)
        goal_sys.ensure_milestones(s, world)
        return goal_sys.list_all(s)


class ClaimRequest(BaseModel):
    goal_id: str


@app.post("/goal/claim")
def goal_claim(req: ClaimRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import goal as goal_sys
        result = goal_sys.claim_goal(s, world, player, req.goal_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "claim failed"))
        p2 = player_sys.load_player(s)
        result["player"] = _player_to_response(s, p2) if p2 else {}
        return result


@app.post("/goal/reset")
def goal_reset() -> dict:
    """清空所有目标并重建（用于调试或老数据修复）。"""
    from sqlmodel import delete
    from server.models.db import GoalRow
    with get_session() as s:
        s.exec(delete(GoalRow))
        s.commit()
        world = load_world(s)
        from server.systems import goal as goal_sys
        import random as _r
        rng = _r.Random(world.seed + world.day)
        goal_sys.ensure_daily_goals(s, world, rng)
        goal_sys.ensure_milestones(s, world)
        return {"ok": True, "reset": True}


# ---------- Quests ----------

@app.get("/quest")
def quest_list(limit: int = 30) -> list[dict]:
    with get_session() as s:
        from server.systems import quest as quest_sys
        from server.core.world import load_npcs as _load_npcs
        npc_names = {n.id: n.name for n in _load_npcs(s)}
        rows = quest_sys.list_all(s, limit=limit)
        return [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "kind": q.kind,
                "state": q.state,
                "progress": q.progress,
                "progress_target": q.progress_target,
                "giver_npc_id": q.giver_npc_id,
                "giver_name": npc_names.get(q.giver_npc_id, ""),
                "target_location_id": q.target_location_id,
                "target_location_label": i18n.location_label(q.target_location_id) if q.target_location_id else "",
                "reward_exp": q.reward_exp,
                "reward_money": q.reward_money,
                "created_tick": q.created_tick,
                "completed_tick": q.completed_tick,
                "require_item_kind": getattr(q, "require_item_kind", "") or "",
                "require_item_count": getattr(q, "require_item_count", 0),
            }
            for q in rows
        ]


class AbandonRequest(BaseModel):
    quest_id: str


@app.post("/quest/abandon")
def quest_abandon(req: AbandonRequest) -> dict:
    with get_session() as s:
        from server.systems import quest as quest_sys
        result = quest_sys.abandon_quest(s, req.quest_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "abandon failed"))
        return result


@app.get("/faction")
def faction_status() -> dict:
    with get_session() as s:
        from server.systems import faction as faction_sys
        return {
            "factions": faction_sys.player_rep_summary(s),
            "market_discount": faction_sys.market_discount(s),
        }


# ---------- Crafting ----------

@app.get("/craft/recipes")
def list_recipes() -> list[dict]:
    with get_session() as s:
        from server.systems import crafting as craft_sys
        return craft_sys.list_available_recipes(s, "player")


class CraftRequest(BaseModel):
    recipe_id: str


@app.post("/craft")
def do_craft(req: CraftRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import crafting as craft_sys
        result = craft_sys.craft(s, world, player, req.recipe_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "craft failed"))
        return result


# ---------- Equipment ----------

class EquipRequest(BaseModel):
    item_id: str


class UnequipRequest(BaseModel):
    slot: str


@app.post("/equip")
def equip_endpoint(req: EquipRequest) -> dict:
    with get_session() as s:
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import equipment as equip_sys
        result = equip_sys.equip(s, player, req.item_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "equip failed"))
        return result


@app.post("/unequip")
def unequip_endpoint(req: UnequipRequest) -> dict:
    with get_session() as s:
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import equipment as equip_sys
        result = equip_sys.unequip(s, player, req.slot)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "unequip failed"))
        return result


@app.get("/equipment")
def get_equipment() -> dict:
    with get_session() as s:
        from server.systems import equipment as equip_sys
        return {"slots": equip_sys.equipped_summary(s)}


@app.get("/npc/{npc_id}/quests")
def npc_offerable_quests(npc_id: str) -> list[dict]:
    with get_session() as s:
        from server.systems import quest as quest_sys
        items = quest_sys.get_offerable_quests(s, npc_id)
        # 补 location_label
        for it in items:
            it["require_location_label"] = i18n.location_label(it["require_location"])
        return items


class AcceptQuestRequest(BaseModel):
    quest_def_id: str


@app.post("/npc/{npc_id}/quests/accept")
def accept_quest_endpoint(npc_id: str, req: AcceptQuestRequest) -> dict:
    with get_session() as s:
        world = load_world(s)
        from server.systems import quest as quest_sys
        result = quest_sys.accept_quest(s, world, npc_id, req.quest_def_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "accept failed"))
        return result


@app.post("/quest/{quest_id}/turn_in")
def quest_turn_in(quest_id: str) -> dict:
    with get_session() as s:
        world = load_world(s)
        from server.systems import quest as quest_sys
        result = quest_sys.turn_in_quest(s, world, quest_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "turn in failed"))
        # 返回更新后的 player
        p2 = player_sys.load_player(s)
        result["player"] = _player_to_response(s, p2) if p2 else {}
        return result


@app.get("/npc/{npc_id}/active_quests")
def npc_active_quests(npc_id: str) -> list[dict]:
    with get_session() as s:
        from server.systems import quest as quest_sys
        return quest_sys.list_npc_active_quests(s, npc_id)


# ---------- Save ----------

@app.get("/save/list")
def save_list() -> list[dict]:
    from server.systems import save_manager
    return save_manager.list_saves()


@app.get("/save/current")
def save_current() -> dict:
    from server.systems import save_manager
    return save_manager.current_save_info()


class SaveReq(BaseModel):
    name: str


@app.post("/save/create")
def save_create(req: SaveReq) -> dict:
    from server.systems import save_manager
    return save_manager.create_save(req.name)


@app.post("/save/load")
def save_load(req: SaveReq) -> dict:
    from server.systems import save_manager
    r = save_manager.load_save(req.name)
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "load failed"))
    return r


@app.post("/save/delete")
def save_delete(req: SaveReq) -> dict:
    from server.systems import save_manager
    return save_manager.delete_save(req.name)


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:
    with get_session() as s:
        npc_names = {n.id: n.name for n in load_npcs(s)}
        rows = s.exec(
            select(EventRow)
            .where(EventRow.state != "rejected")
            .order_by(EventRow.created_at.desc())
            .limit(limit)
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
    from server.core import event_flow as _ef

    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()

        # 预扫不可能满足的模板
        all_npcs = load_npcs(s)
        exclude = _ef.impossible_templates(templates, all_npcs)
        if exclude:
            print("[trigger] 预扫排除不可能模板：%s" % sorted(exclude))

        event = None
        tried = 0

        for attempt in range(3):
            remaining = [t for t in templates if t.id not in exclude]
            if not remaining:
                break

            seed_extra = random.randint(0, 10**9)
            tried += 1

            # 不再用外层 wait_for，让 LLM client 自己超时（30 秒）
            try:
                event = await run_event_cycle(
                    s, world, remaining,
                    force=True, attempt=seed_extra,
                )
            except Exception as e:
                print("[trigger] attempt %d 异常：%s" % (attempt, e))
                continue

            if event is not None:
                break

            rejected = _ef.get_last_rejected_template_id()
            if rejected:
                exclude.add(rejected)
                print("[trigger] attempt %d 被拒：%s" % (attempt, rejected))

        if event is None:
            raise HTTPException(
                400,
                "尝试 %d 次都没能生成合理事件，请换个时间或推进几回合" % tried,
            )

        npc_names = {n.id: n.name for n in load_npcs(s)}
        row = s.get(EventRow, event.id)
        if row is None:
            raise HTTPException(500, "event saved but not found")
        return _row_to_event(row, npc_names)
@app.post("/event/{event_id}/resolve")
async def resolve_event_endpoint(
    event_id: str,
    choice_id: str = Body(..., embed=True),
) -> dict:
    print("[resolve] event_id=[%s] choice_id=[%s]" % (event_id, choice_id))

    with get_session() as s:
        world = load_world(s)
        result = await resolve_event(s, world, event_id, choice_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "resolve failed"))

        # 记录"参与事件"目标
        try:
            from server.systems import goal as goal_sys
            import random as _r
            goal_sys.ensure_daily_goals(s, world, _r.Random(world.seed + world.day))
            goal_sys.ensure_milestones(s, world)
            player = player_sys.load_player(s)
            if player is not None:
                goal_sys.record_action(s, world, player, "event_resolved", 1)
        except Exception as e:
            import traceback
            print("[resolve] 目标记录失败：%s" % e)
            traceback.print_exc()

        return result
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
    target_type: str = "auto"


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
        "category": getattr(r, "category", "material") or "material",
        "slot": getattr(r, "slot", "") or "",
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
            user_id="player",
            target_npc_id=req.target_npc_id,
            target_type=req.target_type,
        )
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "use failed"))
        return result
