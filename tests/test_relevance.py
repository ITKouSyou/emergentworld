from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_world
from server.models.schemas import Event, EventTemplate, Player
from server.systems import relationship
from server.systems.relevance import check_relevance


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_same_location_increases_relevance():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        player = Player(
            id="player", name="张", location_id="market",
            attributes={"luck": 5, "strength": 5, "agility": 5,
                        "intelligence": 5, "perception": 5, "charisma": 5},
            known_npcs=[],
        )
        evt = Event(
            id="e", template_id="market_dispute",
            participants=["npc_a"], location_id="market",
        )
        tpl = EventTemplate(id="market_dispute", tags=["daily"])
        ok, score, detail = check_relevance(s, evt, tpl, world, player, [])
        # 同地点 +0.25，加上 daily 不加 public 分
        assert "same_location" in detail
        assert score >= 0.25


def test_no_relevance_at_all():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        player = Player(
            id="player", name="张", location_id="home",
            attributes={"luck": 5, "strength": 5, "agility": 5,
                        "intelligence": 5, "perception": 5, "charisma": 5},
        )
        evt = Event(
            id="e", template_id="x",
            participants=["npc_a"], location_id="forest",
        )
        tpl = EventTemplate(id="x", tags=["daily"])
        ok, score, detail = check_relevance(s, evt, tpl, world, player, [])
        assert ok is False
        assert score < 0.35
