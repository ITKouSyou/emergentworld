# 行动时属性自然成长
from pathlib import Path

# ============================================================
# 1. player.py：加 try_natural_growth
# ============================================================
p = Path("server/systems/player.py")
t = p.read_text(encoding="utf-8")

if "def try_natural_growth" not in t:
    anchor = "def roll_check("
    addition = '''NATURAL_CAP = 15  # 自然成长上限

GROWTH_CHANCE = {
    "critical": 0.30,
    "success": 0.15,
    "partial": 0.05,
    "failure": 0.0,
}


def try_natural_growth(
    session,
    player,
    attribute: str,
    check_result: str,
    rng,
) -> bool:
    """行动后有概率自然成长属性。返回是否真的涨了。"""
    if check_result not in GROWTH_CHANCE:
        return False

    cur = int(player.attributes.get(attribute, 5))
    if cur >= NATURAL_CAP:
        return False

    # 属性越高，概率越低（15 时概率只剩 30%）
    base_chance = GROWTH_CHANCE[check_result]
    scale = max(0.3, 1.0 - (cur - 5) * 0.07)
    chance = base_chance * scale

    if rng.random() >= chance:
        return False

    # 直接改 PlayerRow
    from server.models.db import PlayerRow, dumps
    pr = session.get(PlayerRow, "player")
    if pr is None:
        return False

    import json
    attrs = json.loads(pr.attributes_json or "{}")
    attrs[attribute] = cur + 1
    pr.attributes_json = json.dumps(attrs, ensure_ascii=False)
    session.add(pr)
    session.commit()

    # 同步内存对象
    player.attributes[attribute] = cur + 1
    print("[growth] %s %d → %d（%s 后）" % (
        attribute, cur, cur + 1, check_result))
    return True


def roll_check('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] player.py 加 try_natural_growth")
    else:
        print("[fail] player.py 锚点未找到")
else:
    print("[skip] player.py 已有 try_natural_growth")

# ============================================================
# 2. actions.py：每个行动后尝试成长
# ============================================================
p = Path("server/systems/actions.py")
t = p.read_text(encoding="utf-8")

# 用一个统一包装函数
if "def _apply_growth" not in t:
    anchor = "def get_discovered("
    addition = '''def _apply_growth(session, world, player, action_result: dict, rng):
    """行动完成后，根据判定结果尝试属性成长。"""
    check = action_result.get("check")
    if not check or not isinstance(check, dict):
        return

    result = check.get("result")
    attribute = check.get("attribute")
    if not result or not attribute:
        return

    grew = player_sys.try_natural_growth(
        session, player, attribute, result, rng,
    )
    if grew:
        action_result["attribute_growth"] = {
            "attribute": attribute,
            "attribute_label": _attr_label(attribute),
            "new_value": int(player.attributes.get(attribute, 5)),
        }


def _attr_label(key: str) -> str:
    return {
        "strength": "力量",
        "agility": "敏捷",
        "intelligence": "智慧",
        "perception": "感知",
        "charisma": "魅力",
        "luck": "运气",
    }.get(key, key)


def get_discovered('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] actions.py 加 _apply_growth")
    else:
        print("[fail] actions.py 锚点未找到")
else:
    print("[skip] actions.py 已有 _apply_growth")

# 在 do_action 里调用
t = p.read_text(encoding="utf-8")
old = '''    if action == "explore":
        return await _do_explore(session, world, player, origin, rng, result)
    if action == "gather":
        return _do_gather(session, world, player, origin, rng, result)
    if action == "hunt":
        return _do_hunt(session, world, player, origin, rng, result)
    if action == "train":
        return _do_train(session, world, player, rng, result)
    if action == "socialize":
        return _do_socialize(session, world, player, rng, result)
    return result'''

new = '''    if action == "explore":
        out = await _do_explore(session, world, player, origin, rng, result)
    elif action == "gather":
        out = _do_gather(session, world, player, origin, rng, result)
    elif action == "hunt":
        out = _do_hunt(session, world, player, origin, rng, result)
    elif action == "train":
        out = _do_train(session, world, player, rng, result)
    elif action == "socialize":
        out = _do_socialize(session, world, player, rng, result)
    else:
        out = result

    _apply_growth(session, world, player, out, rng)
    return out'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] do_action 里调用 _apply_growth")
else:
    print("[skip] do_action 已改过或锚点未匹配")

# ============================================================
# 3. main.py：动作返回后带上 player 最新值
# ============================================================
# 已通过 _player_to_response 返回最新 player，无需改

print()
print("A 完成。下一步 fix54b.py（前端）")