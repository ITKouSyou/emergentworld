# 修 claim_goal：直接改传入的 player 对象，一次性保存
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

    row.claimed = True
    session.add(row)
    session.commit()

    # 直接把奖励加到传入的 player 对象上
    if row.exp_reward > 0:
        player.exp += row.exp_reward
        # 升级循环
        while player.exp >= player.exp_next:
            player.exp -= player.exp_next
            player.level += 1
            player.unspent_points += 2
            player.exp_next = player_sys.exp_for_level(player.level)
            player.max_hp += 10
            player.hp = player.max_hp

    if row.money_reward > 0:
        player.money += row.money_reward

    player_sys.save_player(session, player)

    # 写入 reward 表（让奖励 Tab 能看到）
    try:
        from server.models.db import RewardRow, dumps
        import uuid as _uuid
        rr = RewardRow(
            id="rwd_goal_%s" % _uuid.uuid4().hex[:8],
            event_id="",
            kind="reputation" if row.money_reward > 0 else "skill",
            value=float(row.money_reward or row.exp_reward),
            description="完成目标：%s（经验 +%d，铜钱 +%d）" % (
                row.label, row.exp_reward, row.money_reward),
            payload_json=dumps({"goal_id": goal_id, "source": "goal"}),
        )
        session.add(rr)
        session.commit()
    except Exception as e:
        print("[goal] reward 写入失败：%s" % e)

    return {
        "ok": True,
        "label": row.label,
        "exp_reward": row.exp_reward,
        "money_reward": row.money_reward,
        "player_money": player.money,
        "player_level": player.level,
    }
'''

t = t[:start] + new_claim + t[end:]
p.write_text(t, encoding="utf-8")
print("[fix] claim_goal 重写")

# 确认 player_sys.exp_for_level 存在
p2 = Path("server/systems/player.py")
t2 = p2.read_text(encoding="utf-8")
if "def exp_for_level" in t2:
    print("[ok] player_sys.exp_for_level 存在")
else:
    print("[FAIL] 缺 exp_for_level")