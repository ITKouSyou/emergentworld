"""评估器：生成系统的核心。规则层 + LLM 抽样层 + 日志层。"""

from __future__ import annotations

import uuid

from sqlmodel import Session

from server.models.db import EvaluationRow, dumps
from server.models.schemas import Event, NPC, Reward, World


def entities_exist(event: Event, world: World, npc_ids: set[str]) -> bool:
    return all(p in npc_ids for p in event.participants)


def reward_over_budget(reward: Reward, budget: float) -> bool:
    return reward.value > budget * 1.2


def contradicts_memory(event: Event, world: World) -> bool:
    return False


def evaluate_event(
    event: Event,
    world: World,
    npc_ids: set[str],
    budget: float = 1.0,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not entities_exist(event, world, npc_ids):
        errors.append("missing_entity")
    if not event.location_id:
        errors.append("missing_location")
    if event.created_at < 0:
        errors.append("invalid_time")
    if contradicts_memory(event, world):
        errors.append("contradiction")
    return (len(errors) == 0), errors


def log_evaluation(
    session: Session,
    target_type: str,
    target_id: str,
    passed: bool,
    errors: list[str],
    score: float | None = None,
    raw: dict | None = None,
) -> None:
    row = EvaluationRow(
        id=str(uuid.uuid4()),
        target_type=target_type,
        target_id=target_id,
        passed=passed,
        score=score,
        errors_json=dumps(errors),
        raw_json=dumps(raw or {}),
    )
    session.add(row)
    session.commit()


def evaluate_npc(npc: NPC) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not npc.name:
        errors.append("missing_name")
    if not (0 <= npc.age <= 200):
        errors.append("invalid_age")
    if not npc.goals:
        errors.append("missing_goals")
    return (len(errors) == 0), errors


def evaluate_reward(reward: Reward, budget: float) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if reward.value < 0:
        errors.append("negative_value")
    if reward_over_budget(reward, budget):
        errors.append("reward_over_budget")
    if not reward.description:
        errors.append("missing_description")
    return (len(errors) == 0), errors
