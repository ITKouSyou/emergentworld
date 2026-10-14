# 直接改 PlayerRow 数据库行，绕过缓存
from pathlib import Path

p = Path("server/systems/goal.py")
t = p.read_text(encoding="utf-8")

start = t.find("def claim_goal(")
if start < 0:
    print("[fail] 找不到 claim_goal")
    raise SystemExit(1)

end = t.find("\n\ndef ", start + 1)
if end < 0:
    end = len(t)

new_claim = '''def claim_goal(session: Session, world: World, player: Player, goal_id: str) -> dict:
    row = session.get(GoalRow, goal_id)
    if row is None:
        return {"ok": False, "error": "goal not found"}
    if not row.done:
        return {"ok": False, "error": "goal not done"}
    if row.claimed:
        return {"ok": False, "error": "already claimed"}

    # 直接读数据库里的 PlayerRow，改它
    from server.models.db import PlayerRow
    pr = session.get(PlayerRow, "player")
    if pr is None:
        return {"ok": False, "error": "player row not found"}

    row.claimed = True
    session.add(row)

    exp_added = 0
    money_added = 0

    if row.exp_reward > 0:
        pr.exp = (pr.exp or 0) + row.exp_reward
        exp_added = row.exp_reward
        # 升级
        while pr.exp >= pr.exp_next:
            pr.exp -= pr.exp_next
            pr.level += 1
            pr.unspent_points = (pr.unspent_points or 0) + 2
            pr.exp_next = player_sys.exp_for_level(pr.level)
            pr.max_hp = (pr.max_hp or 100) + 10
            pr.hp = pr.max_hp

    if row.money_reward > 0:
        pr.money = (pr.money or 0) + row.money_reward
        money_added = row.money_reward

    session.add(pr)
    session.commit()
    session.refresh(pr)

    print("[claim] goal=%s exp+%d money+%d -> pr.money=%d lv=%d" % (
        goal_id, exp_added, money_added, pr.money, pr.level))

    # 同步回传入的 Player（让调用方看到最新值）
    player.exp = pr.exp
    player.level = pr.level
    player.money = pr.money
    player.max_hp = pr.max_hp
    player.hp = pr.hp
    player.unspent_points = pr.unspent_points
    player.exp_next = pr.exp_next

    # 写 Reward
    try:
        from server.models.db import RewardRow, dumps
        import uuid as _uuid
        rr = RewardRow(
            id="rwd_goal_%s" % _uuid.uuid4().hex[:8],
            event_id="",
            kind="reputation" if money_added > 0 else "skill",
            value=float(money_added or exp_added),
            description="完成目标：%s（经验 +%d，铜钱 +%d）" % (
                row.label, exp_added, money_added),
            payload_json=dumps({"goal_id": goal_id, "source": "goal"}),
        )
        session.add(rr)
        session.commit()
    except Exception as e:
        print("[goal] reward 写入失败：%s" % e)

    return {
        "ok": True,
        "label": row.label,
        "exp_reward": exp_added,
        "money_reward": money_added,
        "player_money": pr.money,
        "player_level": pr.level,
    }
'''

t = t[:start] + new_claim + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] claim_goal 改为直接操作 PlayerRow")

# 顺便修 trade_sell / action 里的钱，也用同样思路
p2 = Path("server/systems/market.py")
t2 = p2.read_text(encoding="utf-8")

old_sell = '''    price = sell_price(row.value, world)
    player.money += price
    # 标记为已消耗（从库存移除）
    row.consumed = True
    session.add(row)
    player_sys.save_player(session, player)'''

new_sell = '''    price = sell_price(row.value, world)
    row.consumed = True
    session.add(row)

    # 直接改 PlayerRow
    from server.models.db import PlayerRow
    pr = session.get(PlayerRow, "player")
    if pr is not None:
        pr.money = (pr.money or 0) + price
        session.add(pr)
        player.money = pr.money

    session.commit()'''

if old_sell in t2:
    t2 = t2.replace(old_sell, new_sell, 1)
    p2.write_text(t2, encoding="utf-8")
    print("[fix] sell_item 也改为直改 PlayerRow")
else:
    print("[skip] sell_item 已改过")