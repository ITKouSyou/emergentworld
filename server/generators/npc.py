# NPC 生成器：LLM + 规则兜底
from __future__ import annotations

import random
import uuid

from server.core.evaluator import EvalPipeline, NPCGoalEvaluator, evaluate_npc
from server.generators.base import get_llm, load_prompt
from server.models.schemas import NPC

TRAIT_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
NEED_KEYS = ["hunger", "safety", "social", "wealth", "curiosity"]

GENDER_ZH = {"male": "男", "female": "女", "unknown": "未知"}


# ---------- 儿童 goals（不分性别）----------
CHILD_GOALS = [
    ["想学写字", "让爹娘高兴"],
    ["养一只自己的小狗", "给它起个好听的名字"],
    ["把糖葫芦分给朋友", "成为村里最会爬树的孩子"],
    ["想偷偷看村外的世界", "快点长大"],
    ["想学打猎", "让父亲夸一次"],
    ["把风筝放得最高", "让所有人看见"],
    ["学会唱那首新歌", "唱给娘听"],
    ["想要一把小木剑", "和栓子比试"],
]


# ---------- 成年男性 goals ----------
MALE_GOALS = [
    ["攒钱翻修老屋", "娶妻成家"],
    ["娶一位贤惠的媳妇", "在村里有一席之地"],
    ["找出当年害我的人", "不再被人轻视"],
    ["守住祖上的手艺", "收一个徒弟"],
    ["攒够盘缠去远方", "看一眼外面的世界"],
    ["让病重的亲人痊愈", "还清欠下的债"],
    ["赢得村人的尊重", "不再被人指指点点"],
    ["读到更多的书", "考一个功名"],
    ["变得更强壮", "保护想保护的人"],
    ["查明兄长的死因", "为他讨回公道"],
    ["学会酿酒", "开一间自己的酒铺"],
    ["找到失散多年的兄弟", "一起回乡"],
    ["成为村里最会打猎的人", "让父亲刮目相看"],
    ["攒钱赎回被典当的祖传玉佩", "重振家门"],
    ["在村口开一间铁匠铺", "打出全村最好的刀"],
    ["考中秀才", "光宗耀祖"],
    ["上山打一只虎", "证明自己不是懦夫"],
    ["跟随商队远行一次", "带回足够全家过冬的钱"],
]


# ---------- 成年女性 goals ----------
FEMALE_GOALS = [
    ["攒钱翻修老屋", "让家人过上好日子"],
    ["绣出全村最好看的帕子", "卖到镇上"],
    ["找到一位可靠的夫婿", "安稳过一生"],
    ["学会医术", "照看村里病人"],
    ["让儿子将来念书识字", "走出这个村子"],
    ["守住娘留下的绣样", "教给女儿"],
    ["开一间小织坊", "自己养活自己"],
    ["攒够钱给娘看病", "让她不再受苦"],
    ["酿出最香的桂花酒", "让全村都来尝"],
    ["照顾好年迈的公婆", "赢得他们的认可"],
    ["找到失散多年的妹妹", "带她回来团圆"],
    ["在村里办一场像样的婚礼", "风风光光"],
    ["把家里的地种好", "明年收成翻倍"],
    ["跟村里的老人学认药草", "派上用场"],
    ["去镇上赶一次大集", "看看外面的世界"],
    ["给小女儿攒一份嫁妆", "不让她受苦"],
]


# 按名字推断性别的兜底（防止 LLM 或调用方传错）
FEMALE_NAME_HINTS = [
    "秀", "兰", "桂", "梅", "娇", "翠", "玉", "盼",
    "蓉", "莲", "婵", "薇", "烟", "娥", "丫", "娣",
    "香", "杏", "桃", "妮", "侬", "素",
]
MALE_NAME_HINTS = [
    "铁", "柱", "山", "狗", "望", "河", "远", "慎",
    "越", "屠", "舟", "守", "风", "平", "墨",
    "石", "蛋", "栓", "剩", "牛", "娃", "棒", "虎",
]


def _guess_gender(name: str) -> str:
    """按名字特征推断性别。返回 "male" / "female" / "unknown"。"""
    if not name:
        return "unknown"
    # 优先检查女性特征
    for ch in name:
        if ch in FEMALE_NAME_HINTS:
            return "female"
    for ch in name:
        if ch in MALE_NAME_HINTS:
            return "male"
    return "unknown"


def gender_zh(gender: str) -> str:
    return GENDER_ZH.get(gender, "未知")


def _pick_goals(gender: str, age: int, rng: random.Random) -> list:
    """按性别和年龄选一组 goals。"""
    if age < 16:
        return list(rng.choice(CHILD_GOALS))
    if gender == "female":
        return list(rng.choice(FEMALE_GOALS))
    return list(rng.choice(MALE_GOALS))


def _default_npc(npc_id: str, seed_name: str, gender: str = "unknown") -> NPC:
    rng = random.Random(hash(npc_id) & 0xFFFF)
    traits = {k: round(rng.uniform(0.25, 0.75), 2) for k in TRAIT_KEYS}
    needs = {k: round(rng.uniform(0.3, 0.7), 2) for k in NEED_KEYS}
    age = rng.randint(18, 55)
    goals = _pick_goals(gender, age, rng)
    return NPC(
        id=npc_id,
        name=seed_name,
        age=age,
        gender=gender,
        traits=traits,
        needs=needs,
        goals=goals,
        behavior_profile={k: 0.5 for k in NEED_KEYS},
        asset_params={"hair": "short", "outfit": "plain", "palette": "neutral"},
    )


def _goals_gender_mismatch(goals: list, gender: str, age: int) -> bool:
    """检测 goals 是否与性别/年龄矛盾。"""
    if not goals:
        return True

    text = " ".join(goals)

    # 小孩不该有成人目标
    if age < 16:
        adult_kw = ["娶妻", "嫁人", "夫婿", "光宗耀祖", "考功名",
                    "收徒弟", "开酒铺", "开铺子", "赚钱养家", "保护家人"]
        if any(kw in text for kw in adult_kw):
            return True

    # 女性不该有男性专属目标
    if gender == "female":
        male_kw = ["娶妻", "娶一位", "娶媳妇", "打虎", "考秀才",
                   "考中", "光宗耀祖", "打一只虎"]
        if any(kw in text for kw in male_kw):
            return True

    # 男性不该有女性专属目标
    if gender == "male":
        female_kw = ["绣", "帕子", "嫁妆", "夫婿", "织坊",
                     "桂花酒", "小女儿", "公婆"]
        if any(kw in text for kw in female_kw):
            return True

    return False


# 套话关键词
COMMON_KEYWORDS = [
    "安稳度日", "照顾好家人", "过好日子", "平平安安",
    "安安稳稳", "平淡", "安稳", "好好生活", "平淡度日",
    "安静地生活", "平静地生活", "安稳生活",
]


async def generate_npc(seed_name: str, context: str = "", gender: str = "unknown") -> NPC:
    npc_id = "npc_%s" % uuid.uuid4().hex[:8]
    
    # 1. 先把原本的兜底 NPC 生成好，作为最终降级方案
    fallback_npc = _default_npc(npc_id, seed_name, gender)

    # 2. 构建评估器链 (复用你的业务逻辑)
    pipeline = EvalPipeline(
        evaluators=[NPCGoalEvaluator()], 
        max_retry=2, 
        pass_score=0.65
    )
    
    ctx = {"name": seed_name, "gender": gender, "context": context}

    # 3. 定义生成函数 (带有反馈拼接)
    async def _gen(ctx_data: dict, feedback: list) -> NPC:
        prompt = load_prompt("npc_gen.md").format(
            name=ctx_data["name"], gender=gender_zh(ctx_data["gender"]), context=ctx_data["context"],
        )
        if feedback:
            prompt += "\n\n【上一次生成存在以下问题，请务必改正】：\n"
            for hint in feedback:
                prompt += f"- {hint}\n"
                
        # 调真实的异步 LLM
        npc = await get_llm().json(prompt, NPC, fallback=fallback_npc)
        
        # 把你原本的推断逻辑搬到这里，确保 LLM 出来的数据先经过清洗
        npc.id = npc_id
        npc.name = npc.name or seed_name
        
        name_gender = _guess_gender(npc.name)
        if name_gender != "unknown":
            npc.gender = name_gender
        elif ctx_data["gender"] != "unknown":
            npc.gender = ctx_data["gender"]
            
        return npc

    # 4. 定义最终降级函数
    def _fallback(ctx_data: dict) -> NPC:
        print(f"[npc] {seed_name} 触发兜底")
        return fallback_npc

    # 5. 运行 Pipeline
    final_npc, history = await pipeline.run_async(_gen, ctx, _fallback)

    # 6. 最后的双层保险 (调用你原有的评估逻辑)
    ok, _ = evaluate_npc(final_npc)
    if not ok:
        return fallback_npc
        
    # 打印评估记录，方便你在终端看谁翻车了
    if history and not all(r.passed for r in history):
        print(f"[npc-eval] {final_npc.name} 经过重试后通过。失败记录: {[r.reasons for r in history if r.reasons]}")

    return final_npc