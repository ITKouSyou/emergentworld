import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_event, save_world
from server.models.schemas import Event
from server.systems import chronicle


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_chronicle_fallback_when_llm_fails(monkeypatch):
    from server.systems import chronicle as cm

    class FakeLLM:
        async def text(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(cm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 50
        save_world(s, world)
        for i in range(3):
            evt = Event(
                id="e%d" % i, template_id="market_dispute",
                participants=[], location_id="market",
                state="resolved", payload={"summary": "事%d" % i},
                created_at=i * 10, resolved_at=i * 10 + 1,
            )
            save_event(s, evt)

        result = await chronicle.generate_chronicle(s, from_tick=0, to_tick=50)
        assert result is not None
        assert result["body"] != ""


@pytest.mark.asyncio
async def test_chronicle_list(monkeypatch):
    from server.systems import chronicle as cm

    class FakeLLM:
        async def text(self, prompt):
            return "今日无大事。"

    monkeypatch.setattr(cm, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.tick = 50
        save_world(s, world)
        await chronicle.generate_chronicle(s, 0, 50)
        await chronicle.generate_chronicle(s, 50, 100)
        rows = chronicle.list_chronicles(s, limit=10)
        assert len(rows) == 2
