# 诊断 money 字段
from pathlib import Path
import json
import urllib.request

print("=== 检查数据库表结构 ===")
import sqlite3
conn = sqlite3.connect("data/world.db")
cur = conn.cursor()
cur.execute("PRAGMA table_info(player)")
cols = [r[1] for r in cur.fetchall()]
print("player 表的列：", cols)
if "money" not in cols:
    print("[FAIL] player 表没有 money 列！迁移失败")
else:
    print("[ok] 有 money 列")
    cur.execute("SELECT id, name, money FROM player")
    print("当前值：", cur.fetchall())

conn.close()

print()
print("=== 检查 /player API 返回 ===")
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/player") as r:
        data = json.loads(r.read())
        print("money 字段：", data.get("money", "MISSING"))
except Exception as e:
    print("API 调用失败：", e)

print()
print("=== 检查 schemas.py 定义 ===")
p = Path("server/models/schemas.py")
t = p.read_text(encoding="utf-8")
i = t.find("class Player")
e = t.find("class ", i + 10)
chunk = t[i:e]
if "money" in chunk:
    print("[ok] Player 类里有 money")
else:
    print("[FAIL] Player 类里没有 money")

print()
print("=== 检查 player.py ===")
p = Path("server/systems/player.py")
t = p.read_text(encoding="utf-8")
print("load_player 用 money：%s" % ("money=row.money" in t))
print("save_player 用 money：%s" % ("row.money" in t))
print("create_player 初始 money：%s" % ("money=20" in t))