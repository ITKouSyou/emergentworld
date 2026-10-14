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
    target_type: str = "auto",
) -> dict:
    """按物品 category 分支处理使用。

    target_type: "self" / "npc" / "scene" / "none" / "auto"
    """
    import random
    rng = random.Random(world.seed * 100003 + world.tick)

    from server.systems import item_meta

    row = inventory.get_item_row(session, item_id)
    if row is None:
        return {"ok": False, "error": "item not found"}
    if row.consumed:
        return {"ok": False, "error": "item already consumed"}

    cat = getattr(row, "category", "") or item_meta.infer_category(row.kind)
    row.category = cat

    # ---------- consumable ----------
    if cat == "consumable":
        effect = getattr(row, "use_effect_json", "")
        import json
        try:
            eff = json.loads(effect) if effect else {}
        except Exception:
            eff = {}
        if not eff:
            eff = item_meta.infer_effect(row.kind)

        return _apply_consume(session, world, row, eff, target_npc_id, rng)

    # ---------- equipment ----------
    if cat == "equipment":
        # 不消耗，只是切换到"已装备"逻辑（下一轮完整实现）
        # 暂时：返回一条描述
        return {
            "ok": True,
            "kind": "equipment",
            "item_id": item_id,
            "item_name": row.name,
            "effect": "你把%s拿在手里试了试。" % row.name,
            "consumed": False,
        }

    # ---------- key ----------
    if cat == "key":
        return {
            "ok": True,
            "kind": "key",
            "item_id": item_id,
            "item_name": row.name,
            "effect": "你拿着%s四处查看，但眼下没有能用它的地方。" % row.name,
            "consumed": False,
        }

    # ---------- material / quest ----------
    return {
        "ok": False,
        "error": "%s 是%s，不能直接使用。" % (
            row.name,
            "材料" if cat == "material" else "剧情物品"
        ),
    }


def _apply_consume(session, world, row, eff: dict, target_npc_id: str, rng) -> dict:
    """处理消耗品。"""
    from server.systems import player as player_sys

    effects_text = []
    pr = session.get(__import__("server.models.db", fromlist=["PlayerRow"]).PlayerRow, "player")

    # 效果应用
    if target_npc_id:
        # 对 NPC 用（送礼、治疗），不消耗玩家 HP
        if "hp" in eff:
            effects_text.append("对方恢复了 %d 点生命" % int(eff["hp"]))
        # 关系加成
        from server.systems import relationship
        relationship.adjust(session, target_npc_id, "player",
                            affection=0.05, trust=0.03)
        effects_text.append("对方对你的好感略有提升")
    else:
        # 对自己用
        if pr is not None:
            if "hp" in eff:
                old_hp = pr.hp or 0
                pr.hp = min(pr.max_hp or 100, old_hp + int(eff["hp"]))
                effects_text.append("生命 %d → %d" % (old_hp, pr.hp))
            if "hunger" in eff:
                # hunger 是 NPC 需求，玩家没这字段；忽略或映射
                effects_text.append("你感觉不那么饿了")
            if "social" in eff:
                effects_text.append("你感觉精神一振")
            session.add(pr)
            session.commit()

    # 消耗
    row.consumed = True
    session.add(row)
    session.commit()

    return {
        "ok": True,
        "kind": "consumable",
        "item_id": row.id,
        "item_name": row.name,
        "effect": "、".join(effects_text) or "你使用了%s。" % row.name,
        "consumed": True,
        "effects": eff,
    }
