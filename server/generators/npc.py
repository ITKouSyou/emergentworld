"""NPC 生成器：LLM 生成属性 + 规则兜底。"""

from __future__ import annotations

import random
import uuid

from server.core.evaluator import evaluate_npc
from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC

TRAIT_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
NEED_KEYS = ["hunger", "safety", "social", "wealth", "curiosity"]

GENDER_ZH = {"male": "男", "female": "女", "unknown": "未知"}


def gender_zh(gender: str) -> str:
    return GENDER_ZH.get(gender, "未知")


def _default_npc(npc_id: str, seed_name: str, gender: str = "unknown") -> NPC:
    rng = random.Random(hash(npc_id) & 0xFFFF)
    traits = {k: round(rng.uniform(0.25, 0.75), 2) for k in TRAIT_KEYS}
    needs = {k: round(rng.uniform(0.3, 0.7), 2) for k in NEED_KEYS}
    return NPC(
        id=npc_id,
        name=seed_name,
        age=rng.randint(18, 55),
        gender=gender,
        traits=traits,
        needs=needs,
        goals=["安稳度日", "照顾好家人"],
        behavior_profile={k: 0.5 for k in NEED_KEYS},
        asset_params={"hair": "short", "outfit": "plain", "palette": "neutral"},
    )


async def generate_npc(
    seed_name: str,
    context: str = "",
    gender: str = "unknown",
) -> NPC:
    npc_id = "npc_%s" % uuid.uuid4().hex[:8]
    fallback = _default_npc(npc_id, seed_name, gender)

    prompt = load_prompt("npc_gen.md").format(
        name=seed_name,
        gender=gender_zh(gender),
        context=context,
    )
    npc = await get_llm().json(prompt, NPC, fallback=fallback)
    npc.id = npc_id
    npc.name = npc.name or seed_name
    if gender != "unknown":
        npc.gender = gender

    ok, _ = evaluate_npc(npc)
    if not ok:
        return fallback
    return npc
