import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.models.db import MemoryRow, dumps
from server.systems.embedding import cosine, deserialize, serialize
from server.systems.memory import retrieve_relevant


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_cosine_identical_vectors():
    v = [1.0, 2.0, 3.0]
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine(a, b)) < 1e-6


def test_serialize_roundtrip():
    v = [0.1, 0.2, 0.3]
    assert deserialize(serialize(v)) == v


@pytest.mark.asyncio
async def test_retrieve_falls_back_without_embedding(monkeypatch):
    """无 embedding 服务时，应按时间倒序返回最近记忆。"""
    from server.systems import memory as memory_mod

    class FakeEmb:
        enabled = False
        async def embed(self, text):
            return [1.0, 0.0, 0.0]

    monkeypatch.setattr(memory_mod, "get_embedding", lambda: FakeEmb())

    engine = _engine()
    with Session(engine) as s:
        for i in range(5):
            row = MemoryRow(
                id="mem_%d" % i,
                npc_id="npc_a",
                event_id="evt_%d" % i,
                summary="事件 %d" % i,
                emotion_json="{}",
                timestamp=100 - i,
                embedding_json="[]",
            )
            s.add(row)
        s.commit()
        result = await retrieve_relevant(s, "npc_a", "最近的", top_k=3)
        assert len(result) == 3
        # timestamp 越大越靠前
        assert result[0].timestamp == 100
