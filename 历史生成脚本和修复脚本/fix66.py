# 1. social.py 传年龄给 LLM
# 2. npc_chat.md 加年龄约束
# 3. 顺便：小孩的 goals 也特殊处理
from pathlib import Path

# ============================================================
# 1. social.py 加年龄参数
# ============================================================
p = Path("server/systems/social.py")
t = p.read_text(encoding="utf-8")

old = '''    prompt = load_prompt("npc_chat.md").format(
        name_a=a.name,
        goals_a="，".join(a.goals) or "（无）",
        name_b=b.name,
        goals_b="，".join(b.goals) or "（无）",
        relation=rel_desc,
        location=loc_zh,
    )'''

new = '''    prompt = load_prompt("npc_chat.md").format(
        name_a=a.name,
        age_a=a.age,
        goals_a="，".join(a.goals) or "（无）",
        name_b=b.name,
        age_b=b.age,
        goals_b="，".join(b.goals) or "（无）",
        relation=rel_desc,
        location=loc_zh,
    )'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] social.py 传 age")
else:
    print("[fail] social.py 锚点未找到")

# ============================================================
# 2. npc_chat.md 加年龄约束
# ============================================================
Path("server/prompts/npc_chat.md").write_text('''你是游戏里两个 NPC 对话的生成器。

**所有输出必须是简体中文，并输出为合法 JSON。**

结构：
{{"topic": "话题主题（4-8 字）", "lines": [{{"speaker": "名字", "text": "台词"}}, ...]}}

规则：
- lines 里 2 到 4 句对话，双方轮流说话
- 每句不超过 40 字
- 台词符合角色**年龄、性格与目标**
- speaker 必须使用真实名字（{name_a} 或 {name_b}）
- 不要输出 markdown，不要输出解释

**年龄约束（非常重要）**：
- **16 岁以下的孩子**：
  - 说话要短、直接、像小孩
  - 不能喝酒、不能谈生意、不能说"请你喝顿酒"这种成人社交
  - 不能独自处理大事（报仇、讨公道、借钱给大人）
  - 可以提父母、玩耍、怕的东西
- **60 岁以上的老人**：语速慢，常提往事和身体
- **成年人**：正常对话

场景：
  地点：{location}
  两人关系：{relation}

角色 A：{name_a}（{age_a} 岁）
  目标：{goals_a}

角色 B：{name_b}（{age_b} 岁）
  目标：{goals_b}
''', encoding="utf-8")
print("[write] npc_chat.md 加年龄约束")

# ============================================================
# 3. 小孩的 goals 替换成"童年版"
# ============================================================
# 检查 npc.py 里是否有针对小孩 goals 的处理
p2 = Path("server/generators/npc.py")
t2 = p2.read_text(encoding="utf-8")

if "CHILD_GOALS" not in t2:
    # 加 CHILD_GOALS 常量
    anchor = "FALLBACK_GOALS = ["
    addition = '''CHILD_GOALS = [
    ["想学写字", "让爹娘高兴"],
    ["养一只自己的小狗", "给它起个好听的名字"],
    ["把糖葫芦分给朋友", "成为村里最会爬树的孩子"],
    ["想偷偷看村外的世界", "快点长大"],
    ["想学打猎", "让父亲夸一次"],
    ["把风筝放得最高", "让所有人看见"],
    ["学会唱那首新歌", "唱给娘听"],
    ["想要一把小木剑", "和栓子比试"],
]

FALLBACK_GOALS = ['''
    if anchor in t2:
        t2 = t2.replace(anchor, addition, 1)
        print("[fix] npc.py 加 CHILD_GOALS")

    # 在 _default_npc 里根据年龄选 goals
    old_g = '''def _default_npc(npc_id: str, seed_name: str, gender: str = "unknown") -> NPC:
    rng = random.Random(hash(npc_id) & 0xFFFF)
    traits = {k: round(rng.uniform(0.25, 0.75), 2) for k in TRAIT_KEYS}
    needs = {k: round(rng.uniform(0.3, 0.7), 2) for k in NEED_KEYS}
    goals = rng.choice(FALLBACK_GOALS)'''
    new_g = '''def _default_npc(npc_id: str, seed_name: str, gender: str = "unknown") -> NPC:
    rng = random.Random(hash(npc_id) & 0xFFFF)
    traits = {k: round(rng.uniform(0.25, 0.75), 2) for k in TRAIT_KEYS}
    needs = {k: round(rng.uniform(0.3, 0.7), 2) for k in NEED_KEYS}
    age = rng.randint(18, 55)
    # 小孩用童年版目标
    if seed_name in ("小石头", "铁蛋", "栓子", "狗剩", "阿牛",
                     "丫丫", "招娣", "小翠", "阿香", "杏儿"):
        age = rng.randint(7, 15)
        goals = rng.choice(CHILD_GOALS)
    else:
        goals = rng.choice(FALLBACK_GOALS)'''
    if old_g in t2:
        t2 = t2.replace(old_g, new_g, 1)
        print("[fix] _default_npc 区分成人/儿童 goals")

    # 改 age 引用
    old_age = '''        age=rng.randint(18, 55),'''
    new_age = '''        age=age,'''
    if old_age in t2:
        t2 = t2.replace(old_age, new_age, 1)
        print("[fix] _default_npc age 使用新变量")

    # generate_npc 里 LLM 返回后也检查年龄
    old_check = '''    # 检测套话 goals（关键词匹配），强制替换'''
    new_check = '''    # 小孩强制童年版 goals
    if npc.age < 16:
        rng_kid = random.Random(uuid.uuid4().int)
        npc.goals = list(rng_kid.choice(CHILD_GOALS))

    # 检测套话 goals（关键词匹配），强制替换'''
    if old_check in t2:
        t2 = t2.replace(old_check, new_check, 1)
        print("[fix] generate_npc 小孩强制童年版 goals")

    p2.write_text(t2, encoding="utf-8")
else:
    print("[skip] npc.py 已有 CHILD_GOALS")

# ============================================================
# 4. seed_world.py：强制小孩年龄
# ============================================================
p3 = Path("tools/seed_world.py")
t3 = p3.read_text(encoding="utf-8")

if "rng.randint(7, 15)" not in t3.split("npc.age")[0]:
    old_seed = '''        # 儿童：从 CHILD_NAMES 取
        child_pool = list(CHILD_NAMES)
        rng.shuffle(child_pool)
        for i in range(min(n_children, len(child_pool))):
            cname = child_pool[i]
            cgender = "male" if i % 2 == 0 else "female"
            npc = await generate_npc(cname, context="村里的孩子", gender=cgender)
            # 强制年龄段
            npc.age = rng.randint(7, 15)
            save_npc(session, npc)
            npcs.append(npc)
            print("created child %s %s (age=%d)" % (npc.id, npc.name, npc.age))'''
    new_seed = '''        # 儿童：从 CHILD_NAMES 取
        child_pool = list(CHILD_NAMES)
        rng.shuffle(child_pool)
        for i in range(min(n_children, len(child_pool))):
            cname = child_pool[i]
            cgender = "male" if i % 2 == 0 else "female"
            npc = await generate_npc(cname, context="村里的孩子", gender=cgender)
            # 强制年龄段（生成后再覆盖一次）
            npc.age = rng.randint(7, 15)
            # 强制童年版 goals
            from server.generators.npc import CHILD_GOALS
            npc.goals = list(rng.choice(CHILD_GOALS))
            save_npc(session, npc)
            npcs.append(npc)
            print("created child %s %s (age=%d) goals=%r" % (
                npc.id, npc.name, npc.age, npc.goals))'''
    if old_seed in t3:
        t3 = t3.replace(old_seed, new_seed, 1)
        p3.write_text(t3, encoding="utf-8")
        print("[fix] seed_world 儿童强制 goals")
    else:
        print("[skip] seed_world 已改过或锚点未匹配")
else:
    print("[skip] seed_world 已改过")

print()
print("清库重 seed：")
print("  Remove-Item data\\world.db")
print("  python tools\\seed_world.py --npc 14")
print("  uvicorn server.main:app")