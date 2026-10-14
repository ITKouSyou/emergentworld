# 修 main.gd 里重复的 cat 变量
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 找 _render_item_detail 函数
start = t.find("func _render_item_detail(")
if start < 0:
    print("[fail] 找不到 _render_item_detail")
    raise SystemExit(1)

end = t.find("\nfunc ", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]

# 把后半段那个"# 装备按钮"处的 cat 改成 cat_eq
old = '''		# 装备按钮：仅装备类可用
		var cat: String = str(it.get("category", "material"))
		if equip_btn != null:
			equip_btn.disabled = not (is_player and cat == "equipment")
		return'''

new = '''		# 装备按钮：仅装备类可用
		var cat_eq: String = str(it.get("category", "material"))
		if equip_btn != null:
			equip_btn.disabled = not (is_player and cat_eq == "equipment")
		return'''

if old in body:
    body = body.replace(old, new, 1)
    t = t[:start] + body + t[end:]
    p.write_text(t, encoding="utf-8")
    print("[fix] 第二个 cat → cat_eq")
else:
    # 兜底：把所有 var cat 之外的多余 cat 改成 cat_eq
    print("[skip] 未找到目标，打印所有含 cat 的行：")
    for i, line in enumerate(body.split("\n")):
        if "cat" in line and "var cat" in line:
            print("  %s" % line)

print()
print("Godot 完全关闭重开，按 F5")