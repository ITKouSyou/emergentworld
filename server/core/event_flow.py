"""事件流程：包含相关性判定 + 属性判定 + 玩家参与。

流程：
    1. Director 选模板
    2. Generator 生成事件
    3. 相关性判定：
        相关 → awaiting_player，等玩家抉择
        不相关 → 立即 resolved，作为"消息"
    4. 玩家选择后：
        属性判定 → 结果 quality
        LLM 根据 quality 生成结算文本
        应用奖励、经验、关系变化
"""

from __future__ import annotations

import random
import uuid
from typing import Optional

from sqlmodel import Session, select

from server.core import director
from server.core.choices import build_choices, get_choice_spec
from server.core.evaluator import evaluate_event, evaluate_reward, log_evaluation
from server.core.evaluator import EvalPipeline, EventLogicEvaluator
from server.core.world import load_npcs, save_event, save_world
from server.generators.base import get_llm, load_prompt
from server.generators.event import fill_event
from server.generators.reward import compute_budget, generate_reward
from server.models.db import EventRow, ItemRow, RewardRow, dumps
from server.models.schemas import Event, EventTemplate, Reward, World
from server.systems import player as player_sys
from server.systems import relationship
from server.systems.relevance import check_relevance

PLAYER_TIMEOUT_TICKS = 8

# 最近一次因参与者不合适被拒的模板 id
_last_rejected_template_id: str = ""


def get_last_rejected_template_id() -> str:
    return _last_rejected_template_id



# 模板 → 参与者需满足的条件
#   has_children  至少一人有子女
#   has_spouse    至少一人有配偶
#   no_spouse     至少一人未婚
#   has_family    至少一人有家人
TEMPLATE_REQUIRES = {
    "lost_child": "has_spouse",
    "romance_blooms": "no_spouse",
    "lovers_quarrel": "has_spouse",
    "wedding": "no_spouse",
    "broken_promise": "has_family",
    "funeral": "has_family",
    "birth_of_child": "has_spouse",
}

MAX_PENDING = 3


def _save_reward(session: Session, reward: Reward) -> None:
    row = RewardRow(
        id=reward.id,
        event_id=reward.event_id,
        kind=reward.kind,
        value=reward.value,
        description=reward.description,
        payload_json=dumps({k: v for k, v in reward.payload.items() if k != "item"}),
    )
    session.add(row)
    session.commit()


def _save_item(
    session: Session,
    reward_id: str,
    event_id: str,
    item_data: dict,
    owner_id: str,
) -> None:
    row = ItemRow(
        id=item_data["id"],
        reward_id=reward_id,
        event_id=event_id,
        name=item_data.get("name", ""),
        kind=item_data.get("kind", ""),
        affixes_json=dumps(item_data.get("affixes", [])),
        story=item_data.get("story", ""),
        value=float(item_data.get("value", 0.0)),
        owner_id=owner_id,
        consumed=False,
    )
    session.add(row)
    session.commit()


def _apply_initial_effects(
    session: Session,
    world: World,
    event: Event,
    tpl: EventTemplate,
    rng: random.Random,
) -> None:
    summary = event.payload.get("summary", "") or ("发生了 %s" % tpl.id)
    relationship.npc_effects_from_event(
        session=session,
        participants=event.participants,
        event_id=event.id,
        summary=summary,
        timestamp=world.tick,
        rng=rng,
    )
    relationship.apply_event_effects(
        session=session,
        participants=event.participants,
        tags=tpl.tags,
        rng=rng,
    )


def impossible_templates(templates, npcs) -> set:
    """扫一遍所有 NPC，找出当前环境下不可能满足条件的模板 id。"""
    has_children = any(n.family.children for n in npcs)
    has_spouse = any(n.family.spouse for n in npcs)
    no_spouse = any(not n.family.spouse and n.age >= 18 for n in npcs)
    has_family = any(
        n.family.spouse or n.family.children or n.family.parents
        for n in npcs
    )

    result: set = set()
    for tpl in templates:
        req = TEMPLATE_REQUIRES.get(tpl.id)
        if req == "has_children" and not has_children:
            result.add(tpl.id)
        elif req == "has_spouse" and not has_spouse:
            result.add(tpl.id)
        elif req == "no_spouse" and not no_spouse:
            result.add(tpl.id)
        elif req == "has_family" and not has_family:
            result.add(tpl.id)
    return result


# 每个模板需要的具体角色
# 值：(角色名, 从谁的什么关系里选)
#   self  = 参与者本人
#   child = 参与者的子女
#   spouse = 参与者的配偶
#   single_male / single_female = 参与者中未婚的男女
TEMPLATE_ROLES = {
    "lost_child": {
        "mother_or_father": ("self", "any"),
        "child": ("child", "any"),
    },
    "funeral": {
        "deceased": ("self", "any"),
    },
    "wedding": {
        "bride": ("self", "female_single"),
        "groom": ("self", "male_single"),
    },
    "romance_blooms": {
        "lover_a": ("self", "any"),
        "lover_b": ("self", "any"),
    },
    "lovers_quarrel": {
        "lover_a": ("self", "any"),
        "lover_b": ("self", "any"),
    },
    "birth_of_child": {
        "parent": ("self", "has_spouse"),
    },
}


def _pick_participant_ids(tpl, npcs, rng) -> list:
    """抽参与者 id 列表。与 fill_event 内部逻辑保持一致。"""
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _pick_roles(
    tpl,
    participants_ids: list[str],
    npcs_by_id: dict,
    rng,
) -> dict:
    """为模板挑选具体角色。返回 {role_name: npc_id}。"""
    rules = TEMPLATE_ROLES.get(tpl.id)
    if not rules:
        return {}

    chosen = [npcs_by_id[pid] for pid in participants_ids if pid in npcs_by_id]
    if not chosen:
        return {}

    roles: dict = {}
    used: set = set()

    # 先处理 child 类型（从参与者的子女里选）
    child_role_names = [k for k, v in rules.items() if v[0] == "child"]
    if child_role_names:
        all_children: list = []
        for p_npc in chosen:
            for cid in p_npc.family.children:
                if cid in npcs_by_id and cid not in used:
                    all_children.append(npcs_by_id[cid])
        if all_children:
            child = rng.choice(all_children)
            for rn in child_role_names:
                roles[rn] = child.id
                used.add(child.id)

    # 处理 self 类型
    for role_name, (kind, filt) in rules.items():
        if role_name in roles:
            continue
        pool = [n for n in chosen if n.id not in used]
        if not pool:
            continue

        # 过滤
        if filt == "female_single":
            pool = [n for n in pool if n.gender == "female" and not n.family.spouse]
        elif filt == "male_single":
            pool = [n for n in pool if n.gender == "male" and not n.family.spouse]
        elif filt == "has_spouse":
            pool = [n for n in pool if n.family.spouse]

        if not pool:
            continue

        pick = rng.choice(pool)
        roles[role_name] = pick.id
        used.add(pick.id)

    return roles


def _participants_valid(tpl, participants_ids: list[str], npcs_by_id: dict) -> bool:
    """检查事件参与者是否满足模板的前置条件。"""
    req = TEMPLATE_REQUIRES.get(tpl.id)
    if not req:
        return True

    chosen = [npcs_by_id[pid] for pid in participants_ids if pid in npcs_by_id]
    if not chosen:
        return False

    if req == "has_children":
        return any(n.family.children for n in chosen)
    if req == "has_spouse":
        return any(n.family.spouse for n in chosen)
    if req == "no_spouse":
        return any(not n.family.spouse and n.age >= 18 for n in chosen)
    if req == "has_family":
        return any(
            n.family.spouse or n.family.children or n.family.parents
            for n in chosen
        )
    return True


def _pending_rows(session: Session) -> list[EventRow]:
    return list(session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all())


def _resolve_item_owner(event: Event, choice_id: str, rng: random.Random) -> str:
    if choice_id == "oppose":
        return "player"
    if choice_id == "help":
        if event.participants:
            return event.participants[0]
        return ""
    if event.participants and rng.random() < 0.8:
        return rng.choice(event.participants)
    return "player"


async def _emit_reward_and_item(
    session: Session,
    world: World,
    event: Event,
    rng: random.Random,
    value_multiplier: float = 1.0,
    owner_hint: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    budget = compute_budget(event, world) * value_multiplier
    reward = await generate_reward(event, world)
    reward.value = min(reward.value * value_multiplier, 1.0)

    reward_ok, reward_errors = evaluate_reward(reward, budget)
    log_evaluation(session, "reward", reward.id, reward_ok, reward_errors)
    if not reward_ok:
        return None, None, None

    _save_reward(session, reward)
    reward_id = reward.id
    item_id = None
    item_owner = None

    item_data = reward.payload.get("item")
    if isinstance(item_data, dict) and item_data.get("id"):
        if owner_hint is None:
            item_owner = _resolve_item_owner(event, "observe", rng)
        else:
            item_owner = owner_hint
        _save_item(session, reward.id, event.id, item_data, item_owner)
        item_id = item_data["id"]

    return reward_id, item_id, item_owner


async def run_event_cycle(
    session: Session,
    world: World,
    templates: list[EventTemplate],
    force: bool = False,
    attempt: int = 0,
) -> Optional[Event]:
    rng = random.Random(world.seed * 1000003 + world.tick + attempt * 7919)

    pending = _pending_rows(session)
    if len(pending) >= MAX_PENDING:
        return None

    if not force and not director.should_trigger(world, rng):
        # 打印为什么没触发，方便排查
        print(f"[director] tick={world.tick} 未触发事件 (tension={world.director.tension:.2f}, last_tick={world.director.last_event_tick})")
        return None

    npcs = load_npcs(session)
    if len(npcs) < 1:
        return None

    player = player_sys.load_player(session)
    pending_template_ids = {r.template_id for r in pending}

    tpl = director.pick_template(
        templates, world, npcs, rng,
        ignore_cooldown=force,
        pending_template_ids=pending_template_ids,
    )
    if tpl is None:
        if pending_template_ids:
            tpl = director.pick_template(
                templates, world, npcs, rng,
                ignore_cooldown=False,
                pending_template_ids=pending_template_ids,
                want_interactive=False,
            )
        if tpl is None:
            return None

    # 先抽一次参与者（用于选角色）—— 用同一个 rng 保持一致
    _tmp_participants = _pick_participant_ids(tpl, npcs, rng)
    _tmp_by_id = {n.id: n for n in npcs}
    pre_roles = _pick_roles(tpl, _tmp_participants, _tmp_by_id, rng)

    # ==========================================
    # 包装：带重试和兜底的 fill_event
    # ==========================================
    async def _gen_event_with_retry(ctx: dict, feedback: list) -> Event:
        try:
            return await fill_event(
                tpl, world, npcs, rng,
                player=player,
                event_roles=pre_roles,
            )
        except Exception as e:
            print(f"[event_flow] fill_event 抛出异常: {e}")
            raise e

    def _fallback_event(ctx: dict) -> Event:
        from server.i18n import template_label
        loc_id = "village_square"
        if player is not None:
            loc_id = player.location_id

        is_interactive = bool(tpl.interactive)
        tpl_name = template_label(tpl.id)
        
        fallback_payload = {
            "summary": f"关于【{tpl_name}】的普通事件。",
            "narrative": __import__("random").choice([
                "这件事情在村里引起了小小的波澜，但并没有引起太大的注意。",
                "风波悄然兴起，人们交头接耳，似乎在暗中酝酿着什么。",
                "看似平静的表象下，似乎隐藏着不为人知的秘密。",
                "现场留下了一些蛛丝马迹，但线索如同乱麻般难以理清。"
            ]),
            "as_message": not is_interactive,
        }
        
        if is_interactive:
            fallback_payload["choices"] = [
                {"id": "help", "label": "伸出援手", "attribute": "charisma", "attribute_label": "魅力"},
                {"id": "observe", "label": "静观其变", "attribute": "perception", "attribute_label": "感知"}
            ]

        return Event(

            id=f"evt_fallback_{uuid.uuid4().hex[:8]}",
            template_id=tpl.id,
            participants=[n.id for n in rng.sample(npcs, min(2, len(npcs)))],
            location_id=loc_id,
            state="awaiting_player" if is_interactive else "active",
            payload=fallback_payload,
            created_at=world.tick,
            resolved_at=None
        )

    from server.core.evaluator import EvalPipeline, EventLogicEvaluator

    # 组装 Pipeline
    pipeline = EvalPipeline(
        evaluators=[EventLogicEvaluator()],
        max_retry=2,
        pass_score=0.65
    )
    
    context = {"tpl_id": tpl.id, "world_tick": world.tick}
    
    # 运行 Pipeline，获取 event
    event, eval_results = await pipeline.run_async(
        generate_fn=_gen_event_with_retry,
        context=context,
        fallback_fn=_fallback_event
    )

    # 记录评估结果
    if not all(r.passed for r in eval_results):
        print(f"[event-eval] {tpl.id} 触发兜底。原因: {[r.reasons for r in eval_results if r.reasons]}")

    # ==========================================
    # 后续流程恢复原样
    # ==========================================
    event.payload["interactive"] = bool(tpl.interactive)

    npc_ids = {n.id for n in npcs}
    max_reward = float(tpl.evaluator.get("max_reward", 1.0)) if tpl.evaluator else 1.0
    ok, errors = evaluate_event(event, world, npc_ids, budget=max_reward)
    log_evaluation(session, "event", event.id, ok, errors)

    if not ok:
        event.state = "rejected"
        save_event(session, event)
        director.update_tension_after_event(world, event, tpl)
        save_world(session, world)
        return None

    # 参与者合理性校验
    global _last_rejected_template_id
    npcs_by_id = {n.id: n for n in npcs}
    if not _participants_valid(tpl, event.participants, npcs_by_id):
        print("[event] 参与者不满足 %s 的前置条件，跳过：%s" % (
            tpl.id, event.participants))
        _last_rejected_template_id = tpl.id
        return None

    # 角色已在生成前选好，直接写入
    if pre_roles:
        event.payload["roles"] = pre_roles
        role_desc = ", ".join("%s=%s" % (k, _tmp_by_id[v].name)
                              for k, v in pre_roles.items() if v in _tmp_by_id)
        print("[event] %s 具体角色：%s" % (tpl.id, role_desc))

        # 相关性判定
    relevance_ok = False
    relevance_score = 0.0
    relevance_detail: dict = {}
    if tpl.interactive and player is not None:
        relevance_ok, relevance_score, relevance_detail = check_relevance(
            session, event, tpl, world, player, npcs,
        )
        # 【新增】：如果这是一个交互模板，但相关性不足，有 30% 概率强制卷入玩家
        # 这能保证玩家在跑图时，偶尔会遇到“管闲事”的机会
        import random as _r
        if not relevance_ok and _r.random() < 1.0:
            relevance_ok = True
            relevance_score = 0.5
            relevance_detail["forced_involvement"] = True

    event.payload["relevance_score"] = round(relevance_score, 3)
    event.payload["relevance_detail"] = relevance_detail

    # ============================================================
    # 分支 A：非交互 或 与玩家无关 → 消息，直接结算
    # ============================================================
    if (not tpl.interactive) or (not relevance_ok):
        event.state = "active"
        save_event(session, event)

        _apply_initial_effects(session, world, event, tpl, rng)

        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng, value_multiplier=1.0,
        )
        event.payload["reward_id"] = reward_id
        event.payload["item_id"] = item_id
        event.payload["item_owner"] = item_owner
        event.payload["as_message"] = True

        event.state = "resolved"
        event.resolved_at = world.tick
        save_event(session, event)

        director.update_tension_after_event(world, event, tpl)
        save_world(session, world)
        return event

    # ============================================================
    # 分支 B：与玩家相关 → 等待玩家抉择
    # ============================================================
    event.payload["choices"] = build_choices(tpl)
    event.payload["choice_made"] = None
    event.payload["tpl_tags"] = list(tpl.tags)
    event.payload["max_reward"] = max_reward
    event.payload["difficulty"] = 0.5
    event.payload["as_message"] = False

    event.state = "awaiting_player"
    save_event(session, event)

    _apply_initial_effects(session, world, event, tpl, rng)

    # 认识参与者
    if player is not None:
        for pid in event.participants:
            player_sys.learn_about_npc(session, pid)

    save_world(session, world)
    return event


async def _generate_outcome_text(
    event: Event,
    choice_id: str,
    choice_label: str,
    player,
    check: dict,
    attribute_label: str,
) -> str:
    prompt = load_prompt("event_resolve.md").format(
        summary=event.payload.get("summary", ""),
        narrative=event.payload.get("narrative", ""),
        player_name=player.name if player else "无名者",
        choice_id=choice_id,
        choice_label=choice_label,
        attribute_label=attribute_label,
        attribute_value=check["base"],
        roll=check["roll"],
        total=check["total"],
        threshold=check["threshold"],
        result=check["result"],
    )
    try:
        raw = await get_llm().text_json(prompt)
        if isinstance(raw, dict):
            outcome = str(raw.get("outcome", "")).strip()
            epilogue = str(raw.get("epilogue", "")).strip()
            if outcome:
                return (outcome + " " + epilogue).strip() if epilogue else outcome
    except Exception:
        pass
    # fallback
    result_zh = {
        "critical": "你出色地处理了此事。",
        "success": "你顺利处理了此事。",
        "partial": "此事勉强有了着落。",
        "failure": "你没能处理好此事。",
    }.get(check["result"], "")
    
    # 不要直接拿 summary，用模板的 label，避免暴露英文 ID
    from server.i18n import template_label
    tpl_name = template_label(event.template_id)
    
    return "关于【%s】，你选择了%s。%s" % (
        tpl_name,
        choice_label,
        result_zh,
    )


async def resolve_event(
    session: Session,
    world: World,
    event_id: str,
    choice_id: str,
) -> dict:
    row = session.get(EventRow, event_id)
    if row is None:
        return {"ok": False, "error": "event not found"}
    if row.state != "awaiting_player":
        return {"ok": False, "error": "event not awaiting player (state=%s)" % row.state}

    spec = get_choice_spec(choice_id)
    if spec is None:
        return {"ok": False, "error": "unknown choice: %s" % choice_id}

    from server.models.db import loads as _loads

    payload = _loads(row.payload_json) or {}
    event = Event(
        id=row.id,
        template_id=row.template_id,
        participants=_loads(row.participants_json) or [],
        location_id=row.location_id,
        state="awaiting_player",  # type: ignore[arg-type]
        payload=payload,
        created_at=row.created_at,
        resolved_at=None,
    )

    rng = random.Random(world.seed * 100003 + world.tick)

    # 找 choice 的实际属性（可能被 tag 覆盖）
    choice_attribute = spec["attribute"]
    for c in payload.get("choices", []):
        if isinstance(c, dict) and c.get("id") == choice_id:
            choice_attribute = str(c.get("attribute", choice_attribute))
            break

    player = player_sys.load_player(session)
    if player is None:
        return {"ok": False, "error": "player not created"}

    # 属性判定
    check = player_sys.roll_check(player, choice_attribute, spec["difficulty"], rng)

    # 判定结果影响 relation delta 与 reward multiplier 的修正
    quality_mult = {
        "critical": 1.5,
        "success": 1.0,
        "partial": 0.6,
        "failure": -0.5,
    }.get(check["result"], 1.0)

    # 显示用的中文标签
    from server.core.choices import _attr_label
    attribute_label = _attr_label(choice_attribute)

    # 生成结算文本
    choice_label = spec["label"]
    for c in payload.get("choices", []):
        if isinstance(c, dict) and c.get("id") == choice_id:
            choice_label = str(c.get("label", choice_label))
            break

    outcome_text = await _generate_outcome_text(
        event, choice_id, choice_label, player, check, attribute_label,
    )

    # 关系变化
    for npc_id in event.participants:
        delta = spec["relation_delta"]
        mult = 1.0 if quality_mult > 0 else 0.5
        relationship.adjust(
            session,
            from_npc=npc_id,
            to_npc="player",
            trust=float(delta.get("trust", 0.0)) * mult,
            affection=float(delta.get("affection", 0.0)) * mult,
            fear=float(delta.get("fear", 0.0)) * mult,
            debt=float(delta.get("debt", 0.0)) * mult,
        )

    # 张力
    world.director.tension = max(
        0.0,
        min(1.0, world.director.tension + float(spec["tension_delta"])),
    )

    # 奖励（除 observe 外，即使失败也可能有部分收获）
    reward_id = None
    item_id = None
    item_owner = None
    if choice_id != "observe":
        value_mult = float(spec["reward_multiplier"]) * max(0.2, quality_mult)
        owner_hint = _resolve_item_owner(event, choice_id, rng)
        reward_id, item_id, item_owner = await _emit_reward_and_item(
            session, world, event, rng,
            value_multiplier=value_mult,
            owner_hint=owner_hint,
        )

    # 经验与声望
    exp_gain = int(spec["exp_reward"] * max(0.2, quality_mult))
    if exp_gain > 0:
        player_after, leveled = player_sys.add_exp(session, exp_gain)
    else:
        player_after, leveled = player, False

    rep_gain = 0
    if check["result"] in ("critical", "success"):
        rep_gain = 3 if check["result"] == "success" else 6
        player_sys.add_reputation(session, rep_gain)
    elif check["result"] == "failure":
        player_sys.add_reputation(session, -1)

    # 派系声望
    try:
        from server.systems import faction as faction_sys
        faction_sys.apply_event_choice(
            session, event.template_id, choice_id, event.participants,
        )
    except Exception as e:
        import traceback
        print("[event] 派系声望写入失败：%s" % e)
        traceback.print_exc()

    # 写印象
    try:
        from server.systems import impression as impr_sys
        roles = payload.get("roles", {})
        for npc_id in event.participants:
            tags = impr_sys.tags_from_event(
                event.template_id, choice_id, roles, npc_id,
            )
            for tag in tags:
                impr_sys.add_impression(session, npc_id, tag, 1)
    except Exception as e:
        import traceback
        print("[event] 印象写入失败：%s" % e)
        traceback.print_exc()

    # 更新事件
    payload["choice_made"] = choice_id
    payload["choice_label"] = choice_label
    payload["outcome"] = outcome_text
    payload["reward_id"] = reward_id
    payload["item_id"] = item_id
    payload["item_owner"] = item_owner
    payload["check"] = check
    payload["exp_gain"] = exp_gain
    payload["rep_gain"] = rep_gain

    row.state = "resolved"
    row.resolved_at = world.tick
    row.payload_json = dumps(payload)
    session.add(row)
    session.commit()

    save_world(session, world)

    return {
        "ok": True,
        "event_id": event_id,
        "choice_id": choice_id,
        "choice_label": choice_label,
        "outcome": outcome_text,
        "check": check,
        "exp_gain": exp_gain,
        "rep_gain": rep_gain,
        "leveled_up": leveled,
        "new_level": player_after.level,
        "reward_id": reward_id,
        "item_id": item_id,
        "item_owner": item_owner,
    }


async def check_timeouts(session: Session, world: World) -> int:
    from server.models.db import loads as _loads

    rows = session.exec(
        select(EventRow).where(EventRow.state == "awaiting_player")
    ).all()

    count = 0
    for row in rows:
        if world.tick - row.created_at < PLAYER_TIMEOUT_TICKS:
            continue
        try:
            payload = _loads(row.payload_json) or {}
            payload["choice_made"] = "observe"
            payload["choice_label"] = "静观其变（超时）"
            payload["outcome"] = "%s——你没有介入，事件自行落幕。" % (
                payload.get("summary", "事件")
            )
            payload["timeout"] = True
            row.state = "expired"
            row.resolved_at = world.tick
            row.payload_json = dumps(payload)
            session.add(row)
            count += 1
        except Exception:
            continue

    if count:
        session.commit()
    return count
