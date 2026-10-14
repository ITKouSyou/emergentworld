# 装备系统
from __future__ import annotations

import json

from sqlmodel import Session

from server.models.db import ItemRow, PlayerRow, dumps, loads
from server.models.schemas import Player
from server.systems import inventory, item_meta


SLOTS = ["weapon", "armor", "accessory", "tool"]
SLOT_LABELS = {
    "weapon": "武器",
    "armor": "护甲",
    "accessory": "饰物",
    "tool": "工具",
}


def get_equipped(session: Session) -> dict[str, str]:
    """返回 {slot: item_id}。"""
    row = session.get(PlayerRow, "player")
    if row is None:
        return {}
    return loads(row.equipment_json) or {}


def _item_attributes(item_row: ItemRow) -> dict[str, int]:
    """取物品的属性加成。"""
    attrs = loads(getattr(item_row, "attributes_json", "{}")) or {}
    if not attrs:
        # 没显式属性时按 kind + value 推断
        kind = item_row.kind
        v = item_row.value
        if kind in ("武器",):
            bonus = max(1, int(v * 5))
            return {"strength": bonus}
        if kind in ("甲", "甲胄"):
            bonus = max(1, int(v * 5))
            return {"strength": bonus}
        if kind == "工具":
            bonus = max(1, int(v * 3))
            return {"agility": bonus}
        if kind == "饰物":
            bonus = max(1, int(v * 3))
            return {"charisma": bonus}
    return {k: int(v) for k, v in attrs.items()}


def compute_total_attributes(session: Session, base: dict[str, int]) -> dict[str, int]:
    """玩家最终属性 = 基础 + 装备加成。"""
    eq = get_equipped(session)
    total = dict(base)
    for slot, item_id in eq.items():
        if not item_id:
            continue
        row = session.get(ItemRow, item_id)
        if row is None or row.consumed:
            continue
        for k, v in _item_attributes(row).items():
            total[k] = total.get(k, 0) + v
    return total


def equip(session: Session, player: Player, item_id: str) -> dict:
    row = session.get(ItemRow, item_id)
    if row is None:
        return {"ok": False, "error": "item not found"}
    if row.owner_id != "player":
        return {"ok": False, "error": "not your item"}
    if row.consumed:
        return {"ok": False, "error": "item consumed"}

    cat = getattr(row, "category", "material")
    if cat != "equipment":
        return {"ok": False, "error": "%s 不是装备" % row.name}

    slot = getattr(row, "slot", "") or item_meta.infer_slot(row.kind)
    if not slot:
        return {"ok": False, "error": "无法推断装备槽"}

    # 卸下旧装备（旧装备保留，只是不再加成）
    eq = get_equipped(session)
    eq[slot] = item_id

    pr = session.get(PlayerRow, "player")
    pr.equipment_json = dumps(eq)
    session.add(pr)
    session.commit()

    player.equipment = eq

    # 计算属性
    total = compute_total_attributes(session, player.attributes)
    return {
        "ok": True,
        "slot": slot,
        "slot_label": SLOT_LABELS.get(slot, slot),
        "item_id": item_id,
        "item_name": row.name,
        "attributes": _item_attributes(row),
        "total_attributes": total,
    }


def unequip(session: Session, player: Player, slot: str) -> dict:
    eq = get_equipped(session)
    old_id = eq.pop(slot, "")
    if not old_id:
        return {"ok": False, "error": "该槽位没有装备"}

    pr = session.get(PlayerRow, "player")
    pr.equipment_json = dumps(eq)
    session.add(pr)
    session.commit()

    player.equipment = eq
    total = compute_total_attributes(session, player.attributes)
    return {
        "ok": True,
        "slot": slot,
        "removed_item_id": old_id,
        "total_attributes": total,
    }


def equipped_summary(session: Session) -> list[dict]:
    """给前端显示已装备列表。"""
    eq = get_equipped(session)
    result = []
    for slot in SLOTS:
        item_id = eq.get(slot, "")
        row = session.get(ItemRow, item_id) if item_id else None
        if row is None or row.consumed:
            result.append({
                "slot": slot,
                "slot_label": SLOT_LABELS.get(slot, slot),
                "item_id": "",
                "item_name": "（空）",
                "attributes": {},
            })
            continue
        result.append({
            "slot": slot,
            "slot_label": SLOT_LABELS.get(slot, slot),
            "item_id": item_id,
            "item_name": row.name,
            "attributes": _item_attributes(row),
        })
    return result
