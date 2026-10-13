# 把属性名和 tick 都换中文
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# ---------- 1. 顶部 Tick → 回合 ----------
t = t.replace(
    '"Tick %d',
    '"第 %d 回合',
)
t = t.replace(
    'Tick %d',
    '第 %d 回合',
)
# 更保守：只改显示文本
t = t.replace(
    'Tick %d   张力',
    '第 %d 回合  张力',
)
t = t.replace(
    '   Tick %d   张力',
    '   第 %d 回合  张力',
)

# 直接找状态栏那行做替换
import re
# 模式： Tick %d
t = re.sub(r'Tick %d', '第 %d 回合', t)
t = re.sub(r'Tick %d', '第 %d 回合', t)

print("[fix] Tick → 回合")

# ---------- 2. 史册"记录于第 N tick" ----------
t = t.replace(
    '记录于第 %d tick',
    '记录于第 %d 回合',
)

# ---------- 3. _on_action_done 里的属性名映射 ----------
old_check = '''	var check = data.get("check", {})
	if check is Dictionary and check.has("result"):
		var result_zh: String = {
			"critical": "大成功",
			"success": "成功",
			"partial": "勉强",
			"failure": "失败",
		}.get(str(check.get("result", "")), "")
		lines.append("[color=cyan]%s  %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]" % [
			str(check.get("attribute", "")),
			int(check.get("base", 0)),
			int(check.get("roll", 0)),
			int(check.get("total", 0)),
			int(check.get("threshold", 0)),
			result_zh,
		])'''

new_check = '''	var check = data.get("check", {})
	if check is Dictionary and check.has("result"):
		var result_zh: String = {
			"critical": "大成功",
			"success": "成功",
			"partial": "勉强",
			"failure": "失败",
		}.get(str(check.get("result", "")), "")
		var attr_key: String = str(check.get("attribute", ""))
		var attr_zh: String = {
			"strength": "力量",
			"agility": "敏捷",
			"intelligence": "智慧",
			"perception": "感知",
			"charisma": "魅力",
			"luck": "运气",
		}.get(attr_key, attr_key)
		lines.append("[color=cyan]%s %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]" % [
			attr_zh,
			int(check.get("base", 0)),
			int(check.get("roll", 0)),
			int(check.get("total", 0)),
			int(check.get("threshold", 0)),
			result_zh,
		])'''

if old_check in t:
    t = t.replace(old_check, new_check, 1)
    print("[fix] _on_action_done 属性名换中文")
else:
    print("[skip] _on_action_done 已改过或未匹配")

# ---------- 4. _on_event_resolved 里的属性名（事件结算） ----------
old_evt = '''			event_log.append_text(
				"    [color=cyan]%s %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]\\n" % [
					_attr_label_from_dict(check),
					int(check.get("base", 0)),
					int(check.get("roll", 0)),
					int(check.get("total", 0)),
					int(check.get("threshold", 0)),
					result_zh,
				])'''

new_evt = '''			event_log.append_text(
				"    [color=cyan]%s %d + 骰 %d = %d vs 难度 %d → [b]%s[/b][/color]\\n" % [
					_attr_label_from_dict(check),
					int(check.get("base", 0)),
					int(check.get("roll", 0)),
					int(check.get("total", 0)),
					int(check.get("threshold", 0)),
					result_zh,
				])'''
# 这个已经用 _attr_label_from_dict，不用改

# ---------- 5. _on_travel_done 加中文提示 ----------
# 已有"你从...来到..."，无需改

p.write_text(t, encoding="utf-8")
print()
print("Godot 完全关闭重开，按 F5")