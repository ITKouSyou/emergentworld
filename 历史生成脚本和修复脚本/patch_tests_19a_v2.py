"""修 2 个残留失败的测试。

1. test_event_flow.py：整文件重写，包含：
   - 有玩家且相关性通过 → awaiting_player
   - 无玩家 → 自动 resolved（消息）
2. test_event_participation.py：在 resolve 测试里插入玩家创建
"""
from pathlib import Path

# ============================================================
# test_event_flow.py 整文件重写
# ============================================================
NEW_EVENT_FLOW = '''import random

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
    """玩家相关时，事件停在 awaiting_player。"""
    from server.core import event_flow
    from server.core.world import create_world, save_npc, save_world
    from server.models.schemas import NPC
    from server.systems import player as player_sys

    async def fake_fill_event(tpl, world, npcs, rng, player=None):
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

    def fake_check_relevance(session, event, tpl, world, player, npcs):
        return True, 0.9, {"forced": 0.9}

    monkeypatch.setattr(event_flow, "fill_event", fake_fill_event)
    monkeypatch.setattr(event_flow, "generate_reward", fake_generate_reward)
    monkeypatch.setattr(event_flow, "check_relevance", fake_check_relevance)

    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=7)
        world.tick = 10
        save_world(s, world)
        player_sys.create_player(s, "测试者", "male")
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="NPC%d" % i, age=20,
                            goals=["g"], behavior_profile={}, asset_params={}))

        tpl = EventTemplate(id="missing_person", tags=["conflict"],
                            cooldown=0, weight=1.0, params={"participant_count": 2})
        evt = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert evt is not None
        assert evt.state == "awaiting_player"
        assert "choices" in evt.payload
        assert len(evt.payload["choices"]) == 3
        choice_ids = [c["id"] for c in evt.payload["choices"]]
        assert choice_ids == ["help", "observe", "oppose"]


@pytest.mark.asyncio
async def test_run_event_cycle_no_player_auto_resolves(monkeypatch):
    """没有玩家时，事件自动结算为消息。"""
    from server.core import event_flow
    from server.core.world import create_world, save_npc, save_world
    from server.models.schemas import NPC

    async def fake_fill(tpl, world, npcs, rng, player=None):
        return Event(
            id="evt_auto", template_id=tpl.id,
            participants=[n.id for n in npcs[:2]],
            location_id="village_square",
            state="pending",
            payload={"summary": "x", "narrative": ""},
            created_at=world.tick,
        )

    async def fake_reward(event, world):
        from server.models.schemas import Reward
        return Reward(id="r", event_id=event.id, kind="item",
                      value=0.1, description="x", payload={})

    monkeypatch.setattr(event_flow, "fill_event", fake_fill)
    monkeypatch.setattr(event_flow, "generate_reward", fake_reward)

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 10
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20))

        tpl = EventTemplate(id="t", tags=["daily"], weight=1.0,
                            cooldown=0, params={"participant_count": 2})
        evt = await event_flow.run_event_cycle(s, world, [tpl], force=True)
        assert evt is not None
        assert evt.state == "resolved"
        assert evt.payload.get("as_message") is True
'''

p = Path("tests/test_event_flow.py")
p.write_text(NEW_EVENT_FLOW, encoding="utf-8", newline="\n")
print("[write] tests/test_event_flow.py")

# ============================================================
# test_event_participation.py 只插入 create_player
# ============================================================
p2 = Path("tests/test_event_participation.py")
t2 = p2.read_text(encoding="utf-8")

if "player_sys.create_player" in t2:
    print("[skip] test_event_participation.py 已有 create_player")
else:
    anchor = '            save_npc(s, NPC(id="npc_a", name="Alden", age=30))'
    if anchor in t2:
        insert = (
            '            from server.systems import player as player_sys\n'
            '            player_sys.create_player(s, "测试者", "male")\n'
            '\n'
            + anchor
        )
        t2 = t2.replace(anchor, insert, 1)
        p2.write_text(t2, encoding="utf-8", newline="\n")
        print("[fix] test_event_participation.py 插入 create_player")
    else:
        print("[fail] 未找到锚点，请手动在 resolve 测试的 save_npc 前插入：")
        print('    from server.systems import player as player_sys')
        print('    player_sys.create_player(s, "测试者", "male")')

print()
print("再跑：pytest -v")