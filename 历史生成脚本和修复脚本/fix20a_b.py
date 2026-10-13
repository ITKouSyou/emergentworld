"""Part 20A - B：patch db.py / session.py / world.py / seed_world.py。

用简单字符串替换，不重写整个文件。
"""
from pathlib import Path

# ---------- db.py：NPCRow 加 family_json ----------
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "family_json" not in t:
    old = '    location_id: str = "village_square"\n    alive: bool = True\n\n\nclass MemoryRow'
    new = '    location_id: str = "village_square"\n    alive: bool = True\n    family_json: str = "{}"\n\n\nclass MemoryRow'
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8", newline="\n")
        print("[fix] db.py NPCRow 加 family_json")
    else:
        print("[fail] db.py 锚点未找到")
else:
    print("[skip] db.py 已有 family_json")

# ---------- session.py：加 family_json 迁移 ----------
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if 'family_json' not in t:
    anchor = '        _add_col(conn, "npc", "gender", "gender TEXT NOT NULL DEFAULT \'unknown\'")\n'
    addition = anchor + '        _add_col(conn, "npc", "family_json", "family_json TEXT NOT NULL DEFAULT \'{}\'")\n'
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8", newline="\n")
        print("[fix] session.py 加 family_json 迁移")
    else:
        print("[fail] session.py 锚点未找到")
else:
    print("[skip] session.py 已有 family_json")

# 加 relationship.kind 迁移
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")
if 'relationship' not in t or 'kind' not in t:
    anchor = '        _add_col(conn, "world", "social_count_today",\n                 "social_count_today INTEGER NOT NULL DEFAULT 0")\n'
    if anchor in t:
        t = t.replace(anchor, anchor + '        _add_col(conn, "relationship", "kind", "kind TEXT NOT NULL DEFAULT \'\'")\n', 1)
        p.write_text(t, encoding="utf-8", newline="\n")
        print("[fix] session.py 加 relationship.kind 迁移")
    else:
        print("[skip] relationship.kind 迁移锚点未找到")

# ---------- relationship.py：加 kind 字段 ----------
p = Path("server/systems/relationship.py")
t = p.read_text(encoding="utf-8")

if "kind=row.kind" not in t:
    # get_or_create 返回 Relationship 时带上 kind
    old1 = '''    return Relationship(
        id=row.id, from_npc=row.from_npc, to_npc=row.to_npc,
        trust=row.trust, affection=row.affection,
        fear=row.fear, debt=row.debt,
    )'''
    new1 = '''    return Relationship(
        id=row.id, from_npc=row.from_npc, to_npc=row.to_npc,
        trust=row.trust, affection=row.affection,
        fear=row.fear, debt=row.debt,
        kind=row.kind or "",
    )'''
    n = t.count(old1)
    if n > 0:
        t = t.replace(old1, new1)
        p.write_text(t, encoding="utf-8", newline="\n")
        print("[fix] relationship.py Relationship 加 kind（%d 处）" % n)
    else:
        print("[fail] relationship.py 锚点未找到")
else:
    print("[skip] relationship.py 已有 kind")

# ---------- world.py：读写 family_json ----------
p = Path("server/core/world.py")
t = p.read_text(encoding="utf-8")

if "family_json" not in t:
    # save_npc：加 family
    old_save = '    row.location_id = npc.location_id\n    row.alive = npc.alive\n    session.add(row)'
    new_save = '    row.location_id = npc.location_id\n    row.alive = npc.alive\n    row.family_json = dumps(npc.family.model_dump())\n    session.add(row)'
    if old_save in t:
        t = t.replace(old_save, new_save, 1)
        print("[fix] world.py save_npc 加 family")

    # load_npcs：加载 family
    old_load = '''def load_npcs(session: Session) -> list[NPC]:
    rows = session.exec(select(NPCRow).where(NPCRow.alive == True)).all()  # noqa: E712
    return [
        NPC(
            id=r.id,
            name=r.name,
            age=r.age,
            gender=r.gender or "unknown",
            traits=loads(r.traits_json) or {},
            needs=loads(r.needs_json) or {},
            goals=loads(r.goals_json) or [],
            behavior_profile=loads(r.behavior_json) or {},
            asset_params=loads(r.asset_json) or {},
            memory_ids=loads(r.memory_ids_json) or [],
            location_id=r.location_id,
            alive=r.alive,
        )
        for r in rows
    ]'''
    new_load = '''def load_npcs(session: Session) -> list[NPC]:
    rows = session.exec(select(NPCRow).where(NPCRow.alive == True)).all()  # noqa: E712
    result: list[NPC] = []
    for r in rows:
        fam_data = loads(r.family_json) or {}
        result.append(NPC(
            id=r.id, name=r.name, age=r.age,
            gender=r.gender or "unknown",
            traits=loads(r.traits_json) or {},
            needs=loads(r.needs_json) or {},
            goals=loads(r.goals_json) or [],
            behavior_profile=loads(r.behavior_json) or {},
            asset_params=loads(r.asset_json) or {},
            memory_ids=loads(r.memory_ids_json) or [],
            location_id=r.location_id,
            alive=r.alive,
            family=Family(**fam_data) if fam_data else Family(),
        ))
    return result'''
    if old_load in t:
        t = t.replace(old_load, new_load, 1)
        print("[fix] world.py load_npcs 加 family")
    else:
        print("[fail] world.py load_npcs 锚点未找到")

    # import Family
    if "Family" not in t.split("\n")[0:20]:
        t = t.replace(
            "from server.models.schemas import DirectorState, EconomyState, Event, NPC, World",
            "from server.models.schemas import DirectorState, EconomyState, Event, Family, NPC, World",
            1,
        )

    p.write_text(t, encoding="utf-8", newline="\n")
else:
    print("[skip] world.py 已有 family_json")

# ---------- seed_world.py：调用 build_families ----------
p = Path("tools/seed_world.py")
t = p.read_text(encoding="utf-8")

if "build_families" not in t:
    # 加 import
    t = t.replace(
        "from server.generators.npc import generate_npc",
        "from server.generators.npc import generate_npc\nfrom server.systems.family import build_families",
        1,
    )

    # 在 names 循环结束后调用
    old = '''        picks = pick_name_pool(n, rng)
        for name, gender in picks:
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            save_npc(session, npc)
            print("created npc %s %s (%s)" % (npc.id, npc.name, npc.gender))'''
    new = '''        picks = pick_name_pool(n, rng)
        npcs = []
        for name, gender in picks:
            npc = await generate_npc(name, context="一个偏远村庄", gender=gender)
            save_npc(session, npc)
            npcs.append(npc)
            print("created npc %s %s (%s)" % (npc.id, npc.name, npc.gender))

        build_families(session, npcs, rng)
        print("built families")
        for npc in npcs:
            fam = npc.family
            bits = []
            if fam.spouse: bits.append("配偶")
            if fam.children: bits.append("%d子女" % len(fam.children))
            if fam.parents: bits.append("父母")
            if fam.siblings: bits.append("%d兄弟姐妹" % len(fam.siblings))
            print("  %s: %s" % (npc.name, "、".join(bits) or "独身"))'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8", newline="\n")
        print("[fix] seed_world.py 加 build_families")
    else:
        print("[fail] seed_world.py 锚点未找到")
else:
    print("[skip] seed_world.py 已有 build_families")

print("\nB 部分完成。")