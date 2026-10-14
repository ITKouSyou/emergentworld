# Part 60A：事件角色具体化
from pathlib import Path

# ============================================================
# 1. event_flow.py：加角色选择器
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

if "def _pick_roles" not in t:
    anchor = "def _participants_valid("
    addition = '''# 每个模板需要的具体角色
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


def _participants_valid('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] event_flow 加 _pick_roles")
    else:
        print("[fail] event_flow 锚点未找到")
else:
    print("[skip] event_flow 已有 _pick_roles")

# ============================================================
# 2. 在 run_event_cycle 里调用 _pick_roles
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

old = '''    # 参与者合理性校验
    global _last_rejected_template_id
    npcs_by_id = {n.id: n for n in npcs}
    if not _participants_valid(tpl, event.participants, npcs_by_id):
        print("[event] 参与者不满足 %s 的前置条件，跳过：%s" % (
            tpl.id, event.participants))
        _last_rejected_template_id = tpl.id
        # 不写数据库
        return None'''

new = '''    # 参与者合理性校验
    global _last_rejected_template_id
    npcs_by_id = {n.id: n for n in npcs}
    if not _participants_valid(tpl, event.participants, npcs_by_id):
        print("[event] 参与者不满足 %s 的前置条件，跳过：%s" % (
            tpl.id, event.participants))
        _last_rejected_template_id = tpl.id
        return None

    # 具体角色选择
    roles = _pick_roles(tpl, event.participants, npcs_by_id, rng)
    if roles:
        event.payload["roles"] = roles
        role_desc = ", ".join("%s=%s" % (k, npcs_by_id[v].name)
                              for k, v in roles.items() if v in npcs_by_id)
        print("[event] %s 具体角色：%s" % (tpl.id, role_desc))'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] event_flow 调用 _pick_roles")
else:
    print("[skip] event_flow 已改过或锚点未匹配")

print()
print("A 完成。下一步 fix60b.py（事件 prompt + 任务 target）")