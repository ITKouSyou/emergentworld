"""事件生成器：模板 + LLM 填充 + 规则兜底。"""

from __future__ import annotations

import random
import uuid

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label, template_label
from server.models.schemas import Event, EventTemplate, NPC, Player, World


def _pick_participants(tpl: EventTemplate, npcs: list[NPC], rng: random.Random) -> list[str]:
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _fallback_payload(tpl: EventTemplate, location: str, participants: list[NPC]) -> dict:
    names = "、".join(p.name for p in participants) or "无人"
    loc_zh = location_label(location)
    tpl_zh = template_label(tpl.id)
    return {
        "summary": "在%s发生了%s，涉及%s。" % (loc_zh, tpl_zh, names),
        "narrative": "（LLM 未返回，使用模板兜底。）",
    }


async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    player: Player | None = None,
) -> Event:
    participants_ids = _pick_participants(tpl, npcs, rng)
    participants = [n for n in npcs if n.id in participants_ids]
    location = tpl.params.get("location", "village_square")

    player_name = "（未创建）"
    player_loc = "（未知）"
    if player is not None and player.created:
        player_name = player.name
        player_loc = location_label(player.location_id)

    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        template_label=template_label(tpl.id),
        prompt=tpl.prompt,
        participants=", ".join("%s(%s)" % (p.name, p.id) for p in participants) or "无",
        location=location,
        location_label=location_label(location),
        player_name=player_name,
        player_location=player_loc,
        day=world.day,
    )
    fallback = _fallback_payload(tpl, location, participants)

    payload = fallback
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            candidate = raw.get("payload") if "payload" in raw else raw
            if isinstance(candidate, dict) and candidate.get("summary"):
                payload = {
                    "summary": str(candidate.get("summary", ""))[:300],
                    "narrative": str(candidate.get("narrative", ""))[:800],
                }
    except Exception:
        payload = fallback

    return Event(
        id="evt_%s" % uuid.uuid4().hex[:8],
        template_id=tpl.id,
        participants=participants_ids,
        location_id=location,
        state="pending",
        payload=payload,
        created_at=world.tick,
    )
