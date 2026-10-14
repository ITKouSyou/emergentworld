# Part 60B：事件 prompt 用角色名字 + 任务用具体目标
from pathlib import Path

# ============================================================
# 1. generators/event.py：把角色信息传给 LLM
# ============================================================
p = Path("server/generators/event.py")
t = p.read_text(encoding="utf-8")

old = '''    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        template_label=template_label(tpl.id),
        prompt=tpl.prompt,
        participants=", ".join("%s(%s)" % (p.name, p.id) for p in participants) or "无",
        location=location,
        location_label=location_label(location),
        player_name=player_name,
        player_location=player_loc,
        day=world.day,
    )'''

new = '''    # 构建"具体角色"文本
    roles_text = "（无）"
    roles = event_roles or {}
    if roles:
        parts = []
        for role_name, npc_id in roles.items():
            p_npc = next((n for n in npcs if n.id == npc_id), None)
            if p_npc is not None:
                role_zh = {
                    "mother_or_father": "家长",
                    "child": "走失的孩子",
                    "deceased": "逝者",
                    "bride": "新娘",
                    "groom": "新郎",
                    "lover_a": "一方",
                    "lover_b": "另一方",
                    "parent": "父母",
                }.get(role_name, role_name)
                parts.append("%s：%s" % (role_zh, p_npc.name))
        if parts:
            roles_text = "\\n  ".join(parts)

    prompt = load_prompt("event_fill.md").format(
        template_id=tpl.id,
        template_label=template_label(tpl.id),
        prompt=tpl.prompt,
        participants=", ".join("%s(%s)" % (p.name, p.id) for p in participants) or "无",
        location=location,
        location_label=location_label(location),
        player_name=player_name,
        player_location=player_loc,
        roles=roles_text,
        day=world.day,
    )'''

if old in t:
    t = t.replace(old, new, 1)
    print("[fix] generators/event.py 传 roles")

# 修改 fill_event 签名
t = p.read_text(encoding="utf-8")
old_sig = '''async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    player: Player | None = None,
) -> Event:'''
new_sig = '''async def fill_event(
    tpl: EventTemplate,
    world: World,
    npcs: list[NPC],
    rng: random.Random,
    player: Player | None = None,
    event_roles: dict | None = None,
) -> Event:'''
if old_sig in t:
    t = t.replace(old_sig, new_sig, 1)
    print("[fix] fill_event 加 event_roles 参数")
else:
    print("[skip] fill_event 签名已改过")

p.write_text(t, encoding="utf-8")

# ============================================================
# 2. event_flow.py：先选角色，再填事件
# ============================================================
p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

# 当前是"先生成事件 → 再选角色"。要改成"先选角色 → 再生成事件"
# 但角色需要先抽参与者，所以顺序是：抽参与者 → 选角色 → fill_event
# 现有逻辑 fill_event 内部抽参与者，无法先知道参与者
# 折中方案：fill_event 之后重生成一次 summary（用具体角色名）

old_regen = '''    event = await fill_event(tpl, world, npcs, rng, player=player)'''

new_regen = '''    # 先抽一次参与者（用于选角色）—— 用同一个 rng 保持一致
    _tmp_participants = _pick_participant_ids(tpl, npcs, rng)
    _tmp_by_id = {n.id: n for n in npcs}
    pre_roles = _pick_roles(tpl, _tmp_participants, _tmp_by_id, rng)

    event = await fill_event(
        tpl, world, npcs, rng,
        player=player,
        event_roles=pre_roles,
    )'''

if old_regen in t:
    t = t.replace(old_regen, new_regen, 1)
    print("[fix] run_event_cycle 先生成角色再 fill_event")

# 加辅助函数 _pick_participant_ids
if "def _pick_participant_ids" not in t:
    anchor = "def _pick_roles("
    addition = '''def _pick_participant_ids(tpl, npcs, rng) -> list:
    """抽参与者 id 列表。与 fill_event 内部逻辑保持一致。"""
    n = int(tpl.params.get("participant_count", 2))
    n = min(n, len(npcs))
    if n <= 0:
        return []
    return [npc.id for npc in rng.sample(npcs, n)]


def _pick_roles('''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] event_flow 加 _pick_participant_ids")

# 删掉后面重复调用 _pick_roles 的代码
old_dup = '''    # 具体角色选择
    roles = _pick_roles(tpl, event.participants, npcs_by_id, rng)
    if roles:
        event.payload["roles"] = roles
        role_desc = ", ".join("%s=%s" % (k, npcs_by_id[v].name)
                              for k, v in roles.items() if v in npcs_by_id)
        print("[event] %s 具体角色：%s" % (tpl.id, role_desc))'''

new_dup = '''    # 角色已在生成前选好，直接写入
    if pre_roles:
        event.payload["roles"] = pre_roles
        role_desc = ", ".join("%s=%s" % (k, _tmp_by_id[v].name)
                              for k, v in pre_roles.items() if v in _tmp_by_id)
        print("[event] %s 具体角色：%s" % (tpl.id, role_desc))'''

if old_dup in t:
    t = t.replace(old_dup, new_dup, 1)
    print("[fix] run_event_cycle 角色写入调整")

p.write_text(t, encoding="utf-8")

# ============================================================
# 3. quest.py：用具体角色作为 target
# ============================================================
p = Path("server/systems/quest.py")
t = p.read_text(encoding="utf-8")

old_quest = '''    giver = participants[0] if participants else ""
    target = participants[1] if len(participants) > 1 else ""
    giver_name = npc_names.get(giver, "某人")'''

new_quest = '''    # 优先用具体角色
    roles = event.payload.get("roles", {})
    giver = roles.get("mother_or_father") or (participants[0] if participants else "")
    target = roles.get("child") or (participants[1] if len(participants) > 1 else "")
    giver_name = npc_names.get(giver, "某人")
    target_name = npc_names.get(target, "")'''

if old_quest in t:
    t = t.replace(old_quest, new_quest, 1)
    print("[fix] quest.py 用具体角色")

# 标题里也用 target_name
old_title = '''    title = rule["title"].format(
        target_npc=giver_name, giver_npc=giver_name
    )
    description = rule["description"].format(
        giver_npc=giver_name, target_npc=giver_name
    )'''
new_title = '''    if target_name and "寻找" in rule["title"]:
        title = "寻找%s的孩子（%s）" % (giver_name, target_name)
    else:
        title = rule["title"].format(
            target_npc=target_name or giver_name,
            giver_npc=giver_name,
        )
    description = rule["description"].format(
        giver_npc=giver_name,
        target_npc=target_name or giver_name,
    )'''
if old_title in t:
    t = t.replace(old_title, new_title, 1)
    print("[fix] quest.py 标题用具体孩子名")

p.write_text(t, encoding="utf-8")

# ============================================================
# 4. event_fill.md 加 {roles} 占位符
# ============================================================
p = Path("server/prompts/event_fill.md")
t = p.read_text(encoding="utf-8")

if "{roles}" not in t:
    old_md = '''参与者（**请使用这些名字**）：{participants}
地点：{location}（{location_label}）'''
    new_md = '''参与者（**请使用这些名字**）：{participants}

**具体角色（必须用这些名字）**：
  {roles}

地点：{location}（{location_label}）'''
    if old_md in t:
        t = t.replace(old_md, new_md, 1)
        p.write_text(t, encoding="utf-8")
        print("[fix] event_fill.md 加 roles 占位符")
    else:
        print("[skip] event_fill.md 锚点未找到")
else:
    print("[skip] event_fill.md 已有 roles")

print()
print("B 完成。重启后端")