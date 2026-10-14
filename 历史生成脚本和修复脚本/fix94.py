from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

old = '		item_detail.append_text("\\n\\n[color=gray]（装备系统下一轮实现，先占位）[/color]")\n		return'
new = '		# 装备走 /equip 端点\n		api.equip_item(current_item_id)\n		return'

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 装备按钮调用 /equip")
else:
    # 找另一段
    import re
    pattern = re.compile(r'\t+item_detail\.append_text\("\\n\\n\[color=gray\]（装备系统下一轮实现[^"]*"\)\n\t+return')
    if pattern.search(t):
        t = pattern.sub('\t\tapi.equip_item(current_item_id)\n\t\treturn', t, count=1)
        p.write_text(t, encoding="utf-8")
        print("[fix] 装备按钮正则替换")
    else:
        print("[skip] 未找到旧提示代码")