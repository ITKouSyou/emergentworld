# 前端：显示 HP + 铜钱 + 战斗信息
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. _render_player_panel 里显示 HP / 铜钱
old = '''	lines.append("[b]等级：[/b]%d   [b]经验：[/b]%d / %d" % [level, exp, exp_next])
	lines.append("[b]可分配点：[/b]%d" % unspent)
	lines.append("[b]声誉：[/b]%d" % rep)'''

new = '''	lines.append("[b]等级：[/b]%d   [b]经验：[/b]%d / %d" % [level, exp, exp_next])
	var hp: int = int(player_data.get("hp", 100))
	var max_hp: int = int(player_data.get("max_hp", 100))
	var hp_color := "lightgreen"
	if max_hp > 0 and hp < max_hp * 0.3:
		hp_color = "red"
	elif max_hp > 0 and hp < max_hp * 0.7:
		hp_color = "yellow"
	lines.append("[b]生命：[/b][color=%s]%d / %d[/color]" % [hp_color, hp, max_hp])
	var money: int = int(player_data.get("money", 0))
	lines.append("[b]铜钱：[/b][color=gold]%d[/color]" % money)
	lines.append("[b]可分配点：[/b]%d" % unspent)
	lines.append("[b]声誉：[/b]%d" % rep)'''

if old in t:
    t = t.replace(old, new, 1)
    print("[fix] 显示 HP + 铜钱")
else:
    print("[skip] _render_player_panel 已改过或未匹配")

# 2. _on_action_done 显示战斗
old2 = '''	var msg: String = str(data.get("message", ""))
	if msg != "":
		lines.append(msg)'''

new2 = '''	var combat = data.get("combat")
	if combat is Dictionary:
		var enemy: String = str(combat.get("enemy", ""))
		if enemy != "":
			lines.append("")
			lines.append("[color=red]⚔ 遭遇：%s[/color]" % enemy)

	var msg: String = str(data.get("message", ""))
	if msg != "":
		lines.append(msg)

	var hp_before = data.get("hp_before")
	var hp_after = data.get("hp_after")
	if hp_before != null and hp_after != null:
		var dmg: int = int(data.get("damage", 0))
		if dmg > 0:
			lines.append("[color=red]损失生命 %d（现 %d）[/color]" % [dmg, int(hp_after)])
		else:
			lines.append("[color=lightgreen]安然无恙[/color]")'''

if old2 in t:
    t = t.replace(old2, new2, 1)
    print("[fix] 战斗结果显示")
else:
    print("[skip] 战斗显示已改过或未匹配")

p.write_text(t, encoding="utf-8")
print()
print("C 完成。")
print()
print("==== 重启 ====")
print("1. Ctrl+C 停掉 uvicorn")
print("2. uvicorn server.main:app --reload")
print("3. Godot 完全关闭重开，按 F5")