# 战斗难度按角色等级缩放
from pathlib import Path

p = Path("server/systems/actions.py")
t = p.read_text(encoding="utf-8")

old = '''    combat_check = player_sys.roll_check(player, "strength", "hard", rng)'''
new = '''    # 按等级选难度：1-2 级 normal，3-5 级 hard，6+ heroic
    lv = int(player.level)
    if lv <= 2:
        combat_diff = "normal"
    elif lv <= 5:
        combat_diff = "hard"
    else:
        combat_diff = "heroic"
    combat_check = player_sys.roll_check(player, "strength", combat_diff, rng)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 战斗难度按等级缩放")
else:
    print("[skip] 已改过")