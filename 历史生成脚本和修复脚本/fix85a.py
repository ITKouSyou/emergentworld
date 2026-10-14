# Part 85A：物品分类 + 使用效果
from pathlib import Path

# ============================================================
# 1. schemas.py：Item 加字段
# ============================================================
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")

if "category: str" not in t.split("class Item")[1][:500]:
    old = '''class Item(BaseModel):
    id: str
    name: str
    kind: str
    affixes: list[str] = Field(default_factory=list)
    story: str = ""
    value: float = 0.0
    durability: int = 100
    max_durability: int = 100'''
    new = '''class Item(BaseModel):
    id: str
    name: str
    kind: str
    category: str = "material"    # consumable / equipment / material / key / quest
    affixes: list[str] = Field(default_factory=list)
    story: str = ""
    value: float = 0.0
    durability: int = 100
    max_durability: int = 100
    use_effect: dict[str, float] = Field(default_factory=dict)   # {"hp": +20, "hunger": -0.3}
    slot: str = ""                 # weapon / armor / accessory / tool
    attributes: dict[str, int] = Field(default_factory=dict)'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py Item 加 category/use_effect/slot/attributes")

# ============================================================
# 2. db.py：ItemRow 加字段
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "use_effect_json" not in t:
    old = '''    owner_id: str = Field(default="", index=True)
    consumed: bool = False
    durability: int = 100
    max_durability: int = 100'''
    new = '''    owner_id: str = Field(default="", index=True)
    consumed: bool = False
    durability: int = 100
    max_durability: int = 100
    category: str = "material"
    use_effect_json: str = "{}"
    slot: str = ""
    attributes_json: str = "{}"'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py ItemRow 加字段")

# ============================================================
# 3. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "use_effect_json" not in t:
    anchor = '        _add_col(conn, "item", "max_durability", "max_durability INTEGER NOT NULL DEFAULT 100")\n'
    if anchor in t:
        add = (
            '        _add_col(conn, "item", "category", "category TEXT NOT NULL DEFAULT \'material\'")\n'
            + '        _add_col(conn, "item", "use_effect_json", "use_effect_json TEXT NOT NULL DEFAULT \'{}\'")\n'
            + '        _add_col(conn, "item", "slot", "slot TEXT NOT NULL DEFAULT \'\'")\n'
            + '        _add_col(conn, "item", "attributes_json", "attributes_json TEXT NOT NULL DEFAULT \'{}\'")\n'
        )
        t = t.replace(anchor, anchor + add, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 item 字段迁移")

# ============================================================
# 4. 新文件：item_meta.py（按 kind 推断 category / use_effect / slot）
# ============================================================
Path("server/systems/item_meta.py").write_text('''# 物品分类推断
from __future__ import annotations

# kind → category
CATEGORY_BY_KIND = {
    # 消耗品
    "食材": "consumable",
    "食物": "consumable",
    "药材": "consumable",
    "药": "consumable",
    "酒": "consumable",
    # 装备
    "工具": "equipment",
    "武器": "equipment",
    "甲": "equipment",
    "甲胄": "equipment",
    "饰物": "equipment",
    # 材料
    "矿石": "material",
    "布料": "material",
    "材料": "material",
    "燃料": "material",
    "杂物": "material",
    "肥料": "material",
    # 特殊
    "信物": "quest",
    "古物": "quest",
    "钥匙": "key",
}

# kind → use_effect（consumable 时）
EFFECT_BY_KIND = {
    "食材": {"hunger": -0.3},
    "食物": {"hunger": -0.4, "hp": 5},
    "药材": {"hp": 15},
    "药": {"hp": 25},
    "酒": {"hp": 5, "hunger": -0.1},
}

# kind → slot（equipment 时）
SLOT_BY_KIND = {
    "工具": "tool",
    "武器": "weapon",
    "甲": "armor",
    "甲胄": "armor",
    "饰物": "accessory",
}


def infer_category(kind: str) -> str:
    return CATEGORY_BY_KIND.get(kind, "material")


def infer_effect(kind: str) -> dict:
    return dict(EFFECT_BY_KIND.get(kind, {}))


def infer_slot(kind: str) -> str:
    return SLOT_BY_KIND.get(kind, "")


def has_durability(kind: str) -> bool:
    """只有 equipment 才有耐久。"""
    return infer_category(kind) == "equipment"
''', encoding="utf-8")
print("[write] server/systems/item_meta.py")

# ============================================================
# 5. item_use.py：按 category 分支处理
# ============================================================
p = Path("server/systems/item_use.py")
t = p.read_text(encoding="utf-8")

start = t.find("async def use_item(")
if start < 0:
    print("[fail] 找不到 use_item")
    raise SystemExit(1)

end = t.find("\n\ndef ", start + 1)
if end < 0:
    end = len(t)

new_func = '''async def use_item(
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
'''

t = t[:start] + new_func + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] item_use.py 按 category 分支")

print()
print("A 完成。下一步 fix85b.py")