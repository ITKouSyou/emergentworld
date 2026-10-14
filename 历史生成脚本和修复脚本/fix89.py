from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = '''		var cat_label := {
			"consumable": "消耗品",
			"equipment": "装备",
			"material": "材料",
			"key": "钥匙",
			"quest": "剧情物品",
		}.get(cat, "材料")'''

new = '''		var cat_label: String = {
			"consumable": "消耗品",
			"equipment": "装备",
			"material": "材料",
			"key": "钥匙",
			"quest": "剧情物品",
		}.get(cat, "材料")'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] cat_label 加显式类型")
else:
    # 尝试更宽松的匹配
    import re
    pattern = re.compile(
        r"var cat_label :=\s*\{[^}]*\}\.get\(cat,\s*\"材料\"\)",
        re.DOTALL,
    )
    new_text = pattern.sub(
        lambda m: m.group(0).replace("var cat_label :=", "var cat_label: String ="),
        t,
    )
    if new_text != t:
        p.write_text(new_text, encoding="utf-8")
        print("[fix] 正则替换 cat_label")
    else:
        print("[skip] 未匹配，可能已改过")