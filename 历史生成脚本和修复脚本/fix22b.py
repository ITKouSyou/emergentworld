# 打猎加入战斗逻辑
from pathlib import Path

p = Path("server/systems/actions.py")
t = p.read_text(encoding="utf-8")

start = t.find("def _do_hunt(")
if start < 0:
    print("[fail] 找不到 _do_hunt")
    raise SystemExit(1)

end = t.find("\n\ndef ", start + 1)
if end < 0:
    end = len(t)

new_hunt = '''def _do_hunt(session, world, player, origin, rng, result):
    pool = HUNT_POOL.get(origin)
    if not pool:
        hint_map = {
            "old_mine": "矿洞里没有猎物，得去森林或山道",
            "river_bend": "河湾只有鱼虾，用打猎的方式不顶用",
            "deep_forest": "密林深处可以打猎",
        }
        hint = hint_map.get(origin, "这里没有猎物，去森林或山道这类地方才行。")
        result["message"] = hint
        result["summary"] = "你在%s想打猎，但这里没猎物" % location_label(origin)
        player_sys.add_exp(session, 2)
        result["exp_gain"] = 2
        return result

    # 第一步：潜行（敏捷）
    stealth = player_sys.roll_check(player, "agility", "normal", rng)
    result["check"] = stealth

    if stealth["result"] in ("critical", "success"):
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s猎得。" % location_label(origin), rng)
        result["exp_gain"] = 25 if stealth["result"] == "critical" else 15
        result["message"] = "你悄无声息地接近了猎物，一击得手。"
        result["summary"] = "你在%s猎得【%s】" % (location_label(origin), name)
        player_sys.add_exp(session, result["exp_gain"])
        return result

    if stealth["result"] == "partial":
        result["message"] = "你追了一阵，猎物跑掉了。"
        result["exp_gain"] = 8
        result["summary"] = "你在%s打猎，追了一阵，猎物跑了" % location_label(origin)
        player_sys.add_exp(session, result["exp_gain"])
        return result

    # 失败：激怒野兽，进入战斗
    beasts_by_loc = {
        "forest": [("野猪", 12, 2), ("野狼", 10, 3)],
        "deep_forest": [("野猪王", 20, 4), ("黑熊", 25, 5), ("猛虎", 30, 6)],
        "village_edge": [("流浪狗", 8, 1)],
        "mountain_pass": [("岩羊", 15, 3), ("山魈", 18, 4)],
    }
    beasts = beasts_by_loc.get(origin, [("野兽", 10, 2)])
    beast_name, beast_hp, beast_atk = rng.choice(beasts)

    combat_check = player_sys.roll_check(player, "strength", "hard", rng)
    result["check"] = combat_check
    result["combat"] = {
        "enemy": beast_name,
        "enemy_hp": beast_hp,
        "enemy_attack": beast_atk,
        "result": combat_check["result"],
    }

    beast_damage = max(1, beast_atk + rng.randint(-1, 2))
    hp_before = player.hp

    if combat_check["result"] == "critical":
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s搏斗中猎得。" % location_label(origin), rng)
        result["exp_gain"] = 40
        result["message"] = "你一拳打倒了%s，干净利落地解决了战斗。" % beast_name
        result["summary"] = "你在%s徒手斗杀【%s】，猎得【%s】" % (
            location_label(origin), beast_name, name)
    elif combat_check["result"] == "success":
        player.hp = max(1, player.hp - beast_damage // 2)
        name, kind = rng.choice(pool)
        result["found_item"] = _make_item(name, kind, "在%s搏斗中猎得。" % location_label(origin), rng)
        result["exp_gain"] = 30
        result["message"] = "你打退了%s，自己也擦破了皮。" % beast_name
        result["summary"] = "你在%s与【%s】搏斗获胜" % (location_label(origin), beast_name)
    elif combat_check["result"] == "partial":
        player.hp = max(1, player.hp - beast_damage)
        result["exp_gain"] = 15
        result["message"] = "你和%s缠斗，受了不轻的伤，它跑了。" % beast_name
        result["summary"] = "你在%s与【%s】缠斗，受伤但活了下来" % (
            location_label(origin), beast_name)
    else:
        player.hp = max(1, player.hp - beast_damage * 2)
        result["exp_gain"] = 5
        result["message"] = "你被%s扑倒，勉强爬起逃回村口。" % beast_name
        result["summary"] = "你在%s被【%s】重伤" % (location_label(origin), beast_name)
        player.location_id = "village_square"

    result["hp_before"] = hp_before
    result["hp_after"] = player.hp
    result["damage"] = hp_before - player.hp

    # 濒死：强制回村并回复一半
    if player.hp <= 1:
        player.hp = max(1, player.max_hp // 2)
        result["message"] += "（你昏睡了许久，醒来时已被人抬回了村里）"
        player.location_id = "village_square"
        result["hp_after"] = player.hp

    player_sys.save_player(session, player)
    player_sys.add_exp(session, result["exp_gain"])
    return result
'''

t = t[:start] + new_hunt + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] _do_hunt 重写为带战斗版本")
print()
print("B 完成。下一步 fix22c.py")