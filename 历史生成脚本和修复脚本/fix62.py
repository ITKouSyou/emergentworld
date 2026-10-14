# 修 travel_endpoint 里的 _uuid
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 在 travel_endpoint 开头加 import uuid as _uuid
old = '''@app.post("/travel")
async def travel_endpoint(req: TravelRequest) -> dict:
    """玩家移动到已发现的地点，消耗 1 tick。"""
    from server.map_layout import LOCATION_LAYOUT'''

new = '''@app.post("/travel")
async def travel_endpoint(req: TravelRequest) -> dict:
    """玩家移动到已发现的地点，消耗 1 tick。"""
    import uuid as _uuid
    from server.map_layout import LOCATION_LAYOUT'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] travel_endpoint 加 import uuid")
else:
    print("[skip] 已改过或锚点未匹配")

# 顺便扫一下 main.py 里还有哪些函数用了 _uuid 但没 import
t2 = p.read_text(encoding="utf-8")
lines = t2.split("\n")

print()
print("=== 所有 _uuid 出现位置 ===")
for i, line in enumerate(lines):
    if "_uuid" in line:
        print("%4d | %s" % (i + 1, line.strip()[:100]))

print()
print("=== 所有有 import uuid 的位置 ===")
for i, line in enumerate(lines):
    if "import uuid" in line:
        print("%4d | %s" % (i + 1, line.strip()))

print()
print("重启后端：Ctrl+C → uvicorn server.main:app")