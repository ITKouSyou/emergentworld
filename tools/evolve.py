"""离线演化：跑事件、生成编年史、生成候选模板。"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

import yaml
from sqlmodel import Session, create_engine, select

from server.config import settings
from server.core import director
from server.core.event_flow import run_event_cycle
from server.core.tick import tick
from server.core.world import load_world, save_world
from server.generators.base import get_llm, load_prompt
from server.models.db import EventRow


def collect_events(session: Session, limit: int = 30) -> list[str]:
    rows = session.exec(
        select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)
    ).all()
    lines = []
    for r in rows:
        summary = ""
        try:
            payload = json.loads(r.payload_json or "{}")
            summary = payload.get("summary", "")
        except Exception:
            pass
        lines.append(f"[{r.template_id}] {summary} ({r.state})")
    return lines


async def make_chronicle(events: list[str]) -> str:
    prompt = load_prompt("chronicle.md").format(events="\n".join(events) or "（无事件）")
    try:
        return await get_llm().text(prompt)
    except Exception:
        return "（LLM 不可用，跳过编年史）"


async def make_template(chronicle: str, existing_ids: list[str]) -> dict | None:
    prompt = load_prompt("template_gen.md").format(
        chronicle=chronicle,
        existing_ids=", ".join(existing_ids),
    )
    try:
        raw = await get_llm().text_json(prompt)
        if not isinstance(raw, dict):
            return None
        required = {"id", "tags", "cooldown", "weight", "params", "prompt", "evaluator"}
        if not required.issubset(raw.keys()):
            return None
        if raw["id"] in existing_ids:
            return None
        return raw
    except Exception:
        return None


def save_template(tpl: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{tpl['id']}.yaml"
    path.write_text(
        yaml.safe_dump(tpl, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


async def evolve(days: int, templates_dir: Path, auto_template: bool) -> None:
    engine = create_engine(f"sqlite:///{settings.db_path}")
    templates = director.load_templates(str(templates_dir))

    with Session(engine) as session:
        world = load_world(session)
        for _ in range(days * 24):
            tick(session, world)
            evt = await run_event_cycle(session, world, templates, force=False)
            if evt:
                print(f"[t{world.tick}] {evt.template_id}: "
                      f"{evt.payload.get('summary', '')[:60]}")
        save_world(session, world)

        events = collect_events(session, limit=40)
        chronicle = await make_chronicle(events)
        print("\n=== 编年史 ===")
        print(chronicle)

        if auto_template:
            existing_ids = [t.id for t in templates]
            new_tpl = await make_template(chronicle, existing_ids)
            if new_tpl:
                path = save_template(new_tpl, templates_dir)
                print(f"\n[新模板] {path}")
            else:
                print("\n[新模板] 生成失败或重复，跳过")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--templates-dir", default="content/templates/events")
    parser.add_argument("--no-template", action="store_true",
                        help="只生成编年史，不生成新模板")
    args = parser.parse_args()
    asyncio.run(evolve(
        days=args.days,
        templates_dir=Path(args.templates_dir),
        auto_template=not args.no_template,
    ))


if globals().get('__name__') == '__main__':
    main()
