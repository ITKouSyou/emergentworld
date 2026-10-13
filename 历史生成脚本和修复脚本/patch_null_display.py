"""修复旧事件的 <null> 显示 + 后端返回空字符串而非 null。"""
from pathlib import Path

# ---------- 1. 后端：_row_to_event 里 None → "" ----------
p = Path("server/main.py")
text = p.read_text(encoding="utf-8")

OLD_BLOCK = '''    return {
        "id": r.id,
        "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": participants,
        "participant_names": participant_names,
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state,
        "state_label": i18n.state_label(r.state),
        "awaiting_player": r.state == "awaiting_player",
        "payload": payload,
        "summary": payload.get("summary", ""),
        "narrative": payload.get("narrative", ""),
        "choices": choices,
        "choice_made": choice_made,
        "choice_label": payload.get("choice_label"),
        "outcome": payload.get("outcome"),
        "item_id": payload.get("item_id"),
        "item_owner": payload.get("item_owner"),
        "created_at": r.created_at,
        "resolved_at": r.resolved_at,
    }'''

NEW_BLOCK = '''    return {
        "id": r.id,
        "template_id": r.template_id,
        "template_label": i18n.template_label(r.template_id),
        "participants": participants,
        "participant_names": participant_names,
        "location_id": r.location_id,
        "location_label": i18n.location_label(r.location_id),
        "state": r.state,
        "state_label": i18n.state_label(r.state),
        "awaiting_player": r.state == "awaiting_player",
        "payload": payload,
        "summary": payload.get("summary") or "",
        "narrative": payload.get("narrative") or "",
        "choices": choices,
        "choice_made": choice_made or "",
        "choice_label": payload.get("choice_label") or "",
        "outcome": payload.get("outcome") or "",
        "item_id": payload.get("item_id") or "",
        "item_owner": payload.get("item_owner") or "",
        "created_at": r.created_at,
        "resolved_at": r.resolved_at,
    }'''

if OLD_BLOCK in text:
    text = text.replace(OLD_BLOCK, NEW_BLOCK)
    p.write_text(text, encoding="utf-8", newline="\n")
    print("[fix] server/main.py: None → ''")
else:
    print("[skip] server/main.py: 未匹配（可能已改过）")

# ---------- 2. 前端：_render_event_entry 防御性处理 ----------
g = Path("client/main.gd")
gt = g.read_text(encoding="utf-8")

OLD_RENDER = '''	var tpl_label: String = str(e.get("template_label", e.get("template_id", "?")))
	var loc_label: String = str(e.get("location_label", ""))
	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			ns.append(str(n))
		names_str = "（" + "、".join(ns) + "）"

	var summary: String = str(e.get("summary", ""))
	var narrative: String = str(e.get("narrative", ""))
	var outcome: String = str(e.get("outcome", ""))
	var choice_label: String = str(e.get("choice_label", ""))'''

NEW_RENDER = '''	var tpl_label: String = _safe_str(e.get("template_label", e.get("template_id", "?")))
	var loc_label: String = _safe_str(e.get("location_label", ""))
	var names_arr: Array = e.get("participant_names", [])
	var names_str := ""
	if not names_arr.is_empty():
		var ns: Array[String] = []
		for n in names_arr:
			ns.append(_safe_str(n))
		names_str = "（" + "、".join(ns) + "）"

	var summary: String = _safe_str(e.get("summary", ""))
	var narrative: String = _safe_str(e.get("narrative", ""))
	var outcome: String = _safe_str(e.get("outcome", ""))
	var choice_label: String = _safe_str(e.get("choice_label", ""))'''

if OLD_RENDER in gt:
    gt = gt.replace(OLD_RENDER, NEW_RENDER)
    print("[fix] client/main.gd: 使用 _safe_str")
else:
    print("[skip] client/main.gd: _render_event_entry 未匹配")

# 加 _safe_str 辅助函数（放在 _on_request_failed 前面）
if "func _safe_str(" not in gt:
    NEW_HELPER = '''

func _safe_str(v) -> String:
	if v == null:
		return ""
	return str(v)

'''
    # 插到文件末尾
    gt = gt.rstrip() + "\n" + NEW_HELPER
    print("[fix] client/main.gd: 添加 _safe_str")

g.write_text(gt, encoding="utf-8", newline="\n")

# ---------- 3. 也修一下事件列表过滤：旧事件不显示"你的选择" ----------
OLD_HIST = '''		if choice_label != "":
			event_log.append_text("    [i]你的选择：%s[/i]\\n" % choice_label)
		if outcome != "":
			event_log.append_text("    [color=lightgreen]%s[/color]\\n" % outcome)'''

NEW_HIST = '''		if choice_label != "" and choice_label != "<null>":
			event_log.append_text("    [i]你的选择：%s[/i]\\n" % choice_label)
		if outcome != "" and outcome != "<null>":
			event_log.append_text("    [color=lightgreen]%s[/color]\\n" % outcome)'''

if OLD_HIST in gt:
    gt = gt.replace(OLD_HIST, NEW_HIST)
    g.write_text(gt, encoding="utf-8", newline="\n")
    print("[fix] client/main.gd: 过滤 <null> 显示")

print()
print("回到 Godot 会自动重载。")
print()
print("================================")
print("为什么看不到橙色事件？")
print("================================")
print("你截图里的都是 Part 15 之前生成的旧数据，状态是 resolved。")
print("新代码只对新触发的事件生成 awaiting_player 状态。")
print()
print("操作：")
print("  1. 点一次【触发事件】按钮")
print("  2. 或连点几次【推进一 tick】")
print()
print("新事件会出现在编年史顶部，橙色高亮，可直接点击。")