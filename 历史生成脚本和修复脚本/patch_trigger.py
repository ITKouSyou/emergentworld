"""调整事件自动触发概率，并加一个保底：gap >= 20 时必触发。"""
from pathlib import Path

p = Path("server/core/director.py")
text = p.read_text(encoding="utf-8")

OLD = '''def should_trigger(world: World, rng: random.Random) -> bool:
    """每 tick 判断是否尝试触发。张力高、间隔久时更容易。"""
    gap = world.tick - world.director.last_event_tick
    if gap < 3:
        return False

    base = 0.015 + world.director.tension * 0.05
    if gap < 8:
        base *= 0.5
    elif gap >= 30:
        base *= 1.8

    return rng.random() < base'''

NEW = '''def should_trigger(world: World, rng: random.Random) -> bool:
    """每 tick 判断是否尝试触发。张力高、间隔久时更容易。

    保底机制：距上次事件 20 tick 以上必定触发一次，
    避免长时间静默让玩家觉得"世界卡住了"。
    """
    gap = world.tick - world.director.last_event_tick
    if gap < 3:
        return False

    # 保底
    if gap >= 20:
        return True

    base = 0.03 + world.director.tension * 0.10
    if gap < 8:
        base *= 0.5
    elif gap >= 12:
        base *= 1.6

    return rng.random() < base'''

if OLD not in text:
    print("未找到 should_trigger，可能已经改过。请手动检查 server/core/director.py")
    raise SystemExit(1)

text = text.replace(OLD, NEW)
p.write_text(text, encoding="utf-8", newline="\n")
print("[fix] should_trigger 已调整")
print()
print("改动：")
print("  - 基础触发率 1.5% → 3%")
print("  - 张力系数 0.05 → 0.10")
print("  - gap >= 12 时 ×1.6")
print("  - gap >= 20 时强制触发（保底）")
print()
print("重启后端生效：uvicorn server.main:app --reload")