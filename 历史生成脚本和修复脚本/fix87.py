# 更新 test_item_use.py 适配新分类
from pathlib import Path

p = Path("tests/test_item_use.py")
t = p.read_text(encoding="utf-8")

# _setup 里把物品 kind 改成"药材"（消耗品）
old = '''    row = ItemRow(
        id="itm_1",
        reward_id="rwd_1",
        event_id="evt_1",
        name="护身符",
        kind="信物",
        affixes_json=dumps(["粗糙的"]),
        story="护身",
        value=0.4,
        owner_id="player",
    )'''
new = '''    row = ItemRow(
        id="itm_1",
        reward_id="rwd_1",
        event_id="evt_1",
        name="护身符",
        kind="药材",       # 消耗品，可以"使用"
        category="consumable",
        use_effect_json='{"hp": 15}',
        affixes_json=dumps(["粗糙的"]),
        story="护身",
        value=0.4,
        owner_id="player",
    )'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] test_item_use.py 物品改成消耗品")
else:
    print("[fail] 锚点未找到")

print()
print("跑：pytest -v")