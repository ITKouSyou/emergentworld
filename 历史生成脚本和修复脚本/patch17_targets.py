"""patch main.py 和 client/main.gd 的两个小改动。"""
from pathlib import Path

# ============ server/main.py ============
p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

OLD = (
    '        "name": npc.name,\n'
    '        "age": npc.age,\n'
    '        "location_id": npc.location_id,\n'
)
NEW = (
    '        "name": npc.name,\n'
    '        "age": npc.age,\n'
    '        "gender": npc.gender,\n'
    '        "gender_label": i18n.gender_label(npc.gender),\n'
    '        "location_id": npc.location_id,\n'
)

if OLD in t and '"gender"' not in t:
    t = t.replace(OLD, NEW, 1)
    p.write_text(t, encoding="utf-8", newline="\n")
    print("[fix] server/main.py _npc_to_display 加 gender")
elif '"gender_label"' in t:
    print("[skip] server/main.py 已有 gender")
else:
    print("[fail] server/main.py 匹配失败，请手动加 gender 字段")

# ============ client/main.gd ============
g = Path("client/main.gd")
gt = g.read_text(encoding="utf-8")

# 1. NPC 详情加性别显示
OLD_DETAIL = (
    '\tlines.append("[b][color=yellow]%s[/color][/b]   %d 岁" % [\n'
    '\t\tstr(data.get("name", "?")),\n'
    '\t\tint(data.get("age", 0)),\n'
    '\t])'
)
NEW_DETAIL = (
    '\tvar gender_zh: String = str(data.get("gender_label", ""))\n'
    '\tif gender_zh == "":\n'
    '\t\tgender_zh = "未知"\n'
    '\tlines.append("[b][color=yellow]%s[/color][/b]   %s   %d 岁" % [\n'
    '\t\tstr(data.get("name", "?")),\n'
    '\t\tgender_zh,\n'
    '\t\tint(data.get("age", 0)),\n'
    '\t])'
)

if OLD_DETAIL in gt:
    gt = gt.replace(OLD_DETAIL, NEW_DETAIL)
    print("[fix] client/main.gd NPC 详情加性别")
elif 'gender_label' in gt:
    print("[skip] client/main.gd 已有性别显示")
else:
    print("[fail] client/main.gd 详情函数匹配失败")

# 2. 物品按钮按 owner 启用
OLD_SEL = (
    'func _on_item_selected(index: int) -> void:\n'
    '\tif index < 0 or index >= item_order.size():\n'
    '\t\treturn\n'
    '\tcurrent_item_id = item_order[index]\n'
    '\t_render_item_detail(current_item_id)\n'
    '\t_set_item_buttons_enabled(true)'
)
NEW_SEL = (
    'func _on_item_selected(index: int) -> void:\n'
    '\tif index < 0 or index >= item_order.size():\n'
    '\t\treturn\n'
    '\tcurrent_item_id = item_order[index]\n'
    '\t_render_item_detail(current_item_id)'
)
if OLD_SEL in gt:
    gt = gt.replace(OLD_SEL, NEW_SEL)
    print("[fix] client/main.gd _on_item_selected")

OLD_RENDER_TAIL = (
    '\t\tlines.append("价值：%.2f" % value)\n'
    '\t\titem_detail.text = "\\n".join(lines)\n'
    '\t\treturn'
)
NEW_RENDER_TAIL = (
    '\t\tlines.append("价值：%.2f" % value)\n'
    '\t\titem_detail.text = "\\n".join(lines)\n'
    '\n'
    '\t\tvar owner_id: String = str(it.get("owner_id", ""))\n'
    '\t\tvar is_player := owner_id == "player"\n'
    '\t\tvar is_npc := owner_id != "" and owner_id != "player"\n'
    '\t\tuse_btn.disabled = not is_player\n'
    '\t\tgive_btn.disabled = not is_player\n'
    '\t\tdrop_btn.disabled = not is_player\n'
    '\t\ttake_btn.disabled = not is_npc\n'
    '\t\treturn'
)
if OLD_RENDER_TAIL in gt:
    gt = gt.replace(OLD_RENDER_TAIL, NEW_RENDER_TAIL)
    print("[fix] client/main.gd 物品按钮状态")

g.write_text(gt, encoding="utf-8", newline="\n")
print()
print("回到 Godot 自动重载")