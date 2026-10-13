r"""EmergentWorld scaffold - Part 5: 对话 + LLM 评审 + 离线演化。

运行：
    python scaffold_5_dialogue_review_evolve.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ api 包

FILES["server/api/__init__.py"] = '"""API routers."""\n'

# ================================================================ 对话路由

FILES["server/api/routes_dialogue.py"] = r'''"""NPC 对话端点：基于记忆生成回复。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from server.core.world import load_npcs, load_world
from server.db.session import get_session
from server.generators.dialogue import npc_dialogue
from server.systems.memory import list_memories, summarize_for_prompt

router = APIRouter(prefix="/npc", tags=["dialogue"])


class DialogueRequest(BaseModel):
    player_input: str


class DialogueResponse(BaseModel):
    npc_id: str
    npc_name: str
    reply: str
    memories_used: list[str]


@router.post("/{npc_id}/dialogue", response_model=DialogueResponse)
async def dialogue(npc_id: str, req: DialogueRequest) -> DialogueResponse:
    with get_session() as s:
        world = load_world(s)
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        npc = npcs[npc_id]

        mems = list_memories(s, npc_id, limit=10)
        mem_summaries = summarize_for_prompt(mems, limit=5)

    reply = await npc_dialogue(
        npc=npc,
        player_input=req.player_input,
        world=world,
        memories=mem_summaries,
    )

    return DialogueResponse(
        npc_id=npc.id,
        npc_name=npc.name,
        reply=reply,
        memories_used=mem_summaries,
    )
'''

# ================================================================ 评审路由

FILES["server/api/routes_review.py"] = r'''"""评审端点：对最近生成的事件 / 奖励做 LLM 抽样评审。"""

from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import select

from server.core.review import review_event
from server.core.world import load_world
from server.db.session import get_session
from server.models.db import EventRow, dumps, loads
from server.models.schemas import Event

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/latest")
async def review_latest(limit: int = 5) -> dict:
    """对最近 N 个事件做 LLM 评审。"""
    results: list[dict] = []
    with get_session() as s:
        world = load_world(s)
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()

        for r in rows:
            event = Event(
                id=r.id,
                template_id=r.template_id,
                participants=loads(r.participants_json) or [],
                location_id=r.location_id,
                state=r.state,  # type: ignore[arg-type]
                payload=loads(r.payload_json) or {},
                created_at=r.created_at,
                resolved_at=r.resolved_at,
            )
            result = await review_event(event, world)
            results.append(result)

    return {"count": len(results), "results": results}
'''

# ================================================================ 评审核心

FILES["server/core/review.py"] = r'''"""LLM 抽样评审：对生成物打分 1-5，并记录到 evaluation 表。"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlmodel import Session

from server.generators.base import get_llm, load_prompt
from server.models.db import EvaluationRow, dumps
from server.models.schemas import Event, World

REVIEW_SCHEMA_HINT = '{"score": <1-5 float>, "errors": [<short tags>]}'


async def llm_review(payload: dict[str, Any], context: dict[str, Any]) -> dict:
    prompt = load_prompt("review.md").format(
        payload=json.dumps(payload, ensure_ascii=False, indent=2),
        context=json.dumps(context, ensure_ascii=False, indent=2),
    )
    try:
        raw = await get_llm().text_json(prompt)
        score = float(raw.get("score", 3.0))
        errors = list(raw.get("errors", []))
    except Exception:
        score = 3.0
        errors = ["review_failed"]
    score = max(1.0, min(5.0, score))
    return {"score": score, "errors": errors}


async def review_event(event: Event, world: World) -> dict:
    context = {
        "tick": world.tick,
        "tension": world.director.tension,
        "template_id": event.template_id,
    }
    result = await llm_review(event.payload, context)

    with Session(__import__("server.main", fromlist=["engine"]).engine) as s:
        row = EvaluationRow(
            id=str(uuid.uuid4()),
            target_type="event",
            target_id=event.id,
            passed=result["score"] >= 3.5,
            score=result["score"],
            errors_json=dumps(result["errors"]),
            raw_json=dumps({"source": "llm_review"}),
        )
        s.add(row)
        s.commit()

    return {
        "event_id": event.id,
        "template_id": event.template_id,
        "score": result["score"],
        "errors": result["errors"],
        "passed": result["score"] >= 3.5,
    }
'''

# ================================================================ db.session

FILES["server/db/__init__.py"] = '"""DB helpers."""\n'

FILES["server/db/session.py"] = r'''"""数据库会话工厂。"""

from __future__ import annotations

from sqlmodel import Session, create_engine

from server.config import settings

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


def get_session() -> Session:
    return Session(engine)
'''

# ================================================================ prompts

FILES["server/prompts/dialogue.md"] = r'''你在扮演一个游戏 NPC。根据人设与记忆，对玩家的话做出回应。

规则：
- 保持角色口吻，符合其性格、目标、处境
- 不超过 3 句
- 如果有相关记忆，自然地带入
- 不要提及你是 AI
- 不要输出 markdown
- 只输出回复文本本身，不要加引号或前缀

名字：{name}
性格：{traits}
目标：{goals}
相关记忆：
{memories}

玩家说：{player_input}
'''

FILES["server/prompts/review.md"] = r'''你是游戏内容评审。对给定生成物打分 1-5，并指出问题。

评分标准：
- 5：有趣、连贯、符合世界、有惊喜
- 4：良好，略有平淡
- 3：合格，但缺乏特色
- 2：乏味、重复、不合理
- 1：无意义、矛盾、破坏沉浸

规则：
- 输出必须是合法 JSON，形如 {{"score": 3.5, "errors": []}}
- errors 使用简短英文标签，如 ["too_generic", "contradicts_world"]
- 不要输出 markdown，不要输出解释

生成物：
{payload}

世界上下文：
{context}
'''

FILES["server/prompts/chronicle.md"] = r'''你是世界编年史作者。根据事件日志，写一段简洁的编年史。

规则：
- 不超过 200 字
- 突出戏剧性的转折、关系变化、势力兴衰
- 不要逐条罗列，要讲故事
- 用第三人称
- 不要输出 markdown

事件日志：
{events}
'''

FILES["server/prompts/template_gen.md"] = r'''你是游戏事件模板设计师。根据编年史，设计 1 个新的可复用事件模板。

规则：
- 输出必须是合法 JSON
- 结构必须完全符合以下格式：
  {{"id": "snake_case_id", "tags": ["..."], "cooldown": <int>, "weight": <float 0-2>,
    "conditions": ["..."], "params": {{"participant_count": <int>, "location": "..."}},
    "prompt": "给 LLM 的事件生成提示，2-3 句",
    "evaluator": {{"require": ["..."], "max_reward": <float 0-1>}}}}
- id 必须唯一，不能与已有模板重复
- tags 从 [conflict, social, daily, mystery, trade, survival, plot, investigation, celebration, adventure] 中选
- 不要输出 markdown，不要输出解释

已有模板 ID：{existing_ids}

编年史：
{chronicle}
'''

# ================================================================ 覆盖 main

FILES["server/main.py"] = r'''"""FastAPI 入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, select

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
        "version": "0.2.0",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/world/state",
            "/world/tick",
            "/world/step",
            "/npc",
            "/npc/{npc_id}",
            "/npc/{npc_id}/dialogue",
            "/npc/{npc_id}/relationships",
            "/event",
            "/event/trigger",
            "/reward",
            "/review/latest",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


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
        }


@app.get("/npc", response_model=list[NPC])
def list_npcs() -> list[NPC]:
    with get_session() as s:
        return load_npcs(s)


@app.get("/npc/{npc_id}", response_model=NPC)
def get_npc(npc_id: str) -> NPC:
    with get_session() as s:
        npcs = {n.id: n for n in load_npcs(s)}
        if npc_id not in npcs:
            raise HTTPException(404, "npc not found")
        return npcs[npc_id]


@app.get("/npc/{npc_id}/relationships")
def npc_relationships(npc_id: str) -> list[dict]:
    with get_session() as s:
        return [r.model_dump() for r in relationship.list_relationships(s, npc_id)]


def _row_to_event(r: EventRow) -> Event:
    return Event(
        id=r.id,
        template_id=r.template_id,
        participants=loads(r.participants_json) or [],
        location_id=r.location_id,
        state=r.state,  # type: ignore[arg-type]
        payload=loads(r.payload_json) or {},
        created_at=r.created_at,
        resolved_at=r.resolved_at,
    )


@app.get("/event", response_model=list[Event])
def list_events(limit: int = 20) -> list[Event]:
    with get_session() as s:
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()
        return [_row_to_event(r) for r in rows]


@app.post("/event/trigger", response_model=Event)
async def trigger_event() -> Event:
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered (check templates / npcs)")
        return event


@app.get("/reward", response_model=list[Reward])
def list_rewards(limit: int = 20) -> list[Reward]:
    with get_session() as s:
        rows = s.exec(
            select(RewardRow).order_by(RewardRow.id.desc()).limit(limit)
        ).all()
        return [
            Reward(
                id=r.id,
                event_id=r.event_id,
                kind=r.kind,  # type: ignore[arg-type]
                value=r.value,
                description=r.description,
                payload=loads(r.payload_json) or {},
            )
            for r in rows
        ]
'''

# ================================================================ 覆盖 evolve

FILES["tools/evolve.py"] = r'''"""离线演化：跑事件、生成编年史、生成候选模板。"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

import yaml
from sqlmodel import Session, create_engine, select

from server.config import settings
from server.core import director
from server.core.event_flow import run_event_cycle
from server.core.tick import tick
from server.core.world import load_world, save_world
from server.generators.base import get_llm, load_prompt
from server.models.db import EventRow


def collect_events(session: Session, limit: int = 30) -> list[str]:
    rows = session.exec(
        select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
    ).all()
    lines = []
    for r in rows:
        summary = ""
        try:
            payload = json.loads(r.payload_json or "{}")
            summary = payload.get("summary", "")
        except Exception:
            pass
        lines.append(f"[{r.template_id}] {summary} ({r.state})")
    return lines


async def make_chronicle(events: list[str]) -> str:
    prompt = load_prompt("chronicle.md").format(events="\n".join(events) or "（无事件）")
    try:
        return await get_llm().text(prompt)
    except Exception:
        return "（LLM 不可用，跳过编年史）"


async def make_template(chronicle: str, existing_ids: list[str]) -> dict | None:
    prompt = load_prompt("template_gen.md").format(
        chronicle=chronicle,
        existing_ids=", ".join(existing_ids),
    )
    try:
        raw = await get_llm().text_json(prompt)
        if not isinstance(raw, dict):
            return None
        required = {"id", "tags", "cooldown", "weight", "params", "prompt", "evaluator"}
        if not required.issubset(raw.keys()):
            return None
        if raw["id"] in existing_ids:
            return None
        return raw
    except Exception:
        return None


def save_template(tpl: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{tpl['id']}.yaml"
    path.write_text(
        yaml.safe_dump(tpl, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


async def evolve(days: int, templates_dir: Path, auto_template: bool) -> None:
    engine = create_engine(f"sqlite:///{settings.db_path}")
    templates = director.load_templates(str(templates_dir))

    with Session(engine) as session:
        world = load_world(session)
        for _ in range(days * 24):
            tick(session, world)
            evt = await run_event_cycle(session, world, templates, force=False)
            if evt:
                print(f"[t{world.tick}] {evt.template_id}: "
                      f"{evt.payload.get('summary', '')[:60]}")
        save_world(session, world)

        events = collect_events(session, limit=40)
        chronicle = await make_chronicle(events)
        print("\n=== 编年史 ===")
        print(chronicle)

        if auto_template:
            existing_ids = [t.id for t in templates]
            new_tpl = await make_template(chronicle, existing_ids)
            if new_tpl:
                path = save_template(new_tpl, templates_dir)
                print(f"\n[新模板] {path}")
            else:
                print("\n[新模板] 生成失败或重复，跳过")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--templates-dir", default="content/templates/events")
    parser.add_argument("--no-template", action="store_true",
                        help="只生成编年史，不生成新模板")
    args = parser.parse_args()
    asyncio.run(evolve(
        days=args.days,
        templates_dir=Path(args.templates_dir),
        auto_template=not args.no_template,
    ))


if globals().get('__name__') == '__main__':
    main()
'''

# ================================================================ tests

FILES["tests/test_dialogue.py"] = r'''import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.models.schemas import NPC
from server.systems.memory import add_memory


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_memory_prompt_summary():
    engine = _engine()
    with Session(engine) as s:
        add_memory(s, "npc_1", "evt_1", "看见了火灾", {"fear": 0.8}, 10)
        add_memory(s, "npc_1", "evt_2", "和 Alden 吵架", {"anger": 0.5}, 20)
        from server.systems.memory import list_memories, summarize_for_prompt
        mems = list_memories(s, "npc_1")
        summaries = summarize_for_prompt(mems, limit=2)
        assert summaries[0] == "和 Alden 吵架"


@pytest.mark.asyncio
async def test_npc_dialogue_fallback(monkeypatch):
    from server.generators import dialogue
    from server.models.schemas import World

    async def fake_text(prompt):
        raise RuntimeError("no llm")

    class FakeLLM:
        async def text(self, prompt):
            return await fake_text(prompt)

    monkeypatch.setattr(dialogue, "get_llm", lambda: FakeLLM())
    npc = NPC(id="npc_1", name="Dain", age=30, goals=["survive"])
    reply = await dialogue.npc_dialogue(npc, "你好", World(id="w"), [])
    assert "Dain" in reply
'''

FILES["tests/test_review.py"] = r'''import pytest


@pytest.mark.asyncio
async def test_llm_review_parses_score(monkeypatch):
    from server.core import review

    async def fake_text_json(prompt):
        return {"score": 4.2, "errors": ["slightly_generic"]}

    class FakeLLM:
        async def text_json(self, prompt):
            return await fake_text_json(prompt)

    monkeypatch.setattr(review, "get_llm", lambda: FakeLLM())
    result = await review.llm_review({"summary": "测试事件"}, {"tick": 1})
    assert 4.0 <= result["score"] <= 4.5
    assert "slightly_generic" in result["errors"]


@pytest.mark.asyncio
async def test_llm_review_clamps_score(monkeypatch):
    from server.core import review

    class FakeLLM:
        async def text_json(self, prompt):
            return {"score": 99.0, "errors": []}

    monkeypatch.setattr(review, "get_llm", lambda: FakeLLM())
    result = await review.llm_review({"summary": "x"}, {"tick": 1})
    assert result["score"] == 5.0
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
            print(f"[skip]  {rel}")
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print(f"[write] {rel}")
        written += 1

    print(f"\nPart 5 done. written={written} skipped={skipped}")
    print("下一步：pytest -v")


if globals().get('__name__') == '__main__':
    main()