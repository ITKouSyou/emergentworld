"""修 3 个旧测试以适配 Part 19A 新签名。"""
from pathlib import Path

# ---------- tests/test_event_flow.py ----------
p1 = Path("tests/test_event_flow.py")
t1 = p1.read_text(encoding="utf-8")
old1 = "async def fake_fill_event(tpl, world, npcs, rng):"
new1 = "async def fake_fill_event(tpl, world, npcs, rng, player=None):"
if old1 in t1:
    t1 = t1.replace(old1, new1)
    p1.write_text(t1, encoding="utf-8", newline="\n")
    print("[fix] test_event_flow.py fake_fill_event 加 player 参数")
else:
    print("[skip] test_event_flow.py 未匹配")

# ---------- tests/test_interactive.py ----------
p2 = Path("tests/test_interactive.py")
t2 = p2.read_text(encoding="utf-8")
old2 = "async def fake_fill(tpl, world, npcs, rng):"
new2 = "async def fake_fill(tpl, world, npcs, rng, player=None):"
if old2 in t2:
    t2 = t2.replace(old2, new2)
    p2.write_text(t2, encoding="utf-8", newline="\n")
    print("[fix] test_interactive.py fake_fill 加 player 参数")
else:
    print("[skip] test_interactive.py 未匹配")

# ---------- tests/test_event_participation.py ----------
p3 = Path("tests/test_event_participation.py")
t3 = p3.read_text(encoding="utf-8")

old3 = """        engine = _engine()
        with Session(engine) as s:
            world = create_world("t", seed=1)
            world.tick = 5
            save_world(s, world)

            save_npc(s, NPC(id="npc_a", name="Alden", age=30))
            save_npc(s, NPC(id="npc_b", name="Dain", age=30))"""

new3 = """        engine = _engine()
        with Session(engine) as s:
            world = create_world("t", seed=1)
            world.tick = 5
            save_world(s, world)

            # 创建玩家（Part 19A 起 resolve_event 需要玩家已存在）
            from server.systems import player as player_sys
            player_sys.create_player(s, "测试者", "male")

            save_npc(s, NPC(id="npc_a", name="Alden", age=30))
            save_npc(s, NPC(id="npc_b", name="Dain", age=30))"""

if old3 in t3:
    t3 = t3.replace(old3, new3)
    p3.write_text(t3, encoding="utf-8", newline="\n")
    print("[fix] test_event_participation.py 加玩家创建")
else:
    print("[skip] test_event_participation.py 未匹配")

print()
print("再跑：pytest -v")