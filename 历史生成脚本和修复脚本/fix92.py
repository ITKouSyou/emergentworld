# 补齐 4 个装备相关函数 + 修 sk 类型
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 修 sk 类型
old_sk = '''		var sk := slot_key
		un_btn.pressed.connect(func(): _on_unequip_pressed(sk))'''
new_sk = '''		var sk: String = str(slot_key)
		un_btn.pressed.connect(func(): _on_unequip_pressed(sk))'''
if old_sk in t:
    t = t.replace(old_sk, new_sk, 1)
    print("[fix] sk 加显式类型")
else:
    # 备用：可能格式不同
    import re
    pattern = re.compile(r"(\s+var )sk :=\s*slot_key")
    if pattern.search(t):
        t = pattern.sub(r"\1sk: String = slot_key", t, count=1)
        print("[fix] sk 正则替换")

# 2. 检查 4 个函数是否存在
needed = [
    "_on_equip_done",
    "_on_unequip_done",
    "_on_equip_pressed",
    "_on_unequip_pressed",
]
missing = [f for f in needed if ("func %s(" % f) not in t]

print()
print("缺失的函数：%r" % missing)

if missing:
    tail = "\n"
    if "_on_unequip_pressed" in missing:
        tail += '''
func _on_unequip_pressed(slot: String) -> void:
	api.unequip_slot(slot)
'''
    if "_on_equip_done" in missing:
        tail += '''
func _on_equip_done(data: Dictionary) -> void:
	api.fetch_player()
	api.fetch_items(200)
	status_label.text = "[color=gold]装备：%s（%s）[/color]" % [
		str(data.get("item_name", "")),
		str(data.get("slot_label", "")),
	]
'''
    if "_on_unequip_done" in missing:
        tail += '''
func _on_unequip_done(data: Dictionary) -> void:
	api.fetch_player()
	api.fetch_items(200)
	status_label.text = "[color=gray]已卸下 %s[/color]" % str(data.get("slot", ""))
'''
    if "_on_equip_pressed" in missing:
        tail += '''
func _on_equip_pressed() -> void:
	if current_item_id == "":
		return
	api.equip_item(current_item_id)
'''
    t = t.rstrip() + "\n" + tail
    p.write_text(t, encoding="utf-8")
    print("[fix] 补齐 %d 个函数" % len(missing))
else:
    print("[skip] 4 个函数都已存在")

# 3. 确认信号连接是否在 _connect_signals 里
start = t.find("func _connect_signals() -> void:") if "_connect_signals" in t else t.find("func _connect_signals")
if start >= 0:
    end = t.find("\nfunc ", start + 1)
    body = t[start:end] if end > 0 else t[start:]
    if "api.equip_done.connect" not in body:
        print("[warn] _connect_signals 里没有 equip_done 连接，请检查")
    if "api.unequip_done.connect" not in body:
        print("[warn] _connect_signals 里没有 unequip_done 连接")

print()
print("Godot 完全关闭重开，按 F5")