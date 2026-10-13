"""物品生成器：根据事件上下文生成实物。"""

from __future__ import annotations

import uuid

from server.generators.base import get_llm, load_prompt
from server.i18n import location_label, template_label
from server.models.schemas import Event, World


def _fallback_item(event: Event, value: float) -> dict:
    tpl_zh = template_label(event.template_id)
    return {
        "id": "itm_%s" % uuid.uuid4().hex[:8],
        "name": "%s纪念品" % tpl_zh,
        "kind": "纪念品",
        "affixes": ["朴素的"],
        "story": "来自%s的纪念物。" % tpl_zh,
        "value": value,
    }


async def generate_item(
    event: Event,
    world: World,
    value: float,
) -> dict:
    """生成一件物品。返回 dict，字段与 Item schema 一致。"""
    summary = str(event.payload.get("summary", "")).strip()
    tpl_zh = template_label(event.template_id)
    loc_zh = location_label(event.location_id)

    prompt = load_prompt("item_gen.md").format(
        template_label=tpl_zh,
        summary=summary or "（无）",
        value=value,
        location_label=loc_zh,
    )

    item_id = "itm_%s" % uuid.uuid4().hex[:8]
    fallback = _fallback_item(event, value)

    try:
        raw = await get_llm().text_json(prompt)
        if not isinstance(raw, dict):
            return fallback

        name = str(raw.get("name", "")).strip()[:16]
        kind = str(raw.get("kind", "")).strip()[:16]
        affixes = raw.get("affixes", [])
        if not isinstance(affixes, list):
            affixes = []
        affixes = [str(a).strip()[:8] for a in affixes][:3]
        story = str(raw.get("story", "")).strip()[:120]

        if not name or not kind:
            return fallback

        return {
            "id": item_id,
            "name": name,
            "kind": kind,
            "affixes": affixes,
            "story": story,
            "value": float(value),
        }
    except Exception:
        return fallback
