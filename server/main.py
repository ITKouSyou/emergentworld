"""FastAPI 入口。"""
from __future__ import annotations
import asyncio
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select
from pathlib import Path

from server.config import settings
from server.db.session import engine, ensure_schema
from server.models.db import NPCRow
from server.core.world import load_world
from server.api.utils import _generate_local_avatar

# 导入拆分后的路由和状态
from server.api.routes_system import router as system_router, INIT_STATE
from server.api.routes_player import router as player_router
from server.api.routes_world import router as world_router
from server.api.routes_npc import router as npc_router
from server.api.routes_market import router as market_router
from server.api import routes_dialogue, routes_review, routes_extra

async def _background_init():
    from server.generators.npc import generate_npc
    from server.core.world import save_npc
    from server.systems.family import build_families
    from server.systems.schedule import generate_schedule
    from server.systems.faction import assign_all_factions
    
    INIT_STATE["status"] = "generating"
    MALE_NAMES = ["张铁柱", "李大山", "王二狗", "赵石", "陈望", "刘长河", "孙远", "周慎"]
    FEMALE_NAMES = ["李秀兰", "王桂花", "赵小梅", "陈阿娇", "刘翠", "孙玉"]
    total = len(MALE_NAMES) + len(FEMALE_NAMES)
    INIT_STATE["total"] = total
    INIT_STATE["current"] = 0
    INIT_STATE["message"] = "正在唤醒沉睡的灵魂..."
    
    async def _gen_one(name: str, gender: str):
        npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
        INIT_STATE["current"] += 1
        INIT_STATE["message"] = "正在唤醒灵魂... (%d/%d)" % (INIT_STATE["current"], total)
        return npc

    tasks = [_gen_one(n, "male") for n in MALE_NAMES] + [_gen_one(n, "female") for n in FEMALE_NAMES]
    npcs = await asyncio.gather(*tasks)
    
    INIT_STATE["message"] = "正在雕刻岁月的痕迹..."
    with Session(engine) as session:
        for npc in npcs:
            save_npc(session, npc)
            _generate_local_avatar(npc.id, npc.name)
        
    INIT_STATE["message"] = "正在编织人际羁绊..."
    with Session(engine) as session:
        rng = random.Random(42)
        build_families(session, npcs, rng)
        for npc in npcs:
            npc.schedule = generate_schedule(npc, rng)
            save_npc(session, npc)
        assign_all_factions(session)
        
    INIT_STATE["status"] = "done"
    INIT_STATE["message"] = "世界生成完毕！"

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    ensure_schema()
    
    with Session(engine) as session:
        load_world(session)
        npc_count = len(session.exec(select(NPCRow)).all())
        
    if not settings.llm_api_key or settings.llm_api_key.strip() == "":
        INIT_STATE["status"] = "need_key"
        INIT_STATE["message"] = "请配置大模型 API Key"
        yield
        return
        
    if npc_count == 0:
        asyncio.create_task(_background_init())
    else:
        INIT_STATE["status"] = "done"
        INIT_STATE["current"] = INIT_STATE["total"]
        
    yield

app = FastAPI(title="EmergentWorld", lifespan=lifespan)

app.include_router(system_router)
app.include_router(player_router)
app.include_router(world_router)
app.include_router(npc_router)
app.include_router(market_router)
app.include_router(routes_extra.router)
app.include_router(routes_dialogue.router)
app.include_router(routes_review.router)

# 挂载静态资源目录
avatar_dir = Path("content/assets/avatars")
avatar_dir.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(avatar_dir)), name="avatars")
