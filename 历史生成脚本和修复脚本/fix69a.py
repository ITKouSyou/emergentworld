# Part 69A：派系数据结构
from pathlib import Path

# ============================================================
# 1. schemas.py：Player 加 factions，NPC 加 faction
# ============================================================
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")

# Player.factions
if "factions: dict[str, int]" not in t:
    old = '''    background: str = ""
    known_npcs: list[str] = Field(default_factory=list)
    created: bool = False'''
    new = '''    background: str = ""
    known_npcs: list[str] = Field(default_factory=list)
    factions: dict[str, int] = Field(default_factory=dict)
    created: bool = False'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py Player 加 factions")
    else:
        print("[fail] Player 锚点未找到")

# NPC.faction
t = p.read_text(encoding="utf-8")
if "faction: str" not in t.split("class NPC")[1].split("class ")[0]:
    old = '''    # 对玩家的印象：{ tag: count }，tag 如 "helped_child" / "betrayed_me"
    impressions: dict[str, int] = Field(default_factory=dict)'''
    new = '''    # 对玩家的印象：{ tag: count }
    impressions: dict[str, int] = Field(default_factory=dict)
    # 所属派系
    faction: str = "neutral"'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] schemas.py NPC 加 faction")
    else:
        print("[fail] NPC 锚点未找到")
else:
    print("[skip] NPC 已有 faction")

# ============================================================
# 2. db.py：PlayerRow 加 factions_json，NPCRow 加 faction
# ============================================================
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")

if "factions_json" not in t:
    old = '''    known_npcs_json: str = "[]"
    created: bool = False'''
    new = '''    known_npcs_json: str = "[]"
    factions_json: str = "{}"
    created: bool = False'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py PlayerRow 加 factions_json")

if "faction: str = \"neutral\"" not in t:
    old = '''    schedule_json: str = "{}"
    impressions_json: str = "{}"'''
    new = '''    schedule_json: str = "{}"
    impressions_json: str = "{}"
    faction: str = "neutral"'''
    if old in t:
        t = t.replace(old, new, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] db.py NPCRow 加 faction")

# ============================================================
# 3. session.py：迁移
# ============================================================
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")

if "factions_json" not in t:
    anchor = '        _add_col(conn, "player", "money", "money INTEGER NOT NULL DEFAULT 0")\n'
    if anchor in t:
        t = t.replace(anchor,
            anchor + '        _add_col(conn, "player", "factions_json", "factions_json TEXT NOT NULL DEFAULT \'{}\'")\n',
            1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 factions_json 迁移")

if '"faction"' not in t:
    anchor2 = '        _add_col(conn, "npc", "impressions_json", "impressions_json TEXT NOT NULL DEFAULT \'{}\'")\n'
    if anchor2 in t:
        t = t.replace(anchor2,
            anchor2 + '        _add_col(conn, "npc", "faction", "faction TEXT NOT NULL DEFAULT \'neutral\'")\n',
            1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 npc.faction 迁移")

# ============================================================
# 4. world.py：读写 faction
# ============================================================
p = Path("server/core/world.py")
t = p.read_text(encoding="utf-8")

if "row.faction" not in t:
    old = '    row.impressions_json = dumps(npc.impressions)\n    session.add(row)'
    new = '    row.impressions_json = dumps(npc.impressions)\n    row.faction = npc.faction\n    session.add(row)'
    if old in t:
        t = t.replace(old, new, 1)
        print("[fix] world.py save_npc 加 faction")

    old2 = '''            schedule=loads(r.schedule_json) or {},
            impressions=loads(r.impressions_json) or {},
        ))'''
    new2 = '''            schedule=loads(r.schedule_json) or {},
            impressions=loads(r.impressions_json) or {},
            faction=r.faction or "neutral",
        ))'''
    if old2 in t:
        t = t.replace(old2, new2, 1)
        print("[fix] world.py load_npcs 加 faction")

    p.write_text(t, encoding="utf-8")
else:
    print("[skip] world.py 已有 faction")

# ============================================================
# 5. player.py：读写 factions
# ============================================================
p = Path("server/systems/player.py")
t = p.read_text(encoding="utf-8")

if "factions=loads" not in t:
    old = '''        known_npcs=loads(row.known_npcs_json) or [],
        created=row.created,'''
    new = '''        known_npcs=loads(row.known_npcs_json) or [],
        factions=loads(row.factions_json) or {},
        created=row.created,'''
    if old in t:
        t = t.replace(old, new, 1)
        print("[fix] player.load_player 加 factions")

if "row.factions_json" not in t:
    old2 = '''    row.known_npcs_json = dumps(player.known_npcs)
    row.created = player.created'''
    new2 = '''    row.known_npcs_json = dumps(player.known_npcs)
    row.factions_json = dumps(player.factions)
    row.created = player.created'''
    if old2 in t:
        t = t.replace(old2, new2, 1)
        print("[fix] player.save_player 加 factions")

p.write_text(t, encoding="utf-8")

# 给 create_player 加初始派系声望
t = p.read_text(encoding="utf-8")
if '"elder": 0' not in t and "factions={" not in t:
    old3 = '''        known_npcs=[],
        created=True,
    )'''
    new3 = '''        known_npcs=[],
        factions={"elder": 0, "merchant": 0, "farmer": 0},
        created=True,
    )'''
    if old3 in t:
        t = t.replace(old3, new3, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] create_player 初始派系")

print()
print("A 完成。下一步 fix69b.py（faction 系统）")