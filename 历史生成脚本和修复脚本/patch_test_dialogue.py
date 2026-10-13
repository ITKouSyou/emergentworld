"""更新 test_dialogue.py 以适配新的 npc_dialogue 签名。"""
from pathlib import Path

NEW_TEST = '''import pytest
from sqlmodel import Session, SQLModel, create_engine

from server.core.world import create_world, save_world
from server.models.schemas import NPC
from server.systems.memory import add_memory


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_memory_prompt_summary():
    engine = _engine()
    with Session(engine) as s:
        add_memory(s, "npc_1", "evt_1", "看见了火灾", {"fear": 0.8}, 10)
        add_memory(s, "npc_1", "evt_2", "和 Alden 吵架", {"anger": 0.5}, 20)
        from server.systems.memory import list_memories, summarize_for_prompt
        mems = list_memories(s, "npc_1")
        summaries = summarize_for_prompt(mems, limit=2)
        assert summaries[0] == "和 Alden 吵架"


@pytest.mark.asyncio
async def test_npc_dialogue_fallback(monkeypatch):
    from server.generators import dialogue

    class FakeLLM:
        async def text(self, prompt):
            raise RuntimeError("no llm")

    monkeypatch.setattr(dialogue, "get_llm", lambda: FakeLLM())

    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)

        npc = NPC(id="npc_1", name="Dain", age=30, goals=["survive"])

        # 新版签名：session, npc, player_input, world, memories=...
        result = await dialogue.npc_dialogue(
            session=s,
            npc=npc,
            player_input="你好",
            world=world,
            memories=[],  # 显式传空，跳过 embedding 检索
        )

        assert isinstance(result, dict)
        assert "reply" in result
        assert "Dain" in result["reply"]
        assert "memories_used" in result
        assert "relation_desc" in result
'''


p = Path("tests/test_dialogue.py")
p.write_text(NEW_TEST, encoding="utf-8", newline="\n")
print(f"[write] {p}")
print()
print("再跑：pytest -v")