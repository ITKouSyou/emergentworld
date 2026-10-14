# 更新测试断言
from pathlib import Path

p = Path("tests/test_item_use.py")
t = p.read_text(encoding="utf-8")

old = '''        result = await item_use.use_item(s, world, "itm_1", "player", "npc_a")
        assert result["ok"] is True
        assert "Alden" in result["effect"]'''

new = '''        result = await item_use.use_item(s, world, "itm_1", "player", "npc_a")
        assert result["ok"] is True
        # 新版效果描述固定，不再拼 NPC 名
        assert "生命" in result["effect"] or "好感" in result["effect"]'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] test_item_use.py 更新断言")
else:
    print("[fail] 锚点未找到")

print()
print("跑：pytest -v")