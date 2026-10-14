# NPC 对玩家的印象
from __future__ import annotations

from sqlmodel import Session

from server.models.db import NPCRow, dumps, loads

# 印象标签 → 中文描述
TAG_LABELS = {
    "helped_me": "帮过我",
    "saved_my_child": "救过我的孩子",
    "shared_trade": "和我做过生意",
    "gave_gift": "送过我东西",
    "betrayed_me": "坑过我",
    "refused_help": "拒绝过帮忙",
    "showed_courage": "在我面前勇敢过",
    "spread_rumor": "说过我坏话",
}

# 每种行动 → 对应的印象 tag
# 值可以是 str（固定）或 lambda（根据 choice 决定）
def tags_from_event(
    template_id: str,
    choice_id: str,
    roles: dict,
    npc_id: str,
) -> list[str]:
    """根据事件 + 选择 + 角色，推断这个 NPC 对玩家产生的印象。"""
    tags: list[str] = []

    if choice_id == "help":
        tags.append("helped_me")
    elif choice_id == "oppose":
        tags.append("betrayed_me")
    elif choice_id == "observe":
        # 静观其变不留下强烈印象
        return []

    # 特殊事件加成
    if template_id == "lost_child" and roles.get("child") == npc_id:
        if choice_id == "help":
            tags.append("saved_my_child")

    if template_id in ("bandit_raid", "wolves_at_night", "combat"):
        if choice_id == "help":
            tags.append("showed_courage")

    return tags


def add_impression(session: Session, npc_id: str, tag: str, count: int = 1) -> None:
    """给 NPC 加一条印象计数。"""
    row = session.get(NPCRow, npc_id)
    if row is None:
        return
    impr = loads(row.impressions_json) or {}
    impr[tag] = int(impr.get(tag, 0)) + count
    row.impressions_json = dumps(impr)
    session.add(row)
    session.commit()


def get_impressions(session: Session, npc_id: str) -> dict:
    row = session.get(NPCRow, npc_id)
    if row is None:
        return {}
    return loads(row.impressions_json) or {}


def describe_for_prompt(session: Session, npc_id: str, limit: int = 4) -> str:
    """把印象翻译成 LLM 易读的一句话。"""
    impr = get_impressions(session, npc_id)
    if not impr:
        return "（你对他还没有特别的印象）"

    # 按次数排序
    items = sorted(impr.items(), key=lambda kv: -kv[1])
    parts = []
    for tag, count in items[:limit]:
        label = TAG_LABELS.get(tag, tag)
        if count > 1:
            parts.append("%s（%d 次）" % (label, count))
        else:
            parts.append(label)
    return "，".join(parts)


def describe_for_ui(session: Session, npc_id: str) -> list[str]:
    """给前端显示用。"""
    impr = get_impressions(session, npc_id)
    if not impr:
        return []
    items = sorted(impr.items(), key=lambda kv: -kv[1])
    result = []
    for tag, count in items[:6]:
        label = TAG_LABELS.get(tag, tag)
        if count > 1:
            result.append("%s（%d 次）" % (label, count))
        else:
            result.append(label)
    return result


def decay_impressions(session: Session, npc_id: str, decay_ratio: float = 0.05) -> None:
    """长期未联系时印象会淡化。"""
    row = session.get(NPCRow, npc_id)
    if row is None:
        return
    impr = loads(row.impressions_json) or {}
    if not impr:
        return
    for k in list(impr.keys()):
        impr[k] = max(0, int(impr[k]) - int(impr[k] * decay_ratio + 0.5))
        if impr[k] <= 0:
            del impr[k]
    row.impressions_json = dumps(impr)
    session.add(row)
    session.commit()
