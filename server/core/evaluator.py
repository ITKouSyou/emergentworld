"""评估器：生成系统的核心。规则层 + LLM 抽样层 + 日志层。"""

from __future__ import annotations
import uuid
import re
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, List, Tuple, Awaitable
from sqlmodel import Session

from server.models.db import EvaluationRow, dumps
from server.models.schemas import Event, NPC, Reward, World

# ==========================================
# 原有代码保留，确保不破坏现有依赖
# ==========================================
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

# ==========================================
# 新增：评估器链与 Pipeline (支持异步)
# ==========================================
@dataclass
class EvalResult:
    name: str
    score: float
    reasons: List[str] = field(default_factory=list)
    fix_hint: str | None = None
    passed: bool = False

class BaseEvaluator:
    name: str = "base"
    weight: float = 1.0
    threshold: float = 0.6

    def evaluate(self, payload: dict, context: dict) -> EvalResult:
        raise NotImplementedError

class NPCGoalEvaluator(BaseEvaluator):
    """把你 npc.py 里的 _goals_gender_mismatch 和套话逻辑搬到这里"""
    def __init__(self):
        self.name = "NPCGoal"
        self.weight = 1.5
        self.threshold = 0.6
        # 这里可以引用你 npc.py 里的常量，或者传参进来
        
    def evaluate(self, payload: dict, context: dict) -> EvalResult:
        goals = payload.get("goals", [])
        if not goals:
            return EvalResult(self.name, 0.0, ["空 goals"], "生成的目标不能为空")
            
        text = " ".join(goals)
        gender = payload.get("gender", "unknown")
        age = payload.get("age", 20)
        
        # 套话过滤
        common_keywords = ["安稳度日", "照顾好家人", "过好日子", "平平淡淡"]
        if all(any(kw in g for kw in common_keywords) for g in goals):
            return EvalResult(self.name, 0.2, ["套话"], "请生成更有具体行为细节的目标，不要使用'安稳度日'这类空话。")
            
        # 性别年龄冲突 (简化版，你可以把原逻辑全搬过来)
        if age < 16 and any(kw in text for kw in ["娶妻", "嫁人", "光宗耀祖"]):
            return EvalResult(self.name, 0.3, ["年龄冲突"], "这是一个不到16岁的孩子，目标必须符合儿童认知。")
        if gender == "female" and any(kw in text for kw in ["娶妻", "考功名"]):
            return EvalResult(self.name, 0.3, ["性别冲突"], "目标与角色性别不符，请重新设计。")
            
        return EvalResult(self.name, 1.0, passed=True)


class EvalPipeline:
    def __init__(self, evaluators: List[BaseEvaluator], max_retry: int = 2, pass_score: float = 0.65):
        self.evaluators = evaluators
        self.max_retry = max_retry
        self.pass_score = pass_score

    async def run_async(self, generate_fn: Callable[[dict, List[str]], Awaitable[Any]], context: dict, fallback_fn: Callable[[dict], Any] = None) -> Tuple[Any, List[EvalResult]]:
        history = []
        last_payload = None
        last_results = []
        
        for attempt in range(self.max_retry + 1):
            try:
                # 注意：这里 await 的是你 npc.py 里包装的异步函数
                last_payload = await generate_fn(context, feedback=history)
            except Exception as e:
                history = [f"生成发生异常: {str(e)}"]
                continue
                
            # 将 Pydantic 对象转为 dict 供评估器检查（评估器不依赖具体类）
            payload_dict = last_payload.model_dump() if hasattr(last_payload, "model_dump") else last_payload
            
            results = []
            total_score = 0.0
            total_weight = 0.0
            
            for e in self.evaluators:
                r = e.evaluate(payload_dict, context)
                r.passed = r.score >= e.threshold
                results.append(r)
                total_score += r.score * e.weight
                total_weight += e.weight
                
            final_score = total_score / total_weight if total_weight > 0 else 0
            last_results = results
            
            if final_score >= self.pass_score:
                print(f"[eval] 第 {attempt+1} 次尝试通过。")
                return last_payload, results
                
            history = [r.fix_hint for r in results if not r.passed and r.fix_hint]
            
        if fallback_fn:
            return fallback_fn(context), last_results
        return last_payload, last_results


# 追加事件逻辑评估器，用来捕捉 LLM 生成的事件逻辑漏洞（比如“大夏天穿着棉袄乞讨”、“内向的人突然当众演讲”）
class EventLogicEvaluator(BaseEvaluator):
    """事件逻辑与世界观一致性校验"""
    def __init__(self):
        self.name = "EventLogic"
        self.weight = 1.5
        self.threshold = 0.6
        self.banned_phrases = ["作为AI", "无法生成", "抱歉", "系统提示", "作为一个"]

    def evaluate(self, payload: dict, context: dict) -> EvalResult:
        # 只校验 summary 和 narrative，因为 choices 是外部生成的
        summary = str(payload.get("summary", "")).strip()
        narrative = str(payload.get("narrative", "")).strip()

        # 1. 必须有实际内容，不能是空壳
        if not summary and not narrative:
            return EvalResult(self.name, 0.0, ["内容为空"], "你生成的 summary 和 narrative 都是空的！请提供描述。")
            
        text = summary + narrative
        
        # 2. 套话/出戏过滤
        hits = [p for p in self.banned_phrases if p in text]
        if hits:
            return EvalResult(self.name, 0.0, ["出戏"], f"不要在文本中使用：{'、'.join(hits)}。请用符合古代设定的语言重写。")
            
        # 3. 废除硬性长度限制，改为极短的软限制（比如少于 8 个字才打回）
        # 像“孩子在玩耍”这种短描述是完全合法且合理的
        if len(text) < 4:
            return EvalResult(self.name, 0.4, ["文本极短"], "描述实在太短了，请至少写一句完整的话。")
            
        # 4. 可用性校验（如果事件要求玩家选择，必须提供选项）
        if payload.get("awaiting_player") and not payload.get("choices"):
            return EvalResult(self.name, 0.2, ["缺少选项"], "这是一个需要玩家交互的事件，必须提供 choices 列表。")

        # 5. 极简的重复度过滤（防止 LLM 车轱辘话）
        if text.count(text[:10]) > 3:
            return EvalResult(self.name, 0.2, ["重复度极高"], "生成的内容重复度过高，请提供更丰富的情节。")

        # 6. 结合上下文校验（例如：参与者不能在事件里做违背其当前状态的事）
        # 这里可以继续扩充，比如：
        # season = context.get("season")
        # if season == "summer" and "大雪" in text: ...
        
        return EvalResult(self.name, 1.0, passed=True)

