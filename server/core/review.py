"""LLM 抽样评审：对生成物打分 1-5，并记录到 evaluation 表。"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlmodel import Session

from server.generators.base import get_llm, load_prompt
from server.models.db import EvaluationRow, dumps
from server.models.schemas import Event, World

REVIEW_SCHEMA_HINT = '{"score": <1-5 float>, "errors": [<short tags>]}'


async def llm_review(payload: dict[str, Any], context: dict[str, Any]) -> dict:
    prompt = load_prompt("review.md").format(
        payload=json.dumps(payload, ensure_ascii=False, indent=2),
        context=json.dumps(context, ensure_ascii=False, indent=2),
    )
    try:
        raw = await get_llm().text_json(prompt)
        score = float(raw.get("score", 3.0))
        errors = list(raw.get("errors", []))
    except Exception:
        score = 3.0
        errors = ["review_failed"]
    score = max(1.0, min(5.0, score))
    return {"score": score, "errors": errors}


async def review_event(event: Event, world: World) -> dict:
    context = {
        "tick": world.tick,
        "tension": world.director.tension,
        "template_id": event.template_id,
    }
    result = await llm_review(event.payload, context)

    with Session(__import__("server.main", fromlist=["engine"]).engine) as s:
        row = EvaluationRow(
            id=str(uuid.uuid4()),
            target_type="event",
            target_id=event.id,
            passed=result["score"] >= 3.5,
            score=result["score"],
            errors_json=dumps(result["errors"]),
            raw_json=dumps({"source": "llm_review"}),
        )
        s.add(row)
        s.commit()

    return {
        "event_id": event.id,
        "template_id": event.template_id,
        "score": result["score"],
        "errors": result["errors"],
        "passed": result["score"] >= 3.5,
    }
