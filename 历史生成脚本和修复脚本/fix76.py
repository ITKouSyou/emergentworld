# 修 3 个测试兼容 + 1 个已删除函数引用
from pathlib import Path

# ---------- 1. test_event_flow.py：fake_fill 加 event_roles 参数 ----------
p = Path("tests/test_event_flow.py")
t = p.read_text(encoding="utf-8")

old1 = "async def fake_fill_event(tpl, world, npcs, rng, player=None):"
new1 = "async def fake_fill_event(tpl, world, npcs, rng, player=None, event_roles=None):"
n1 = t.count(old1)
if n1 > 0:
    t = t.replace(old1, new1)
    p.write_text(t, encoding="utf-8")
    print("[fix] test_event_flow.py fake_fill_event 加 event_roles (%d 处)" % n1)

# ---------- 2. test_interactive.py：同样 ----------
p = Path("tests/test_interactive.py")
t = p.read_text(encoding="utf-8")

old2 = "async def fake_fill(tpl, world, npcs, rng, player=None):"
new2 = "async def fake_fill(tpl, world, npcs, rng, player=None, event_roles=None):"
n2 = t.count(old2)
if n2 > 0:
    t = t.replace(old2, new2)
    p.write_text(t, encoding="utf-8")
    print("[fix] test_interactive.py fake_fill 加 event_roles (%d 处)" % n2)

# ---------- 3. test_behavior.py：decide 已删除，改用 step ----------
p = Path("tests/test_behavior.py")
t = p.read_text(encoding="utf-8")

old3 = '''def test_time_prefs_shift_by_hour():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.hour = 9  # morning
        save_world(s, world)
        npc = NPC(id="npc_x", name="X", age=30, goals=["赚钱"],
                  behavior_profile={"wealth": 0.9, "social": 0.5})
        save_npc(s, npc)
        rng = random.Random(1)
        action = behavior.decide(s, world, npc, rng)
        assert action.id in {"work", "explore", "eat", "socialize", "rest"}'''

new3 = '''def test_time_prefs_shift_by_hour():
    engine = _engine()
    with Session(engine) as s:
        world = create_world("t", seed=1)
        world.hour = 9  # morning
        save_world(s, world)
        npc = NPC(id="npc_x", name="X", age=30, goals=["赚钱"],
                  behavior_profile={"wealth": 0.9, "social": 0.5})
        save_npc(s, npc)
        # 新版 behavior.step 直接运行即可
        behavior.step(s, world)
        from server.core.world import load_npcs
        after = load_npcs(s)
        assert len(after) == 1
        assert after[0].location_id != ""'''

if old3 in t:
    t = t.replace(old3, new3, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] test_behavior.py decide → step")
else:
    print("[skip] test_behavior.py 已改过或锚点未匹配")

# ---------- 4. test_behavior.py：_npc_rng 名字可能也变了 ----------
t = p.read_text(encoding="utf-8")
if "behavior._npc_rng" in t:
    # 现在的 behavior.py 里应该还有 _npc_rng，检查一下
    bt = Path("server/systems/behavior.py").read_text(encoding="utf-8")
    if "_npc_rng" not in bt:
        print("[warn] behavior.py 里没有 _npc_rng，测试可能还需要改")

print()
print("跑：pytest -v")