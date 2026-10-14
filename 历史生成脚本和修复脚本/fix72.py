# 用最后一个 connect 做锚点
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

start = t.find("func _connect_signals() -> void:")
if start < 0:
    print("[fail] 找不到 _connect_signals")
    raise SystemExit(1)

after = t.find("\nfunc ", start + 1)
if after < 0:
    after = len(t)

body = t[start:after]

# 需要补上的信号
needed = [
    ("api.factions_received", "_on_factions_received"),
    ("api.quest_abandoned", "_on_quest_abandoned"),
    ("api.request_failed", "_on_request_failed"),
]

added = []
for sig, handler in needed:
    if sig + ".connect" in body:
        continue
    # 用最后一行 connect 做锚点
    lines = body.split("\n")
    # 找最后一行 8 空格 + api.xxx.connect 的行
    insert_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if s.startswith("api.") and ".connect(" in s:
            insert_idx = i
            break

    if insert_idx < 0:
        print("[fail] 找不到任何 connect 行，用于插入 %s" % sig)
        continue

    # 沿用那一行的缩进
    indent = lines[insert_idx][:len(lines[insert_idx]) - len(lines[insert_idx].lstrip())]
    new_line = indent + sig + ".connect(" + handler + ")"
    lines.insert(insert_idx + 1, new_line)
    body = "\n".join(lines)
    added.append(sig)

t = t[:start] + body + t[after:]
p.write_text(t, encoding="utf-8")
print("[fix] 添加信号：%r" % added)

# 打印
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
print(t2[start2:after2])

print()
print("Godot 完全关闭重开，按 F5")