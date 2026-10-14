# 分性别 goals
from pathlib import Path

# ============================================================
# 1. 重写 npc.py：按性别选 goals
# ============================================================
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
    fallback = _default_npc(npc_id, seed_name, gender)

    prompt = load_prompt("npc_gen.md").format(
        name=seed_name, gender=gender_zh(gender), context=context,
    )
    npc = await get_llm().json(prompt, NPC, fallback=fallback)
    npc.id = npc_id
    npc.name = npc.name or seed_name
    if gender != "unknown":
        npc.gender = gender

    def _is_common(g: str) -> bool:
        return any(kw in g for kw in COMMON_KEYWORDS)

    # 校验：套话 or 性别不匹配 or 空 → 用 fallback 池
    need_replace = False
    reason = ""
    if not npc.goals:
        need_replace = True
        reason = "空 goals"
    elif all(_is_common(g) for g in npc.goals):
        need_replace = True
        reason = "套话"
    elif _goals_gender_mismatch(npc.goals, npc.gender, npc.age):
        need_replace = True
        reason = "性别/年龄不匹配"

    if need_replace:
        rng2 = random.Random(uuid.uuid4().int)
        npc.goals = _pick_goals(npc.gender, npc.age, rng2)
        print("[npc] %s（%s %d岁）的 goals %s，替换为 %r" % (
            npc.name, npc.gender, npc.age, reason, npc.goals))
    else:
        print("[npc] %s（%s %d岁）的 goals: %r" % (
            npc.name, npc.gender, npc.age, npc.goals))

    ok, _ = evaluate_npc(npc)
    if not ok:
        return fallback
    return npc
'''

p = Path("server/generators/npc.py")
p.write_text(content, encoding="utf-8")
print("[fix] npc.py 按性别分 goals")
print("行数：%d" % len(content.split(chr(10))))

# ============================================================
# 2. npc_gen.md：强调性别与目标匹配
# ============================================================
p2 = Path("server/prompts/npc_gen.md")
t2 = p2.read_text(encoding="utf-8")

if "性别匹配" not in t2:
    # 在 rules 末尾加约束
    old = "- 不要输出 markdown，不要输出解释"
    new = '''- **性别匹配（非常重要）**：
  - male（男）：可以有"娶妻""打猎""考功名""开铺子"等目标
  - female（女）：可以有"绣花""找夫婿""操持家务""织坊"等目标
  - **绝对不能**把"娶妻"给 female，把"绣花"给 male
- 不要输出 markdown，不要输出解释'''
    if old in t2:
        t2 = t2.replace(old, new, 1)
        p2.write_text(t2, encoding="utf-8")
        print("[fix] npc_gen.md 加性别匹配约束")

# ============================================================
# 3. seed_world.py：小孩强制童年版
# ============================================================
p3 = Path("tools/seed_world.py")
t3 = p3.read_text(encoding="utf-8")

if "from server.generators.npc import CHILD_GOALS" not in t3:
    # 儿童部分已存在，只要保证引用 CHILD_GOALS
    old_seed = '''            from server.generators.npc import CHILD_GOALS
            npc.goals = list(rng.choice(CHILD_GOALS))'''
    if old_seed not in t3:
        # 找强制年龄那段，加 goals 覆盖
        old = '''            npc.age = rng.randint(7, 15)'''
        new = '''            npc.age = rng.randint(7, 15)
            # 强制童年版 goals
            try:
                from server.generators.npc import CHILD_GOALS
                npc.goals = list(rng.choice(CHILD_GOALS))
            except Exception:
                pass'''
        if old in t3:
            t3 = t3.replace(old, new, 1)
            p3.write_text(t3, encoding="utf-8")
            print("[fix] seed_world 儿童强制 CHILD_GOALS")
        else:
            print("[skip] seed_world 锚点未找到")
    else:
        print("[skip] seed_world 已有 CHILD_GOALS 引用")

print()
print("清库重 seed：")
print("  Remove-Item data\\world.db")
print("  python tools\\seed_world.py --npc 14")
print("  uvicorn server.main:app")