# 编年史：增量生成
from __future__ import annotations

import uuid
from typing import Optional

from sqlmodel import Session, select

from server.generators.base import get_llm, load_prompt
from server.models.db import ChronicleRow, EventRow, loads


def _collect_since(session: Session, since_tick: int, limit: int = 60) -> list[str]:
    rows = session.exec(
        select(EventRow)
        .where(EventRow.created_at > since_tick)
        .order_by(EventRow.created_at.asc())
        .limit(limit)
    ).all()
    lines: list[str] = []
    for r in rows:
        payload = loads(r.payload_json) or {}
        summary = payload.get("summary") or ""
        outcome = payload.get("outcome") or ""
        line = "- [%s] %s" % (r.template_id, summary)
        if outcome:
            line += "  →  %s" % outcome
        lines.append(line)
    return lines


def _fallback_body(events: list[str]) -> str:
    if not events:
        return "（这段时间村里风平浪静。）"
    return "近日要闻：\n" + "\n".join(events[-10:])


async def generate_chronicle(
    session: Session,
    from_tick: int = 0,
    to_tick: int = 0,
    title_hint: str = "",
) -> Optional[dict]:
    # 找上一次史册的 to_tick
    last = session.exec(
        select(ChronicleRow).order_by(ChronicleRow.created_at.desc()).limit(1)
    ).first()
    since = last.to_tick if last else from_tick

    events = _collect_since(session, since, limit=60)

    if not events:
        body = "（上次史册之后，村里暂无新的记载。）"
        title = title_hint or "第 %d tick 记" % to_tick
        row = ChronicleRow(
            id="chr_%s" % uuid.uuid4().hex[:8],
            title=title,
            body=body,
            from_tick=since,
            to_tick=to_tick,
            created_at=to_tick,
        )
        session.add(row)
        session.commit()
        return {
            "id": row.id, "title": row.title, "body": row.body,
            "from_tick": row.from_tick, "to_tick": row.to_tick,
            "created_at": row.created_at,
        }

    prompt = load_prompt("chronicle.md").format(events="\n".join(events))
    body = ""
    try:
        body = await get_llm().text(prompt)
    except Exception:
        body = _fallback_body(events)

    if not body.strip():
        body = _fallback_body(events)

    title = title_hint or "第 %d tick 记" % to_tick

    row = ChronicleRow(
        id="chr_%s" % uuid.uuid4().hex[:8],
        title=title,
        body=body.strip(),
        from_tick=since,
        to_tick=to_tick,
        created_at=to_tick,
    )
    session.add(row)
    session.commit()

    return {
        "id": row.id, "title": row.title, "body": row.body,
        "from_tick": row.from_tick, "to_tick": row.to_tick,
        "created_at": row.created_at,
    }


def list_chronicles(session: Session, limit: int = 20) -> list[dict]:
    rows = session.exec(
        select(ChronicleRow).order_by(ChronicleRow.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id, "title": r.title, "body": r.body,
            "from_tick": r.from_tick, "to_tick": r.to_tick,
            "created_at": r.created_at,
        }
        for r in rows
    ]
