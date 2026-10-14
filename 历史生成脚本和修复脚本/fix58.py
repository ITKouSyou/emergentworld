# 整段重写 npc.py
from pathlib import Path

content = '''# NPC 生成器：LLM + 规则兜底
from __future__ import annotations

import random
import uuid

from server.core.evaluator import evaluate_npc
from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC

TRAIT_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
NEED_KEYS = ["hunger", "safety", "social", "wealth", "curiosity"]

GENDER_ZH = {"male": "男", "female": "女", "unknown": "未知"}

FALLBACK_GOALS = [
    ["攒够钱翻修老屋", "让家人过上好日子"],
    ["找出当年害我的人", "不再被人轻视"],
    ["娶妻成家", "在村里有一席之地"],
    ["守住祖上的手艺", "收一个徒弟"],
    ["攒够盘缠去远方", "看一眼外面的世界"],
    ["让病重的亲人痊愈", "还清欠下的债"],
    ["赢得村人的尊重", "不再被人指指点点"],
    ["读到更多的书", "写一本自己的书"],
    ["变得更强壮", "保护想保护的人"],
    ["查明兄长的死因", "为他讨回公道"],
    ["学会酿酒", "开一间自己的酒铺"],
    ["找到失散多年的姐姐", "带她回来团圆"],
    ["成为村里最会打猎的人", "让父亲刮目相看"],
    ["攒钱赎回被典当的祖传玉佩", "重振家门"],
]


def gender_zh(gender: str) -> str:
    return GENDER_ZH.get(gender, "未知")


def _default_npc(npc_id: str, seed_name: str, gender: str = "unknown") -> NPC:
    rng = random.Random(hash(npc_id) & 0xFFFF)
    traits = {k: round(rng.uniform(0.25, 0.75), 2) for k in TRAIT_KEYS}
    needs = {k: round(rng.uniform(0.3, 0.7), 2) for k in NEED_KEYS}
    goals = rng.choice(FALLBACK_GOALS)
    return NPC(
        id=npc_id,
        name=seed_name,
        age=rng.randint(18, 55),
        gender=gender,
        traits=traits,
        needs=needs,
        goals=list(goals),
        behavior_profile={k: 0.5 for k in NEED_KEYS},
        asset_params={"hair": "short", "outfit": "plain", "palette": "neutral"},
    )


async def generate_npc(seed_name: str, context: str = "", gender: str = "unknown") -> NPC:
    npc_id = "npc_%s" % uuid.uuid4().hex[:8]
    fallback = _default_npc(npc_id, seed_name, gender)

    prompt = load_prompt("npc_gen.md").format(
        name=seed_name, gender=gender_zh(gender), context=context,
    )
    npc = await get_llm().json(prompt, NPC, fallback=fallback)
    npc.id = npc_id
    npc.name = npc.name or seed_name
    if gender != "unknown":
        npc.gender = gender

    # 检测套话 goals（关键词匹配），强制替换
    COMMON_KEYWORDS = [
        "安稳度日", "照顾好家人", "过好日子", "平平安安",
        "安安稳稳", "平淡", "安稳", "好好生活", "平淡度日",
        "安静地生活", "平静地生活", "安稳生活",
    ]

    def _is_common(g: str) -> bool:
        return any(kw in g for kw in COMMON_KEYWORDS)

    if not npc.goals or all(_is_common(g) for g in npc.goals):
        rng2 = random.Random(uuid.uuid4().int)
        npc.goals = list(rng2.choice(FALLBACK_GOALS))
        print("[npc] %s 的 goals 是套话，替换为 %r" % (npc.name, npc.goals))
    else:
        print("[npc] %s 的 goals: %r" % (npc.name, npc.goals))

    ok, _ = evaluate_npc(npc)
    if not ok:
        return fallback
    return npc
'''

p = Path("server/generators/npc.py")
p.write_text(content, encoding="utf-8")
print("[fix] npc.py 重写完成")
print("现在文件行数：%d" % len(content.split("\n")))