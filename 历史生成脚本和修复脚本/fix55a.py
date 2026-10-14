# Part 55A：NPC 日程表（后端）
from pathlib import Path

# ============================================================
# 1. schemas.py：NPC 加 schedule
# ============================================================
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")

if "schedule: dict[str, str]" not in t:
    old = '''    location_id: str = "village_square"
    alive: bool = True
    family: Family = Field(default_factory=Family)'''
    new = '''    location_id: str = "village_square"
    alive: bool = True
    family: Family = Field(default_factory=Family)
    schedule: dict[str, str] = Field(default_factory=dict)'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py NPC 加 schedule")
    else:
        print("[fail] schemas.py 锚点未找到")
else:
    print("[skip] schemas.py 已有 schedule")

# ============================================================
# 2. db.py：NPCRow 加 schedule_json
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "schedule_json" not in t:
    old = '''    alive: bool = True
    family_json: str = "{}"'''
    new = '''    alive: bool = True
    family_json: str = "{}"
    schedule_json: str = "{}"'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py NPCRow 加 schedule_json")
    else:
        print("[fail] db.py 锚点未找到")
else:
    print("[skip] db.py 已有 schedule_json")

# ============================================================
# 3. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "schedule_json" not in t:
    anchor = "        _add_col(conn, \"npc\", \"family_json\", \"family_json TEXT NOT NULL DEFAULT '{}'\")\n"
    if anchor in t:
        t = t.replace(
            anchor,
            anchor + "        _add_col(conn, \"npc\", \"schedule_json\", \"schedule_json TEXT NOT NULL DEFAULT '{}'\")\n",
            1,
        )
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 schedule_json 迁移")
    else:
        print("[skip] session.py 迁移锚点未找到")
else:
    print("[skip] session.py 已有 schedule_json")

# ============================================================
# 4. world.py：读写 schedule
# ============================================================
p = Path("server/core/world.py")
t = p.read_text(encoding="utf-8")

if "schedule_json" not in t:
    # save_npc
    old_save = '    row.family_json = dumps(npc.family.model_dump())\n    session.add(row)'
    new_save = '    row.family_json = dumps(npc.family.model_dump())\n    row.schedule_json = dumps(npc.schedule)\n    session.add(row)'
    if old_save in t:
        t = t.replace(old_save, new_save, 1)
        print("[fix] world.py save_npc 加 schedule")

    # load_npcs
    old_load = '''            alive=r.alive,
            family=Family(**fam_data) if fam_data else Family(),
        ))
    return result'''
    new_load = '''            alive=r.alive,
            family=Family(**fam_data) if fam_data else Family(),
            schedule=loads(r.schedule_json) or {},
        ))
    return result'''
    if old_load in t:
        t = t.replace(old_load, new_load, 1)
        print("[fix] world.py load_npcs 加 schedule")

    p.write_text(t, encoding="utf-8")
else:
    print("[skip] world.py 已有 schedule")

# ============================================================
# 5. 新文件 schedule.py：日程生成
# ============================================================
Path("server/systems/schedule.py").write_text('''# NPC 日程表：按时段规定去哪
from __future__ import annotations

import random

from server.models.schemas import NPC

# 时段划分（按小时）
SLOTS = {
    "morning": (6, 11),
    "afternoon": (11, 17),
    "evening": (17, 21),
    "night": (21, 6),  # 跨夜
}


def slot_of_hour(hour: int) -> str:
    h = hour % 24
    if 6 <= h < 11:
        return "morning"
    if 11 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "night"


def generate_schedule(npc: NPC, rng: random.Random) -> dict[str, str]:
    """根据性格、目标、家庭生成日程。"""
    goals_text = " ".join(npc.goals).lower()
    traits = npc.traits or {}
    extraversion = float(traits.get("extraversion", 0.5))
    openness = float(traits.get("openness", 0.5))

    has_home = bool(npc.family.spouse or npc.family.children or npc.family.parents)
    is_elder = npc.age >= 55
    is_child = npc.age < 16

    schedule: dict[str, str] = {}

    # --- 白天（morning + afternoon）---
    if is_child:
        day_loc = "village_square"
    elif is_elder:
        day_loc = rng.choice(["home", "village_square", "market"])
    elif any(kw in goals_text for kw in ["钱", "wealth", "攒", "生意", "商"]):
        day_loc = "market"
    elif any(kw in goals_text for kw in ["探索", "寻", "冒险", "旅", "查", "远"]):
        day_loc = rng.choice(["forest", "village_edge", "market"])
    elif any(kw in goals_text for kw in ["手艺", "徒", "技"]):
        day_loc = "market"
    else:
        if openness > 0.6:
            day_loc = rng.choice(["forest", "village_square", "market"])
        else:
            day_loc = rng.choice(["market", "home", "village_hall"])

    schedule["morning"] = day_loc
    schedule["afternoon"] = day_loc

    # --- 傍晚 ---
    if is_child or is_elder:
        schedule["evening"] = "home"
    elif extraversion > 0.6:
        schedule["evening"] = rng.choice(["tavern", "village_square", "tavern"])
    elif any(kw in goals_text for kw in ["酒", "乐", "朋友", "社交"]):
        schedule["evening"] = "tavern"
    else:
        schedule["evening"] = rng.choice(["tavern", "village_square", "home"])

    # --- 夜里 ---
    # 有家的人基本都回家
    if has_home:
        schedule["night"] = "home"
    elif extraversion > 0.7 and rng.random() < 0.3:
        schedule["night"] = "tavern"  # 夜猫子
    else:
        schedule["night"] = "home"

    return schedule


def target_location(npc: NPC, hour: int) -> str:
    """根据当前小时，返回 NPC 该去的地方。"""
    if not npc.schedule:
        return npc.location_id
    slot = slot_of_hour(hour)
    return npc.schedule.get(slot, npc.location_id)


def describe_schedule(npc: NPC) -> list[str]:
    """给前端显示用。"""
    if not npc.schedule:
        return []
    labels = {
        "morning": "清晨",
        "afternoon": "白天",
        "evening": "傍晚",
        "night": "夜里",
    }
    loc_labels = {
        "village_square": "村庄广场",
        "market": "市场",
        "tavern": "酒馆",
        "home": "住处",
        "forest": "森林",
        "village_edge": "村庄边缘",
        "village_hall": "村公所",
    }
    result = []
    for slot in ["morning", "afternoon", "evening", "night"]:
        loc = npc.schedule.get(slot)
        if not loc:
            continue
        label = labels.get(slot, slot)
        loc_zh = loc_labels.get(loc, loc)
        result.append("%s：%s" % (label, loc_zh))
    return result
''', encoding="utf-8")
print("[write] server/systems/schedule.py")

# ============================================================
# 6. seed_world.py：生成 NPC 后分配日程
# ============================================================
p = Path("tools/seed_world.py")
t = p.read_text(encoding="utf-8")

if "generate_schedule" not in t:
    # 加 import
    t = t.replace(
        "from server.systems.family import build_families",
        "from server.systems.family import build_families\nfrom server.systems.schedule import generate_schedule",
        1,
    )
    # 在 build_families 之后调用
    old = '''        build_families(session, npcs, rng)
        print("built families")'''
    new = '''        build_families(session, npcs, rng)
        print("built families")

        # 分配日程
        for npc in npcs:
            npc.schedule = generate_schedule(npc, rng)
            save_npc(session, npc)
        print("assigned schedules")'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] seed_world.py 分配日程")
    else:
        print("[fail] seed_world.py 锚点未找到")
else:
    print("[skip] seed_world.py 已有 schedule")

print()
print("A 完成。下一步 fix55b.py（behavior 用日程）")