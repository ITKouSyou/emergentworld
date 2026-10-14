# Player 加 money 字段
from pathlib import Path

# schemas
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")
old = '''    reputation: int = 0
    hp: int = 100
    max_hp: int = 100'''
new = '''    reputation: int = 0
    hp: int = 100
    max_hp: int = 100
    money: int = 0'''
if old in t and "\n    money:" not in t.split("class NPC")[0]:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] schemas.py Player 加 money")

# db
p = Path("server/models/db.py")
t = p.read_text(encoding="utf-8")
old = '''    hp: int = 100
    max_hp: int = 100
    background: str = ""'''
new = '''    hp: int = 100
    max_hp: int = 100
    money: int = 0
    background: str = ""'''
if old in t and "money: int = 0" not in t.split("class NPCRow")[0]:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] db.py PlayerRow 加 money")

# session 迁移
p = Path("server/db/session.py")
t = p.read_text(encoding="utf-8")
if '"money"' not in t:
    anchor = '        _add_col(conn, "npc", "family_json", "family_json TEXT NOT NULL DEFAULT \'{}\'")\n'
    if anchor in t:
        t = t.replace(anchor, anchor + '        _add_col(conn, "player", "money", "money INTEGER NOT NULL DEFAULT 0")\n', 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] session.py 加 money 迁移")

# player.py
p = Path("server/systems/player.py")
t = p.read_text(encoding="utf-8")

old_load = '''        reputation=row.reputation,
        hp=row.hp,
        max_hp=row.max_hp,'''
new_load = '''        reputation=row.reputation,
        hp=row.hp,
        max_hp=row.max_hp,
        money=row.money or 0,'''
if old_load in t and "money=row.money" not in t:
    t = t.replace(old_load, new_load, 1)
    print("[fix] player.load_player 加 money")

old_save = '''    row.reputation = player.reputation
    row.hp = player.hp
    row.max_hp = player.max_hp'''
new_save = '''    row.reputation = player.reputation
    row.hp = player.hp
    row.max_hp = player.max_hp
    row.money = player.money'''
if old_save in t and "row.money" not in t:
    t = t.replace(old_save, new_save, 1)
    print("[fix] player.save_player 加 money")

old_create = '''        reputation=0,
        hp=100,
        max_hp=100,'''
new_create = '''        reputation=0,
        hp=100,
        max_hp=100,
        money=20,'''
if old_create in t and "money=20" not in t:
    t = t.replace(old_create, new_create, 1)
    print("[fix] player.create_player 初始 money=20")

p.write_text(t, encoding="utf-8")
print()
print("A 完成。下一步 fix22b.py")