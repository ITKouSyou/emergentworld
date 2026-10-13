import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_npc, save_world
from server.models.db import ItemRow, dumps
from server.models.schemas import NPC
from server.systems import item_use


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def _setup(s):
    world = create_world("test", seed=1)
    world.tick = 10
    save_world(s, world)
    save_npc(s, NPC(id="npc_a", name="Alden", age=30, goals=["g"]))
    row = ItemRow(
        id="itm_1",
        reward_id="rwd_1",
        event_id="evt_1",
        name="护身符",
        kind="信物",
        affixes_json=dumps(["粗糙的"]),
        story="护身",
        value=0.4,
        owner_id="player",
    )
    s.add(row)
    s.commit()
    return world


@pytest.mark.asyncio
async def test_use_item_fallback(monkeypatch):
    from server.systems import item_use as mod

    class FakeLLM:
        async def text_json(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(mod, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = _setup(s)
        result = await item_use.use_item(s, world, "itm_1", "player", "npc_a")
        assert result["ok"] is True
        assert "Alden" in result["effect"]


@pytest.mark.asyncio
async def test_use_consumes_when_llm_says(monkeypatch):
    from server.systems import item_use as mod

    class FakeLLM:
        async def text_json(self, prompt):
            return {
                "effect": "Alden 收下了护身符。",
                "relationship_change": {"trust": 0.2},
                "consume": True,
            }

    monkeypatch.setattr(mod, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = _setup(s)
        result = await item_use.use_item(s, world, "itm_1", "player", "npc_a")
        assert result["ok"] is True
        assert result["consumed"] is True

        from server.systems import inventory
        rows = inventory.list_items_by_owner(s, "player")
        assert len(rows) == 0
