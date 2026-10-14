# Part 82A：物品耐久
from pathlib import Path

# ============================================================
# 1. db.py：ItemRow 加 durability
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "durability" not in t:
    old = '''    owner_id: str = Field(default="", index=True)
    consumed: bool = False'''
    new = '''    owner_id: str = Field(default="", index=True)
    consumed: bool = False
    durability: int = 100
    max_durability: int = 100'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py ItemRow 加 durability")
    else:
        print("[fail] db.py 锚点未找到")
else:
    print("[skip] db.py 已有 durability")

# ============================================================
# 2. schemas.py：Item 加 durability
# ============================================================
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")

if "durability: int" not in t:
    old = '''class Item(BaseModel):
    id: str
    name: str
    kind: str
    affixes: list[str] = Field(default_factory=list)
    story: str = ""
    value: float = 0.0'''
    new = '''class Item(BaseModel):
    id: str
    name: str
    kind: str
    affixes: list[str] = Field(default_factory=list)
    story: str = ""
    value: float = 0.0
    durability: int = 100
    max_durability: int = 100'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py Item 加 durability")

# ============================================================
# 3. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "durability" not in t:
    anchor = '        _add_col(conn, "item", "consumed", "consumed INTEGER NOT NULL DEFAULT 0")\n'
    if anchor in t:
        t = t.replace(anchor,
            anchor + '        _add_col(conn, "item", "durability", "durability INTEGER NOT NULL DEFAULT 100")\n',
            1)
        t = t.replace(
            '        _add_col(conn, "item", "durability", "durability INTEGER NOT NULL DEFAULT 100")\n',
            '        _add_col(conn, "item", "durability", "durability INTEGER NOT NULL DEFAULT 100")\n        _add_col(conn, "item", "max_durability", "max_durability INTEGER NOT NULL DEFAULT 100")\n',
            1,
        )
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 durability 迁移")

# ============================================================
# 4. inventory.py：row_to_dict 加 durability
# ============================================================
p = Path("server/systems/inventory.py")
t = p.read_text(encoding="utf-8")

old = '''        "owner_id": row.owner_id,
        "consumed": row.consumed,
    }'''
new = '''        "owner_id": row.owner_id,
        "consumed": row.consumed,
        "durability": getattr(row, "durability", 100),
        "max_durability": getattr(row, "max_durability", 100),
    }'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] inventory.py row_to_dict 加 durability")

# ============================================================
# 5. 新文件：crafting.py（耐久 + 合成）
# ============================================================
Path("server/systems/crafting.py").write_text('''# 物品耐久 + 合成
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
                {"kind": k, "count": v, "have": counts.get(k, 0)}
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
''', encoding="utf-8")
print("[write] server/systems/crafting.py")

# ============================================================
# 6. item_use.py：使用物品时扣耐久
# ============================================================
p = Path("server/systems/item_use.py")
t = p.read_text(encoding="utf-8")

old = '''    consumed = bool(effect_data.get("consume", False))
    if consumed:
        inventory.consume_item(session, item_id)'''

new = '''    consumed = bool(effect_data.get("consume", False))
    if consumed:
        inventory.consume_item(session, item_id)
    else:
        # 不消耗但会扣耐久
        from server.systems import crafting as craft_sys
        wear = craft_sys.wear_item(session, item_id, "use", rng)
        if wear.get("broken"):
            print("[item] %s 已损坏" % row.name)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] item_use.py 使用扣耐久")
else:
    print("[skip] item_use.py 已改过或锚点未匹配")

print()
print("A 完成。下一步 fix82b.py（API + 前端）")