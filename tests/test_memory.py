from sqlmodel import Session, SQLModel, create_engine

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
