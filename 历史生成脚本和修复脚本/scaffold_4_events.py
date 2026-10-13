r"""EmergentWorld scaffold - Part 4: 事件系统接入。

运行：
    python scaffold_4_events.py --force

新增：
    server/systems/memory.py
    server/systems/relationship.py
    server/core/event_flow.py
    tests/test_memory.py
    tests/test_relationship.py
    tests/test_event_flow.py

覆盖：
    server/core/director.py
    server/core/tick.py
    server/generators/event.py
    server/main.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

# ================================================================ memory

FILES["server/systems/memory.py"] = r'''"""记忆系统：NPC 记住发生的事件。"""

from __future__ import annotations

import uuid

from sqlmodel import Session, select

from server.models.db import MemoryRow, dumps, loads
from server.models.schemas import Memory


def add_memory(
    session: Session,
    npc_id: str,
    event_id: str,
    summary: str,
    emotion: dict[str, float] | None = None,
    timestamp: int = 0,
) -> Memory:
    mem = Memory(
        id=f"mem_{uuid.uuid4().hex[:8]}",
        npc_id=npc_id,
        event_id=event_id,
        summary=summary,
        emotion=emotion or {},
        timestamp=timestamp,
    )
    row = MemoryRow(
        id=mem.id,
        npc_id=mem.npc_id,
        event_id=mem.event_id,
        summary=mem.summary,
        emotion_json=dumps(mem.emotion),
        timestamp=mem.timestamp,
        embedding_id=None,
    )
    session.add(row)
    session.commit()
    return mem


def list_memories(session: Session, npc_id: str, limit: int = 20) -> list[Memory]:
    rows = session.exec(
        select(MemoryRow)
        .where(MemoryRow.npc_id == npc_id)
        .order_by(MemoryRow.timestamp.desc())
        .limit(limit)
    ).all()
    return [
        Memory(
            id=r.id,
            npc_id=r.npc_id,
            event_id=r.event_id,
            summary=r.summary,
            emotion=loads(r.emotion_json) or {},
            timestamp=r.timestamp,
            embedding_id=r.embedding_id,
        )
        for r in rows
    ]


def summarize_for_prompt(memories: list[Memory], limit: int = 5) -> list[str]:
    return [m.summary for m in memories[:limit] if m.summary]
'''

# ================================================================ relationship

FILES["server/systems/relationship.py"] = r'''"""关系系统：NPC 之间的信任、好感、恐惧、债务。"""

from __future__ import annotations

import random

from sqlmodel import Session, select

from server.models.db import RelationshipRow
from server.models.schemas import NPC, Relationship


def _rel_id(a: str, b: str) -> str:
    x, y = sorted([a, b])
    return f"rel_{x}_{y}"


def get_or_create(session: Session, from_npc: str, to_npc: str) -> Relationship:
    rid = _rel_id(from_npc, to_npc)
    row = session.get(RelationshipRow, rid)
    if row is None:
        row = RelationshipRow(id=rid, from_npc=from_npc, to_npc=to_npc)
        session.add(row)
        session.commit()
    return Relationship(
        id=row.id,
        from_npc=row.from_npc,
        to_npc=row.to_npc,
        trust=row.trust,
        affection=row.affection,
        fear=row.fear,
        debt=row.debt,
    )


def adjust(
    session: Session,
    from_npc: str,
    to_npc: str,
    trust: float = 0.0,
    affection: float = 0.0,
    fear: float = 0.0,
    debt: float = 0.0,
) -> Relationship:
    rid = _rel_id(from_npc, to_npc)
    row = session.get(RelationshipRow, rid)
    if row is None:
        row = RelationshipRow(id=rid, from_npc=from_npc, to_npc=to_npc)

    def clamp(v: float) -> float:
        return max(-1.0, min(1.0, v))

    row.trust = clamp(row.trust + trust)
    row.affection = clamp(row.affection + affection)
    row.fear = clamp(row.fear + fear)
    row.debt = clamp(row.debt + debt)
    session.add(row)
    session.commit()
    return Relationship(
        id=row.id,
        from_npc=row.from_npc,
        to_npc=row.to_npc,
        trust=row.trust,
        affection=row.affection,
        fear=row.fear,
        debt=row.debt,
    )


def apply_event_effects(
    session: Session,
    participants: list[str],
    tags: list[str],
    rng: random.Random,
) -> None:
    """根据事件类型调整参与者之间的关系。"""
    if len(participants) < 2:
        return

    conflict = "conflict" in tags
    social = "social" in tags or "daily" in tags or "celebration" in tags

    for i, a in enumerate(participants):
        for b in participants[i + 1:]:
            if conflict:
                adjust(session, a, b,
                       trust=-0.05 - rng.random() * 0.1,
                       affection=-0.05,
                       fear=0.05 + rng.random() * 0.1)
                adjust(session, b, a,
                       trust=-0.05 - rng.random() * 0.1,
                       affection=-0.05,
                       fear=0.05 + rng.random() * 0.1)
            elif social:
                adjust(session, a, b,
                       trust=0.03 + rng.random() * 0.05,
                       affection=0.03 + rng.random() * 0.05)
                adjust(session, b, a,
                       trust=0.03 + rng.random() * 0.05,
                       affection=0.03 + rng.random() * 0.05)
            else:
                adjust(session, a, b, trust=rng.uniform(-0.03, 0.03))
                adjust(session, b, a, trust=rng.uniform(-0.03, 0.03))


def list_relationships(session: Session, npc_id: str) -> list[Relationship]:
    rows = session.exec(
        select(RelationshipRow).where(
            (RelationshipRow.from_npc == npc_id) | (RelationshipRow.to_npc == npc_id)
        )
    ).all()
    return [
        Relationship(
            id=r.id,
            from_npc=r.from_npc,
            to_npc=r.to_npc,
            trust=r.trust,
            affection=r.affection,
            fear=r.fear,
            debt=r.debt,
        )
        for r in rows
    ]


def npc_effects_from_event(
    session: Session,
    participants: list[str],
    event_id: str,
    summary: str,
    timestamp: int,
    rng: random.Random,
) -> None:
    """占位：未来可扩展为更复杂的效果。"""
    from server.systems.memory import add_memory

    for npc_id in participants:
        emotion: dict[str, float] = {}
        if rng.random() < 0.3:
            emotion["fear"] = 0.3 + rng.random() * 0.4
        elif rng.random() < 0.3:
            emotion["joy"] = 0.3 + rng.random() * 0.4
        add_memory(
            session,
            npc_id=npc_id,
            event_id=event_id,
            summary=summary,
            emotion=emotion,
            timestamp=timestamp,
        )
'''

# ================================================================ director（覆盖）

FILES["server/core/director.py"] = r'''"""事件导演：决定何时触发何事件。不调用 LLM。"""

from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path

import yaml

from server.models.schemas import Event, EventTemplate, World


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


def fit_tension(tpl: EventTemplate, tension: float) -> float:
    conflict = "conflict" in tpl.tags
    if conflict:
        return 0.3 + tension
    return 1.2 - tension * 0.5


def cooldown_ok(tpl: EventTemplate, world: World) -> bool:
    last = world.director.last_event_tick
    return (world.tick - last) >= tpl.cooldown


def pick_template(
    templates: list[EventTemplate],
    world: World,
    rng: random.Random,
) -> EventTemplate | None:
    candidates: list[tuple[float, EventTemplate]] = []
    for tpl in templates:
        if not cooldown_ok(tpl, world):
            continue
        score = tpl.weight * fit_tension(tpl, world.director.tension)
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


def should_trigger(world: World, rng: random.Random) -> bool:
    """每 tick 判断是否触发事件。张力高时更容易触发。"""
    base = 0.015
    p = base + world.director.tension * 0.05
    gap = world.tick - world.director.last_event_tick
    if gap < 3:
        return False
    if gap < 8:
        p *= 0.5
    return rng.random() < p


def update_tension_after_event(world: World, event: Event, tpl: EventTemplate) -> None:
    if "conflict" in tpl.tags:
        world.director.tension = min(1.0, world.director.tension + 0.15)
    else:
        world.director.tension = max(0.0, world.director.tension - 0.1)
    world.director.last_event_tick = world.tick
    world.director.event_history.append(event.id)
    if len(world.director.event_history) > 200:
        world.director.event_history = world.director.event_history[-200:]


def decay_tension(world: World) -> None:
    world.director.tension = max(0.0, world.director.tension - 0.003)
'''

# ================================================================ event generator（覆盖）

FILES["server/generators/event.py"] = r'''"""事件生成器：模板 + LLM 填充 + 规则兜底。"""

from __future__ import annotations

import random
import uuid

from server.generators.base import get_llm, load_prompt
from server.models.schemas import Event, EventTemplate, NPC, World


def _pick_participants(tpl: EventTemplate, npcs: list[NPC], rng: random.Random) -> list[str]:
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _fallback_payload(tpl: EventTemplate, location: str, participants: list[NPC]) -> dict:
    names = "、".join(p.name for p in participants) or "无人"
    return {
        "summary": f"在{location}发生了{tpl.id}，涉及{names}。",
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
        prompt=tpl.prompt,
        participants=", ".join(f"{p.name}({p.id})" for p in participants) or "none",
        location=location,
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
        id=f"evt_{uuid.uuid4().hex[:8]}",
        template_id=tpl.id,
        participants=participants_ids,
        location_id=location,
        state="pending",
        payload=payload,
        created_at=world.tick,
    )
'''

# ================================================================ base 兼容：加 text_json

FILES["server/generators/base.py"] = r'''"""LLM 客户端封装。异步、可缓存、强制 JSON Schema。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from server.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = settings.llm_model
        self.cache_dir = settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 缓存 ----------

    def _cache_key(self, prompt: str, schema_name: str) -> str:
        h = hashlib.sha256(f"{self.model}|{schema_name}|{prompt}".encode())
        return h.hexdigest()

    def _cache_get(self, key: str) -> Any | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _cache_set(self, key: str, data: Any) -> None:
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 调用 ----------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _call_raw(self, prompt: str) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a game content generator. "
                        "Always answer with valid JSON. "
                        "No prose, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.9,
        )
        return resp.choices[0].message.content or "{}"

    async def json(
        self,
        prompt: str,
        schema: type[T],
        *,
        fallback: T | None = None,
    ) -> T:
        key = self._cache_key(prompt, schema.__name__)
        cached = self._cache_get(key)
        if cached is not None:
            try:
                return schema.model_validate(cached)
            except Exception:
                pass
        try:
            raw = await self._call_raw(prompt)
            data = json.loads(raw)
            obj = schema.model_validate(data)
            self._cache_set(key, obj.model_dump())
            return obj
        except Exception:
            if fallback is not None:
                return fallback
            raise

    async def text_json(self, prompt: str) -> Any:
        key = self._cache_key(prompt, "text_json")
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        raw = await self._call_raw(prompt)
        data = json.loads(raw)
        self._cache_set(key, data)
        return data

    async def text(self, prompt: str) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        return resp.choices[0].message.content or ""


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


def load_prompt(name: str) -> str:
    path = Path("server/prompts") / name
    return path.read_text(encoding="utf-8")
'''

# ================================================================ event_flow

FILES["server/core/event_flow.py"] = r'''"""事件流程：串起 Director + Generator + Evaluator + 记忆 + 关系。"""

from __future__ import annotations

import random
from typing import Optional

from sqlmodel import Session

from server.core import director
from server.core.evaluator import evaluate_event, evaluate_reward, log_evaluation
from server.core.world import load_npcs, save_event, save_world
from server.generators.event import fill_event
from server.generators.reward import compute_budget, generate_reward
from server.models.db import RewardRow, dumps
from server.models.schemas import Event, EventTemplate, Reward, World
from server.systems import relationship


def _save_reward(session: Session, reward: Reward) -> None:
    row = RewardRow(
        id=reward.id,
        event_id=reward.event_id,
        kind=reward.kind,
        value=reward.value,
        description=reward.description,
        payload_json=dumps(reward.payload),
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
    summary = event.payload.get("summary", "") or f"发生了 {tpl.id}"
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
    """执行一次事件循环。返回触发的事件，或 None。"""
    rng = random.Random(world.seed * 1000003 + world.tick)

    if not force and not director.should_trigger(world, rng):
        return None

    tpl = director.pick_template(templates, world, rng)
    if tpl is None:
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    # 生成
    event = await fill_event(tpl, world, npcs, rng)

    # 评估
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

    # 应用效果：记忆 + 关系
    _apply_effects(session, world, event, tpl, rng)

    # 奖励
    budget = compute_budget(event, world)
    reward = await generate_reward(event, world)
    reward_ok, reward_errors = evaluate_reward(reward, budget)
    log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)
    if reward_ok:
        _save_reward(session, reward)
        event.payload["reward_id"] = reward.id

    # 结算
    event.state = "resolved"
    event.resolved_at = world.tick
    save_event(session, event)

    director.update_tension_after_event(world, event, tpl)
    save_world(session, world)

    return event
'''

# ================================================================ tick（覆盖）

FILES["server/core/tick.py"] = r'''"""时间推进。所有实时逻辑必须同步、无 LLM 调用。

事件触发由 event_flow.run_event_cycle() 异步处理，
调用方需要在 tick 之后单独 await 一次事件循环。
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

# ================================================================ main（覆盖）

FILES["server/main.py"] = r'''"""FastAPI 入口。MVP 阶段所有路由集中在此。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from server.config import settings
from server.core import director
from server.core.event_flow import run_event_cycle
from server.core.tick import tick
from server.core.world import load_npcs, load_world, save_world
from server.models.db import EventRow, RewardRow, dumps, loads
from server.models.schemas import Event, NPC, Reward, World
from server.systems import relationship

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_world(session)
    yield


app = FastAPI(title="EmergentWorld", lifespan=lifespan)


def get_session() -> Session:
    return Session(engine)


# ---------- 根 ----------

@app.get("/")
def root() -> dict:
    return {
        "name": "EmergentWorld",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/world/state",
            "/world/tick",
            "/world/step",
            "/npc",
            "/npc/{npc_id}",
            "/event",
            "/event/trigger",
            "/reward",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# ---------- 世界 ----------

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
    """推进一个 tick，并尝试触发一次事件。"""
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


# ---------- NPC ----------

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
        rels = relationship.list_relationships(s, npc_id)
        return [r.model_dump() for r in rels]


# ---------- 事件 ----------

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
    """手动触发一次事件（调试用）。"""
    with get_session() as s:
        world = load_world(s)
        templates = director.load_templates()
        event = await run_event_cycle(s, world, templates, force=True)
        if event is None:
            raise HTTPException(400, "no event triggered (check templates / npcs)")
        return event


# ---------- 奖励 ----------

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

# ================================================================ tests

FILES["tests/test_memory.py"] = r'''from sqlmodel import Session, SQLModel, create_engine

from server.systems.memory import add_memory, list_memories


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_add_and_list_memory():
    engine = _engine()
    with Session(engine) as s:
        add_memory(s, "npc_1", "evt_1", "看见了火灾", {"fear": 0.8}, 10)
        add_memory(s, "npc_1", "evt_2", "和 Alden 吵架", {"anger": 0.5}, 20)
        mems = list_memories(s, "npc_1")
        assert len(mems) == 2
        assert mems[0].summary == "和 Alden 吵架"  # 新的在前
'''

FILES["tests/test_relationship.py"] = r'''import random

from sqlmodel import Session, SQLModel, create_engine

from server.systems.relationship import adjust, apply_event_effects, get_or_create


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_get_or_create_and_adjust():
    engine = _engine()
    with Session(engine) as s:
        r = get_or_create(s, "npc_a", "npc_b")
        assert r.trust == 0.0
        r2 = adjust(s, "npc_a", "npc_b", trust=0.3, affection=0.2)
        assert abs(r2.trust - 0.3) < 1e-6
        assert abs(r2.affection - 0.2) < 1e-6


def test_apply_event_effects_conflict_lowers_trust():
    engine = _engine()
    with Session(engine) as s:
        rng = random.Random(42)
        apply_event_effects(s, ["a", "b", "c"], ["conflict"], rng)
        r = get_or_create(s, "a", "b")
        assert r.trust < 0
'''

FILES["tests/test_event_flow.py"] = r'''import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.director import should_trigger, update_tension_after_event
from server.models.schemas import Event, EventTemplate, World


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_should_trigger_respects_min_gap():
    world = World(id="w", seed=1)
    world.tick = 5
    world.director.last_event_tick = 4
    rng = random.Random(1)
    # 最小间隔 3 tick，这里只隔了 1，一定不触发
    assert not should_trigger(world, rng)


def test_update_tension_conflict_raises():
    world = World(id="w")
    tpl = EventTemplate(id="t", tags=["conflict"])
    evt = Event(id="e", template_id="t", participants=[], location_id="loc")
    before = world.director.tension
    update_tension_after_event(world, evt, tpl)
    assert world.director.tension > before
    assert evt.id in world.director.event_history


@pytest.mark.asyncio
async def test_run_event_cycle_force_with_mock_llm(monkeypatch):
    """强制触发一次事件流程，不调用真实 LLM。"""
    from server.core import event_flow
    from server.core.world import create_world, save_npc, save_world
    from server.models.schemas import NPC

    async def fake_fill_event(tpl, world, npcs, rng):
        return Event(
            id="evt_test",
            template_id=tpl.id,
            participants=[n.id for n in npcs[:2]],
            location_id="village_square",
            state="pending",
            payload={"summary": "测试事件", "narrative": ""},
            created_at=world.tick,
        )

    async def fake_generate_reward(event, world):
        from server.models.schemas import Reward
        return Reward(
            id="rwd_test",
            event_id=event.id,
            kind="item",
            value=0.1,
            description="test reward",
        )

    monkeypatch.setattr(event_flow, "fill_event", fake_fill_event)
    monkeypatch.setattr(event_flow, "generate_reward", fake_generate_reward)

    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=7)
        world.tick = 10
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id=f"npc_{i}", name=f"NPC{i}", age=20,
                            goals=["g"], behavior_profile={}, asset_params={}))

        tpl = EventTemplate(id="missing_person", tags=["conflict"],
                            cooldown=0, weight=1.0, params={"participant_count": 2})
        evt = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert evt is not None
        assert evt.state == "resolved"
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

    print(f"\nPart 4 done. written={written} skipped={skipped}")
    print("下一步：pytest -v")


if globals().get('__name__') == '__main__':
    main()