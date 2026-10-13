from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, load_world, save_world


def test_create_and_save_world():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        w = create_world("test", seed=1)
        save_world(s, w)
        loaded = load_world(s, "test")
        assert loaded.id == "test"
        assert loaded.seed == 1
