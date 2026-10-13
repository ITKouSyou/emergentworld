"""评审端点：对最近生成的事件 / 奖励做 LLM 抽样评审。"""

from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import select

from server.core.review import review_event
from server.core.world import load_world
from server.db.session import get_session
from server.models.db import EventRow, dumps, loads
from server.models.schemas import Event

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/latest")
async def review_latest(limit: int = 5) -> dict:
    """对最近 N 个事件做 LLM 评审。"""
    results: list[dict] = []
    with get_session() as s:
        world = load_world(s)
        rows = s.exec(
            select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
        ).all()

        for r in rows:
            event = Event(
                id=r.id,
                template_id=r.template_id,
                participants=loads(r.participants_json) or [],
                location_id=r.location_id,
                state=r.state,  # type: ignore[arg-type]
                payload=loads(r.payload_json) or {},
                created_at=r.created_at,
                resolved_at=r.resolved_at,
            )
            result = await review_event(event, world)
            results.append(result)

    return {"count": len(results), "results": results}
