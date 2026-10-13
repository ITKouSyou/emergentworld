"""物品使用：LLM 生成效果 + 关系/需求调整 + 可消耗。"""

from __future__ import annotations

import json
import random
import uuid

from sqlmodel import Session

from server.core.world import load_npcs
from server.generators.base import get_llm, load_prompt
from server.models.db import ItemUseRow, dumps
from server.models.schemas import World
from server.systems import inventory, relationship


def _fallback_effect(item_name: str, target_name: str) -> dict:
    if target_name:
        text = "%s收下了%s，神色略显动容。" % (target_name, item_name)
    else:
        text = "你把玩着%s，心绪稍定。" % item_name
    return {
        "effect": text,
        "relationship_change": {},
        "consume": False,
    }


async def use_item(
    session: Session,
    world: World,
    item_id: str,
    user_id: str = "player",
    target_npc_id: str = "",
) -> dict:
    row = inventory.get_item_row(session, item_id)
    if row is None:
        return {"ok": False, "error": "item not found"}
    if row.consumed:
        return {"ok": False, "error": "item already consumed"}

    npcs = load_npcs(session)
    npc_names = {n.id: n.name for n in npcs}
    target_name = npc_names.get(target_npc_id, "")

    prompt = load_prompt("item_use.md").format(
        item_name=row.name,
        item_kind=row.kind,
        item_affixes=", ".join(inventory.loads(row.affixes_json) or []),
        item_story=row.story,
        target_name=target_name or "（无）",
        world_tick=world.tick,
    )
    fallback = _fallback_effect(row.name, target_name)

    effect_data = fallback
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            effect = str(raw.get("effect", "")).strip()[:200]
            rel_change = raw.get("relationship_change", {})
            if not isinstance(rel_change, dict):
                rel_change = {}
            consume = bool(raw.get("consume", False))
            if effect:
                effect_data = {
                    "effect": effect,
                    "relationship_change": rel_change,
                    "consume": consume,
                }
    except Exception:
        pass

    # 应用效果
    if target_npc_id and effect_data.get("relationship_change"):
        rc = effect_data["relationship_change"]
        relationship.adjust(
            session,
            from_npc=target_npc_id,
            to_npc=user_id if user_id != "player" else target_npc_id,
            trust=float(rc.get("trust", 0.0)),
            affection=float(rc.get("affection", 0.0)),
            fear=float(rc.get("fear", 0.0)),
            debt=float(rc.get("debt", 0.0)),
        )

    consumed = bool(effect_data.get("consume", False))
    if consumed:
        inventory.consume_item(session, item_id)

    use_row = ItemUseRow(
        id="use_%s" % uuid.uuid4().hex[:8],
        item_id=item_id,
        user_id=user_id,
        target_npc_id=target_npc_id,
        effect=effect_data["effect"],
        consumed=consumed,
        timestamp=world.tick,
    )
    session.add(use_row)
    session.commit()

    return {
        "ok": True,
        "item_id": item_id,
        "item_name": row.name,
        "target_npc_id": target_npc_id,
        "target_name": target_name,
        "effect": effect_data["effect"],
        "consumed": consumed,
    }
