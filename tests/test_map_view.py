from sqlmodel import Session, SQLModel, create_engine

from server.core.map_view import build_map_data
from server.core.world import create_world, save_event, save_npc, save_world
from server.models.schemas import Event, NPC


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_map_data_structure():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=1)
        save_world(s, world)
        for i in range(3):
            save_npc(s, NPC(id="npc_%d" % i, name="N%d" % i, age=20,
                            goals=["g"], location_id="village_square"))
        data = build_map_data(s, world)
        assert "locations" in data
        assert "paths" in data
        assert "npcs" in data
        assert "hour" in data
        assert len(data["npcs"]) == 3
        coords = {(n["x"], n["y"]) for n in data["npcs"]}
        assert len(coords) == 3


def test_map_data_includes_active_events():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=1)
        save_world(s, world)
        evt = Event(
            id="evt_x",
            template_id="bandit_raid",
            participants=[],
            location_id="village_edge",
            state="active",
            payload={"summary": "test"},
        )
        save_event(s, evt)
        data = build_map_data(s, world)
        assert len(data["active_events"]) == 1
        assert data["active_events"][0]["location_id"] == "village_edge"


def test_map_paths_are_valid():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("test", seed=1)
        save_world(s, world)
        data = build_map_data(s, world)
        loc_ids = {loc["id"] for loc in data["locations"]}
        for p in data["paths"]:
            assert p["from"] in loc_ids
            assert p["to"] in loc_ids
