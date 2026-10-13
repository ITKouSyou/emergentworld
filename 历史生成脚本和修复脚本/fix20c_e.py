# 删除 main.gd 末尾重复的 _on_explore_pressed / _on_explore_done
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

lines = t.split("\n")

# 找到所有出现位置
pos_pressed = []
pos_done = []
for i, line in enumerate(lines):
    if line.startswith("func _on_explore_pressed("):
        pos_pressed.append(i)
    if line.startswith("func _on_explore_done("):
        pos_done.append(i)

print("_on_explore_pressed 出现位置：%r" % pos_pressed)
print("_on_explore_done 出现位置：%r" % pos_done)

if len(pos_pressed) < 2 and len(pos_done) < 2:
    print("[skip] 没有重复")
    raise SystemExit(0)

# 找出要删除的范围：从第二个 _on_explore_pressed 开始到文件末尾（或者下一个非 explore 相关函数）
# 简单做法：找最后一个"func _ensure_explore_ui("的位置，如果它晚于第一个 define，
# 就把从它到文件末尾（如果末尾都是这几个函数）删掉。
# 更保险：直接删掉最后一次出现的 _on_explore_pressed 到文件末尾。

# 找第二次出现 _on_explore_pressed 的起始行
if len(pos_pressed) >= 2:
    start = pos_pressed[-1]
else:
    start = pos_done[-1]

# 从 start 向前找最后一个空行作为分隔
while start > 0 and lines[start - 1].strip() != "":
    start -= 1

print("将从第 %d 行（1-indexed 为 %d）截断到文件末尾" % (start, start + 1))

# 保留前 start 行
new_lines = lines[:start]

# 去掉末尾多余空行
while new_lines and new_lines[-1].strip() == "":
    new_lines.pop()

new_content = "\n".join(new_lines) + "\n"
p.write_text(new_content, encoding="utf-8")

print("[fix] 已删除末尾重复的 explore 函数")
print()
print("回 Godot 按 F5")