# 修 item_use.py 里 rng 未定义
from pathlib import Path

p = Path("server/systems/item_use.py")
t = p.read_text(encoding="utf-8")

# 在函数开头加 rng 定义
old = '''async def use_item(
    session: Session,
    world: World,
    item_id: str,
    user_id: str = "player",
    target_npc_id: str = "",
) -> dict:
    row = inventory.get_item_row(session, item_id)'''

new = '''async def use_item(
    session: Session,
    world: World,
    item_id: str,
    user_id: str = "player",
    target_npc_id: str = "",
) -> dict:
    import random
    rng = random.Random(world.seed * 100003 + world.tick)

    row = inventory.get_item_row(session, item_id)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] item_use.py 加 rng")
else:
    print("[fail] 锚点未找到")