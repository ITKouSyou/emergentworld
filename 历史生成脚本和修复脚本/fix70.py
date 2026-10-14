# 修 main.gd 里重复的 fl 变量
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 找 _on_npc_detail 函数
start = t.find("func _on_npc_detail")
if start < 0:
    print("[fail] 找不到 _on_npc_detail")
    raise SystemExit(1)

end = t.find("\nfunc ", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]

# 把新增的派系代码里的 fl 改名
old = '''	var fl: String = str(data.get("faction_label", ""))
	if fl != "" and fl != "中立":
		lines.append("所属派系：[color=gold]%s[/color]" % fl)'''

new = '''	var fac_label: String = str(data.get("faction_label", ""))
	if fac_label != "" and fac_label != "中立":
		lines.append("所属派系：[color=gold]%s[/color]" % fac_label)'''

if old in body:
    body = body.replace(old, new, 1)
    t = t[:start] + body + t[end:]
    p.write_text(t, encoding="utf-8")
    print("[fix] fl → fac_label")
else:
    print("[skip] 未找到目标代码，可能已改过")
    # 打印所有 fl 出现位置
    print()
    print("=== 当前 _on_npc_detail 里所有 fl ===")
    for i, line in enumerate(body.split("\n")):
        if "fl" in line:
            print("  %s" % line)

print()
print("Godot 完全关闭重开，按 F5")