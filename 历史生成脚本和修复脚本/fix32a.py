# 加模板参与者前置条件
from pathlib import Path

p = Path("server/core/event_flow.py")
t = p.read_text(encoding="utf-8")

# 1. 定义前置条件表
if "TEMPLATE_REQUIRES" not in t:
    anchor = "PLAYER_TIMEOUT_TICKS = 8"
    addition = '''PLAYER_TIMEOUT_TICKS = 8

# 模板 → 参与者需满足的条件
#   has_children  至少一人有子女
#   has_spouse    至少一人有配偶
#   no_spouse     至少一人未婚
#   has_family    至少一人有家人
TEMPLATE_REQUIRES = {
    "lost_child": "has_children",
    "romance_blooms": "no_spouse",
    "lovers_quarrel": "has_spouse",
    "wedding": "no_spouse",
    "broken_promise": "has_family",
    "funeral": "has_family",
    "birth_of_child": "has_spouse",
}
'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] event_flow 加 TEMPLATE_REQUIRES")
    else:
        print("[fail] event_flow 锚点未找到")

# 2. 加校验函数
if "def _participants_valid" not in t:
    anchor = "def _pending_rows(session: Session) -> list[EventRow]:"
    addition = '''def _participants_valid(tpl, participants_ids: list[str], npcs_by_id: dict) -> bool:
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


def _pending_rows(session: Session) -> list[EventRow]:'''
    if anchor in t:
        t = t.replace(anchor, addition, 1)
        print("[fix] event_flow 加 _participants_valid")
    else:
        print("[fail] event_flow 加校验函数锚点未找到")

# 3. 在事件生成后调用校验
old_check = '''    # 相关性判定
    relevance_ok = False'''
new_check = '''    # 参与者合理性校验
    npcs_by_id = {n.id: n for n in npcs}
    if not _participants_valid(tpl, event.participants, npcs_by_id):
        print("[event] 参与者不满足 %s 的前置条件，拒绝：%s" % (
            tpl.id, event.participants))
        event.state = "rejected"
        save_event(session, event)
        return None

    # 相关性判定
    relevance_ok = False'''
if old_check in t and "参与者合理性校验" not in t:
    t = t.replace(old_check, new_check, 1)
    print("[fix] event_flow 加校验调用")

p.write_text(t, encoding="utf-8")
print()
print("A 完成。下一步 fix32b.py")