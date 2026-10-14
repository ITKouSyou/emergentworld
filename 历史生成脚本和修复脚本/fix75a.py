# Part 75A：Director 加季节权重
from pathlib import Path

p = Path("server/core/director.py")
t = p.read_text(encoding="utf-8")

if "SEASON_TAG_WEIGHT" not in t:
    anchor = "TAG_SIGMA = 0.28"
    addition = '''TAG_SIGMA = 0.28

# 季节 → 各 tag 权重系数（乘在原有 score 上）
SEASON_TAG_WEIGHT: dict[str, dict[str, float]] = {
    "spring": {
        "romance": 1.4,
        "social": 1.2,
        "adventure": 1.2,
        "celebration": 1.2,
        "survival": 0.8,
        "conflict": 0.9,
    },
    "summer": {
        "adventure": 1.3,
        "trade": 1.2,
        "daily": 1.2,
        "conflict": 1.1,
        "survival": 0.9,
        "mystery": 1.0,
    },
    "autumn": {
        "trade": 1.4,
        "celebration": 1.4,
        "daily": 1.2,
        "investigation": 1.1,
        "romance": 0.9,
    },
    "winter": {
        "survival": 1.6,
        "conflict": 1.3,
        "ritual": 1.3,
        "social": 0.8,
        "romance": 0.7,
        "trade": 0.9,
    },
}


def _season_weight(tpl: EventTemplate, season: str) -> float:
    """根据季节给模板加权。取所有 tag 的最高系数。"""
    table = SEASON_TAG_WEIGHT.get(season)
    if not table or not tpl.tags:
        return 1.0
    weights = [table.get(tag, 1.0) for tag in tpl.tags]
    return max(weights)


def _season_max_reward_mult(season: str) -> float:
    """季节对奖励预算的影响。"""
    return {
        "spring": 1.0,
        "summer": 1.0,
        "autumn": 1.15,
        "winter": 0.85,
    }.get(season, 1.0)
'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] director.py 加季节权重")
    else:
        print("[fail] director.py 锚点未找到")
else:
    print("[skip] director.py 已有 SEASON_TAG_WEIGHT")

# 在 pick_template 里应用季节权重
t = p.read_text(encoding="utf-8")
old = '''        fit = fit_tension(tpl, tension)
        if fit < 0.05:
            continue

        diversity = recent_penalty(tpl.id, world)
        score = tpl.weight * fit * diversity * rhythm'''
new = '''        fit = fit_tension(tpl, tension)
        if fit < 0.05:
            continue

        diversity = recent_penalty(tpl.id, world)
        season_w = _season_weight(tpl, getattr(world, "season", "spring"))
        score = tpl.weight * fit * diversity * rhythm * season_w'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] pick_template 应用季节权重")
else:
    print("[skip] pick_template 已改过或锚点未匹配")

print()
print("A 完成。下一步 fix75b.py（8 个季节性事件）")