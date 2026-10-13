import pytest


@pytest.mark.asyncio
async def test_llm_review_parses_score(monkeypatch):
    from server.core import review

    async def fake_text_json(prompt):
        return {"score": 4.2, "errors": ["slightly_generic"]}

    class FakeLLM:
        async def text_json(self, prompt):
            return await fake_text_json(prompt)

    monkeypatch.setattr(review, "get_llm", lambda: FakeLLM())
    result = await review.llm_review({"summary": "测试事件"}, {"tick": 1})
    assert 4.0 <= result["score"] <= 4.5
    assert "slightly_generic" in result["errors"]


@pytest.mark.asyncio
async def test_llm_review_clamps_score(monkeypatch):
    from server.core import review

    class FakeLLM:
        async def text_json(self, prompt):
            return {"score": 99.0, "errors": []}

    monkeypatch.setattr(review, "get_llm", lambda: FakeLLM())
    result = await review.llm_review({"summary": "x"}, {"tick": 1})
    assert result["score"] == 5.0
