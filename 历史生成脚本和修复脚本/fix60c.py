# Part 60C：对话时注入"你在事件里扮演的角色"
from pathlib import Path

p = Path("server/generators/dialogue.py")
t = p.read_text(encoding="utf-8")

if "_recent_events_for_npc" not in t:
    print("[fail] dialogue.py 太旧，请先跑 fix32b")
    raise SystemExit(1)

# 修改 _recent_events_for_npc，把 role 信息带出来
old = '''    lines: list[str] = []
    for r in rows:
        participants = _loads(r.participants_json) or []
        if npc_id not in participants:
            continue
        payload = _loads(r.payload_json) or {}
        summary = payload.get("summary", "")
        outcome = payload.get("outcome", "")
        state = r.state'''

new = '''    lines: list[str] = []
    for r in rows:
        participants = _loads(r.participants_json) or []
        if npc_id not in participants:
            continue
        payload = _loads(r.payload_json) or {}
        summary = payload.get("summary", "")
        outcome = payload.get("outcome", "")
        state = r.state

        # 检查这个 NPC 在事件里扮演什么角色
        roles = payload.get("roles", {})
        role_marker = ""
        if isinstance(roles, dict):
            for role_name, npc_in_role in roles.items():
                if npc_in_role == npc_id:
                    role_zh = {
                        "mother_or_father": "家长",
                        "child": "走失的孩子",
                        "deceased": "逝者",
                        "bride": "新娘",
                        "groom": "新郎",
                        "lover_a": "当事一方",
                        "lover_b": "当事另一方",
                        "parent": "父母",
                    }.get(role_name, role_name)
                    role_marker = "（你在其中是：%s）" % role_zh
                    break'''

if old in t:
    t = t.replace(old, new, 1)
    print("[fix] _recent_events_for_npc 识别角色")

# 输出行里带上 role_marker
old2 = '''        line = "- %s%s" % (summary, marker)
        if outcome:
            line += "  结果：" + outcome[:40]
        lines.append(line)'''

new2 = '''        line = "- %s%s%s" % (summary, marker, role_marker)
        if outcome:
            line += "  结果：" + outcome[:40]
        lines.append(line)'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    print("[fix] 输出带 role_marker")

p.write_text(t, encoding="utf-8")

# 顺便：dialogue.md 里加一条提示
p2 = Path("server/prompts/dialogue.md")
t2 = p2.read_text(encoding="utf-8")

if "扮演的角色" not in t2:
    old_md = '''你最近经历的事：
{recent_events}'''
    new_md = '''你最近经历的事（括号里是你扮演的角色）：
{recent_events}

**重要：如果玩家问起上述事件，你必须基于你扮演的角色回答，不要编造矛盾的情节。**
比如你扮演"走失的孩子"，就要承认自己确实走失了（或说明情况）。
如果你扮演"家长"，就要表现出对孩子的担忧。'''
    if old_md in t2:
        t2 = t2.replace(old_md, new_md, 1)
        p2.write_text(t2, encoding="utf-8")
        print("[fix] dialogue.md 加强一致性约束")

print()
print("C 完成。清库 + seed + 重启")