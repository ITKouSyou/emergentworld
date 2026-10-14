# 给所有 RichTextLabel 加 autowrap + 限制右栏宽度
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

# 1. 给右栏加固定宽度（不撑开）
old = '''	var right_tabs := TabContainer.new()
	right_tabs.custom_minimum_size = Vector2(420, 0)
	right_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(right_tabs)'''

new = '''	var right_tabs := TabContainer.new()
	right_tabs.custom_minimum_size = Vector2(420, 0)
	right_tabs.size_flags_horizontal = Control.SIZE_SHRINK_END
	right_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_child(right_tabs)'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] 右栏固定宽度")
else:
    print("[skip] 右栏锚点未找到")

# 2. 给所有 RichTextLabel 加 autowrap_mode
# 找所有 RichTextLabel.new() 创建的地方
t = p.read_text(encoding="utf-8")

# 用一个替换表覆盖所有常见模式
import re

# 用正则找所有 "xxx = RichTextLabel.new()" 后面的几行，插入 autowrap
# 简单粗暴：全局替换 "bbcode_enabled = true" 后插入 autowrap
replacement_count = 0

# 给每个 RichTextLabel 加 autowrap
lines = t.split("\n")
new_lines = []
i = 0
while i < len(lines):
    new_lines.append(lines[i])
    # 检测 xxx = RichTextLabel.new()
    if "= RichTextLabel.new()" in lines[i]:
        # 在后续 5 行内插入 autowrap（如果还没插入）
        # 找下一行合适位置
        insert_at = len(new_lines) - 1
        # 看后面几行有 bbcode_enabled
        for j in range(i + 1, min(i + 6, len(lines))):
            if "bbcode_enabled = true" in lines[j]:
                insert_at = j
                break
        # 插入 autowrap（我们在此循环处理，等碰到 bbcode_enabled 后再加）
    # 检测 bbcode_enabled = true 后是否需要加 autowrap
    if "bbcode_enabled = true" in lines[i]:
        new_lines.append("")  # 占位
        # 检查下一行是否已有 autowrap
        has_autowrap = False
        for j in range(i + 1, min(i + 4, len(lines))):
            if "autowrap_mode" in lines[j]:
                has_autowrap = True
                break
        if not has_autowrap:
            # 获得缩进
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            new_lines.append(indent + "autowrap_mode = TextServer.AUTOWRAP_WORD_SMART")
            new_lines[-2] = ""  # 撤销占位
            new_lines.pop(-2)  # 删掉占位
            replacement_count += 1
        else:
            new_lines.pop(-1)  # 撤销占位
    i += 1

t = "\n".join(new_lines)
p.write_text(t, encoding="utf-8")
print("[fix] 给 %d 个 RichTextLabel 加 autowrap" % replacement_count)

# 3. 如果上面的正则处理不理想，用更简单的替换
t = p.read_text(encoding="utf-8")
if "autowrap_mode" not in t:
    print("[warn] 未成功加 autowrap，改用另一种方式")
    # 更简单：把每个 "bbcode_enabled = true" 后跟换行的，都加 autowrap
    import re
    def repl(m):
        indent = m.group(1)
        return m.group(0) + "\n" + indent + "autowrap_mode = TextServer.AUTOWRAP_WORD_SMART"
    t = re.sub(r"(?m)^(\s*)bbcode_enabled = true$", repl, t)
    p.write_text(t, encoding="utf-8")

# 最终确认
t = p.read_text(encoding="utf-8")
count = t.count("autowrap_mode")
print()
print("autowrap_mode 总数：%d" % count)

print()
print("Godot 完全关闭重开，按 F5")