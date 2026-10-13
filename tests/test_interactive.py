"""事件模式与防重复测试。"""
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

    async def fake_fill(tpl, world, npcs, rng, player=None):
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
