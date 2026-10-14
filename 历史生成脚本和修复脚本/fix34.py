# 删孤儿行 + 确保 _connect_signals 里有 quest 信号
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")
lines = t.split("\n")

# 1. 删除所有顶格的 api.xxx.connect 行
new_lines = []
removed = 0
for line in lines:
    s = line.lstrip()
    if s.startswith("api.") and ".connect(" in s and line == s:
        print("删除孤儿：%s" % line[:80])
        removed += 1
        continue
    new_lines.append(line)

t = "\n".join(new_lines)
print("[fix] 删除 %d 个孤儿行" % removed)

# 2. 确保 _connect_signals 里有 quest_abandoned
start = t.find("func _connect_signals() -> void:")
after = t.find("\nfunc ", start + 1)
if after < 0:
    after = len(t)
body = t[start:after]

if "api.quest_abandoned.connect" not in body:
    anchor = "api.request_failed.connect(_on_request_failed)"
    if anchor not in body:
        anchor = "\tapi.request_failed.connect(_on_request_failed)"
    if anchor in body:
        indent = anchor[:len(anchor) - len(anchor.lstrip())]
        new_line = indent + "api.quest_abandoned.connect(_on_quest_abandoned)"
        body = body.replace(anchor, new_line + "\n" + anchor, 1)
        t = t[:start] + body + t[after:]
        print("[fix] 加 quest_abandoned 连接")

p.write_text(t, encoding="utf-8")

# 3. 打印新 _connect_signals
t2 = p.read_text(encoding="utf-8")
start2 = t2.find("func _connect_signals() -> void:")
after2 = t2.find("\nfunc ", start2 + 1)
print()
print("--- 新 _connect_signals ---")
for line in t2[start2:after2].split("\n"):
    if line:
        first = line[0]
        marker = "T" if first == "\t" else ("S" if first == " " else "-")
        print("%s | %s" % (marker, line[:90]))

# 4. 再扫一遍孤儿
t3 = p.read_text(encoding="utf-8")
orphans = []
for i, line in enumerate(t3.split("\n")):
    s = line.lstrip()
    if s.startswith("api.") and ".connect(" in s and line == s:
        orphans.append(i+1)
if orphans:
    print()
    print("[warn] 还有孤儿行：%r" % orphans)
else:
    print()
    print("[ok] 无孤儿行")

print()
print("Godot 完全关闭重开，按 F5")