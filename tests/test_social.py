import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_npc, save_world
from server.models.schemas import NPC
from server.systems import social


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_social_respects_daily_cap(monkeypatch):
    from server.systems import social as sm

    class FakeLLM:
        async def text_json(self, prompt):
            return {"topic": "闲聊", "lines": [
                {"speaker": "A", "text": "你好"},
                {"speaker": "B", "text": "你也好"},
            ]}

    monkeypatch.setattr(sm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 100
        world.social_count_today = social.MAX_SOCIAL_PER_DAY
        save_world(s, world)
        npcs = [NPC(id="n%d" % i, name="N%d" % i, age=20, location_id="tavern") for i in range(3)]
        for n in npcs:
            save_npc(s, n)
        result = await social.maybe_social_dialogue(s, world, npcs, random.Random(1))
        assert result is None


@pytest.mark.asyncio
async def test_social_generates_dialogue(monkeypatch):
    from server.systems import social as sm

    class FakeLLM:
        async def text_json(self, prompt):
            return {"topic": "旧事", "lines": [
                {"speaker": "A", "text": "还记得那年么"},
                {"speaker": "B", "text": "当然记得"},
            ]}

    monkeypatch.setattr(sm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=7)
        world.tick = 100
        world.social_count_today = 0
        world.last_social_tick = -999
        save_world(s, world)
        npcs = [NPC(id="n1", name="A", age=20, location_id="tavern"),
                NPC(id="n2", name="B", age=20, location_id="tavern")]
        for n in npcs:
            save_npc(s, n)
        # 用固定 rng 触发：多次尝试直到成功
        for seed in range(50):
            world.social_count_today = 0
            world.last_social_tick = -999
            result = await social.maybe_social_dialogue(s, world, npcs, random.Random(seed))
            if result is not None:
                assert "lines" in result
                assert len(result["lines"]) == 2
                return
        pytest.fail("50 次尝试都没触发 social")
