from pathlib import Path

# ============================================================
# 1. 后端：SLOTS 加 tool
# ============================================================
p = Path("server/systems/equipment.py")
t = p.read_text(encoding="utf-8")

old = 'SLOTS = ["weapon", "armor", "accessory"]'
new = 'SLOTS = ["weapon", "armor", "accessory", "tool"]'
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] equipment.py SLOTS 加 tool")
else:
    print("[skip] 已改过")

# 顺便调整槽位标签顺序
old_label = '''SLOT_LABELS = {
    "weapon": "武器",
    "armor": "护甲",
    "accessory": "饰物",
    "tool": "工具",
}'''
if old_label in t:
    print("[ok] SLOT_LABELS 已含 tool")

# ============================================================
# 2. 前端：装备槽加 tool
# ============================================================
p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = '''	for slot_key in ["weapon", "armor", "accessory"]:'''
new = '''	for slot_key in ["weapon", "armor", "accessory", "tool"]:'''
if old in t:
    t = t.replace(old, new, 1)
    print("[fix] 前端装备槽加 tool")
else:
    print("[skip] 前端已改过")

# 槽位名映射加 tool
old_map = '''		slot_lbl.text = {"weapon": "武器", "armor": "护甲", "accessory": "饰物"}.get(slot_key, slot_key)'''
new_map = '''		slot_lbl.text = {"weapon": "武器", "armor": "护甲", "accessory": "饰物", "tool": "工具"}.get(slot_key, slot_key)'''
if old_map in t:
    t = t.replace(old_map, new_map, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 槽位名加 tool")
else:
    print("[skip] 槽位名映射已改过或未匹配")
    p.write_text(t, encoding="utf-8")

print()
print("重启后端 + Godot 完全关闭重开")