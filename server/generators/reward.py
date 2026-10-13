"""奖励生成器：预算约束下的模板 + LLM 描述 + 物品。"""

from __future__ import annotations

import uuid

from server.generators.item import generate_item
from server.i18n import template_label
from server.models.schemas import Event, Reward, World


def compute_budget(event: Event, world: World, difficulty: float = 0.5) -> float:
    base = 0.3 + difficulty * 0.5
    return base * world.economy.reward_budget_multiplier


async def generate_reward(event: Event, world: World) -> Reward:
    budget = compute_budget(event, world)
    value = min(budget, 1.0)
    tpl_zh = template_label(event.template_id)

    # item 类型：生成真正的物品实体
    item = await generate_item(event, world, value)

    summary = str(event.payload.get("summary", "")).strip()
    if summary:
        description = "%s 的结局：%s" % (tpl_zh, summary[:40])
    else:
        description = "%s的奖励" % tpl_zh

    return Reward(
        id="rwd_%s" % uuid.uuid4().hex[:8],
        event_id=event.id,
        kind="item",
        value=value,
        description=description,
        payload={"item": item},
    )
