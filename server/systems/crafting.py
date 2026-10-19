# 物品耐久 + 合成
from __future__ import annotations

import random
import uuid

from sqlmodel import Session, select

from server.models.db import ItemRow
from server.models.schemas import Player, World
from server.systems import player as player_sys


# ============================================================
# 耐久
# ============================================================

# 消耗耐久的行动类型：耐久扣除值
DURABILITY_COST = {
    "use": 15,
    "give": 5,
    "combat": 30,
}


def wear_item(session: Session, item_id: str, action: str, rng=None) -> dict:
    """消耗物品耐久。返回 {"broken": bool, "durability": int}。"""
    rng = rng or random.Random()
    row = session.get(ItemRow, item_id)
    if row is None:
        return {"broken": False, "durability": 0}

    cost = DURABILITY_COST.get(action, 10)
    # 加随机波动
    cost = int(cost * rng.uniform(0.7, 1.3))

    cur = getattr(row, "durability", 100)
    cur = max(0, cur - cost)
    row.durability = cur

    broken = cur <= 0
    if broken:
        row.consumed = True

    session.add(row)
    session.commit()

    return {
        "broken": broken,
        "durability": cur,
        "max_durability": getattr(row, "max_durability", 100),
        "cost": cost,
    }


# ============================================================
# 合成
# ============================================================

# 材料获取途径提示
MATERIAL_SOURCES = {
    "草药": "【森林】、【井边】、【深山老林】",
    "药材": "【森林】、【温泉】、【盐碱地】",
    "矿石": "【废弃矿洞】、【采石场】、【石林】",
    "燃料": "【村庄边缘】、【住处】、【废弃矿洞】",
    "布料": "【市场】购买",
    "食材": "【农田】、【果园】、【小溪】",
    "信物": "完成事件获得",
    "古物": "【荒坟】、【古庙遗址】，或事件获得",
    "材料": "各地采集或市场购买"
}

# 每个配方：(成品名, 成品 kind, 材料要求 {材料kind: 数量}, 成品 value)
RECIPES = [
    {
        "id": "heal_salve",
        "name": "金创药",
        "kind": "药材",
        "value": 0.4,
        "materials": {"草药": 2, "药材": 1},
        "desc": "由草药与药材熬制，能快速止血。",
        "durability": 60,
    },
    {
        "id": "iron_tool",
        "name": "铁制工具",
        "kind": "工具",
        "value": 0.5,
        "materials": {"矿石": 2, "燃料": 1},
        "desc": "由铁矿和煤块打造，结实耐用。",
        "durability": 150,
    },
    {
        "id": "fine_fabric",
        "name": "上等布料",
        "kind": "布料",
        "value": 0.35,
        "materials": {"布料": 3},
        "desc": "三块粗布拼接，密实平整。",
        "durability": 200,
    },
    {
        "id": "herbal_tea",
        "name": "草药茶",
        "kind": "食材",
        "value": 0.25,
        "materials": {"草药": 1, "食材": 1},
        "desc": "草药泡制，清热解毒。",
        "durability": 40,
    },
    {
        "id": "charm_talisman",
        "name": "护身符",
        "kind": "信物",
        "value": 0.6,
        "materials": {"信物": 1, "材料": 2, "古物": 1},
        "desc": "以信物为引，配以古物，据说能避邪。",
        "durability": 80,
    },
]


def _count_materials(session: Session, player_id: str = "player") -> dict[str, int]:
    """统计玩家身上各 kind 的数量。"""
    rows = session.exec(
        select(ItemRow).where(ItemRow.owner_id == player_id)
    ).all()
    counts: dict[str, int] = {}
    for r in rows:
        if r.consumed:
            continue
        counts[r.kind] = counts.get(r.kind, 0) + 1
    return counts


def list_available_recipes(session: Session, player_id: str = "player") -> list[dict]:
    """返回玩家可以合成的配方列表（含是否满足材料）。"""
    counts = _count_materials(session, player_id)
    result = []
    for rec in RECIPES:
        can_craft = True
        missing = []
        for kind, need in rec["materials"].items():
            have = counts.get(kind, 0)
            if have < need:
                can_craft = False
                missing.append("%s（缺 %d）" % (kind, need - have))
        result.append({
            "id": rec["id"],
            "name": rec["name"],
            "kind": rec["kind"],
            "desc": rec["desc"],
            "value": rec["value"],
            "materials": [
                {
                    "kind": k, 
                    "count": v, 
                    "have": counts.get(k, 0),
                    "source": MATERIAL_SOURCES.get(k, "未知地点")
                }
                for k, v in rec["materials"].items()
            ],
            "can_craft": can_craft,
            "missing": missing,
        })
    return result


def craft(session: Session, world: World, player: Player, recipe_id: str, rng=None) -> dict:
    """执行合成。"""
    rng = rng or random.Random()
    rec = next((r for r in RECIPES if r["id"] == recipe_id), None)
    if rec is None:
        return {"ok": False, "error": "recipe not found"}

    # 检查材料
    rows = session.exec(
        select(ItemRow).where(ItemRow.owner_id == "player")
    ).all()
    # 按 kind 分组，剔除已消耗
    by_kind: dict[str, list] = {}
    for r in rows:
        if r.consumed:
            continue
        by_kind.setdefault(r.kind, []).append(r)

    for kind, need in rec["materials"].items():
        if len(by_kind.get(kind, [])) < need:
            return {"ok": False, "error": "缺少%s" % kind}

    # 扣材料（标记 consumed）
    consumed_items = []
    for kind, need in rec["materials"].items():
        for i in range(need):
            item = by_kind[kind].pop(0)
            item.consumed = True
            session.add(item)
            consumed_items.append(item.id)
    session.commit()

    # 生成成品
    new_id = "itm_%s" % uuid.uuid4().hex[:8]
    dur = rec.get("durability", 100)
    row = ItemRow(
        id=new_id,
        reward_id="craft",
        event_id="",
        name=rec["name"],
        kind=rec["kind"],
        affixes_json="[]",
        story=rec["desc"],
        value=rec["value"],
        owner_id="player",
        consumed=False,
        durability=dur,
        max_durability=dur,
    )
    session.add(row)
    session.commit()

    return {
        "ok": True,
        "item_id": new_id,
        "item_name": rec["name"],
        "consumed_items": consumed_items,
    }
