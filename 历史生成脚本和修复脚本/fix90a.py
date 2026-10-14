# Part 90A：装备系统
from pathlib import Path

# ============================================================
# 1. schemas.py：Player 加 equipment
# ============================================================
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")

if "equipment: dict[str, str]" not in t:
    old = '''    factions: dict[str, int] = Field(default_factory=dict)
    created: bool = False'''
    new = '''    factions: dict[str, int] = Field(default_factory=dict)
    equipment: dict[str, str] = Field(default_factory=dict)   # {weapon: item_id, ...}
    created: bool = False'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py Player 加 equipment")

# ============================================================
# 2. db.py：PlayerRow 加 equipment_json
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "equipment_json" not in t:
    old = '''    factions_json: str = "{}"
    created: bool = False'''
    new = '''    factions_json: str = "{}"
    equipment_json: str = "{}"
    created: bool = False'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py PlayerRow 加 equipment_json")

# ============================================================
# 3. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "equipment_json" not in t:
    anchor = '        _add_col(conn, "player", "factions_json", "factions_json TEXT NOT NULL DEFAULT \'{}\'")\n'
    if anchor in t:
        t = t.replace(anchor,
            anchor + '        _add_col(conn, "player", "equipment_json", "equipment_json TEXT NOT NULL DEFAULT \'{}\'")\n',
            1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 equipment_json 迁移")

# ============================================================
# 4. player.py：读写 equipment
# ============================================================
p = Path("server/systems/player.py")
t = p.read_text(encoding="utf-8")

if "equipment=loads" not in t:
    old = '''        factions=loads(row.factions_json) or {},
        created=row.created,'''
    new = '''        factions=loads(row.factions_json) or {},
        equipment=loads(row.equipment_json) or {},
        created=row.created,'''
    if old in t:
        t = t.replace(old, new, 1)
        print("[fix] load_player 加 equipment")

if "row.equipment_json" not in t:
    old = '''    row.factions_json = dumps(player.factions)
    row.created = player.created'''
    new = '''    row.factions_json = dumps(player.factions)
    row.equipment_json = dumps(player.equipment)
    row.created = player.created'''
    if old in t:
        t = t.replace(old, new, 1)
        print("[fix] save_player 加 equipment")

p.write_text(t, encoding="utf-8")

# ============================================================
# 5. 新文件 equipment.py
# ============================================================
Path("server/systems/equipment.py").write_text('''# 装备系统
from __future__ import annotations

import json

from sqlmodel import Session

from server.models.db import ItemRow, PlayerRow, dumps, loads
from server.models.schemas import Player
from server.systems import inventory, item_meta


SLOTS = ["weapon", "armor", "accessory"]
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
''', encoding="utf-8")
print("[write] server/systems/equipment.py")

# ============================================================
# 6. main.py：加 /equip 和 /unequip 端点
# ============================================================
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

if "/equip" not in t:
    anchor = '''@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    addition = '''# ---------- Equipment ----------

class EquipRequest(BaseModel):
    item_id: str


class UnequipRequest(BaseModel):
    slot: str


@app.post("/equip")
def equip_endpoint(req: EquipRequest) -> dict:
    with get_session() as s:
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import equipment as equip_sys
        result = equip_sys.equip(s, player, req.item_id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "equip failed"))
        return result


@app.post("/unequip")
def unequip_endpoint(req: UnequipRequest) -> dict:
    with get_session() as s:
        player = player_sys.load_player(s)
        if player is None or not player.created:
            raise HTTPException(400, "player not created")
        from server.systems import equipment as equip_sys
        result = equip_sys.unequip(s, player, req.slot)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "unequip failed"))
        return result


@app.get("/equipment")
def get_equipment() -> dict:
    with get_session() as s:
        from server.systems import equipment as equip_sys
        return {"slots": equip_sys.equipped_summary(s)}


@app.get("/event")
def list_events(limit: int = 20) -> list[dict]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] main.py 加 /equip /unequip /equipment 端点")

# _player_to_response 里加 equipment 和 total_attributes
t = p.read_text(encoding="utf-8")
old = '''def _player_to_response(session, p) -> dict:
    """把 Player 转成带 known_locations 的响应 dict。"""
    from server.map_layout import LOCATION_LAYOUT
    data = p.model_dump()'''
new = '''def _player_to_response(session, p) -> dict:
    """把 Player 转成带 known_locations 的响应 dict。"""
    from server.map_layout import LOCATION_LAYOUT
    from server.systems import equipment as equip_sys
    data = p.model_dump()
    # 装备加成后的最终属性
    try:
        data["total_attributes"] = equip_sys.compute_total_attributes(session, p.attributes)
        data["equipment_slots"] = equip_sys.equipped_summary(session)
    except Exception as e:
        data["total_attributes"] = p.attributes
        data["equipment_slots"] = []'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _player_to_response 加装备属性")

print()
print("A 完成。下一步 fix90b.py")