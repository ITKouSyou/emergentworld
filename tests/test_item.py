import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.generators.item import generate_item
from server.models.db import ItemRow, dumps, loads
from server.models.schemas import Event, World


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_generate_item_fallback(monkeypatch):
    from server.generators import item as item_mod

    class FakeLLM:
        async def text_json(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(item_mod, "get_llm", lambda: FakeLLM())

    event = Event(
        id="evt_1",
        template_id="merchant_arrives",
        participants=[],
        location_id="market",
        payload={"summary": "行商到访"},
    )
    item = await generate_item(event, World(id="w"), 0.5)
    assert item["id"].startswith("itm_")
    assert item["name"]
    assert item["value"] == 0.5


def test_item_row_roundtrip():
    engine = _engine()
    with Session(engine) as s:
        row = ItemRow(
            id="itm_test",
            reward_id="rwd_test",
            event_id="evt_test",
            name="旧怀表",
            kind="饰物",
            affixes_json=dumps(["磨损的", "停在子夜的"]),
            story="某位行商遗落。",
            value=0.42,
        )
        s.add(row)
        s.commit()
        loaded = s.get(ItemRow, "itm_test")
        assert loaded is not None
        assert loaded.name == "旧怀表"
        assert "停在子夜的" in (loads(loaded.affixes_json) or [])
