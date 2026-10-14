# 诊断物品 category
import sqlite3
import json

conn = sqlite3.connect("data/world.db")
rows = conn.execute("""
    SELECT id, name, kind, category, use_effect_json, slot
    FROM item
    WHERE consumed = 0
    LIMIT 30
""").fetchall()

print("=== 未消耗物品的 category ===")
for r in rows:
    iid, name, kind, cat, eff, slot = r
    print("  %-20s kind=%-6s cat=%-12s slot=%s" % (name[:20], kind, cat or "(空)", slot or ""))

conn.close()

print()
print("=== item_meta.infer_category('工具') ===")
from server.systems import item_meta
print("  →", item_meta.infer_category("工具"))
print("  →", item_meta.infer_category("武器"))
print("  →", item_meta.infer_category("矿石"))