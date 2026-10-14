# 1. _build_ui 里调用 _build_faction_tab
# 2. 连接 factions_received 信号
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 在 _build_ui 里插入调用
old = '''	_build_event_tab(right_tabs)
	_build_quest_tab(right_tabs)
	_build_chronicle_tab(right_tabs)'''
new = '''	_build_event_tab(right_tabs)
	_build_quest_tab(right_tabs)
	_build_faction_tab(right_tabs)
	_build_chronicle_tab(right_tabs)'''

if old in t:
    t = t.replace(old, new, 1)
    print("[fix] _build_ui 调用 _build_faction_tab")
else:
    print("[fail] _build_ui 锚点未找到")

# 2. 连接信号
start = t.find("func _connect_signals() -> void:")
if start >= 0:
    after = t.find("\nfunc ", start + 1)
    if after < 0:
        after = len(t)
    body = t[start:after]

    if "api.factions_received.connect" not in body:
        # 找锚点
        for anchor_try in [
            "api.request_failed.connect(_on_request_failed)",
            "\tapi.request_failed.connect(_on_request_failed)",
        ]:
            if anchor_try in body:
                indent = anchor_try[:len(anchor_try) - len(anchor_try.lstrip())]
                new_line = indent + "api.factions_received.connect(_on_factions_received)"
                body = body.replace(anchor_try, new_line + "\n" + anchor_try, 1)
                t = t[:start] + body + t[after:]
                p.write_text(t, encoding="utf-8")
                print("[fix] 连接 factions_received 信号")
                break
        else:
            print("[fail] 信号连接锚点未找到")
    else:
        print("[skip] 已有 factions_received 连接")

# 打印新 _connect_signals 确认
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
print(t2[start2:after2])

print()
print("Godot 完全关闭重开，按 F5")