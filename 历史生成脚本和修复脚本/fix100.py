# 修 autowrap_mode：加上变量名前缀
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")
lines = t.split("\n")

new_lines = []
count = 0
for i, line in enumerate(lines):
    stripped = line.lstrip()
    if stripped.startswith("autowrap_mode ="):
        # 看前一行找变量名
        indent = line[:len(line) - len(line.lstrip())]
        var_name = ""
        for j in range(i - 1, max(0, i - 4), -1):
            prev = lines[j].strip()
            if ".bbcode_enabled = true" in prev:
                var_name = prev.split(".bbcode_enabled")[0].strip()
                break
        if var_name:
            new_line = indent + var_name + "." + stripped
            new_lines.append(new_line)
            count += 1
            print("[fix] 行 %d: %s" % (i + 1, new_line.strip()[:70]))
        else:
            new_lines.append(line)
            print("[warn] 行 %d 找不到变量名，跳过" % (i + 1))
    else:
        new_lines.append(line)

t = "\n".join(new_lines)
p.write_text(t, encoding="utf-8")
print()
print("共修 %d 处" % count)

# 再检查是否还有残留
t2 = p.read_text(encoding="utf-8")
remaining = [i + 1 for i, line in enumerate(t2.split("\n"))
             if line.lstrip().startswith("autowrap_mode =")]
if remaining:
    print("[warn] 还有 %r 处未修" % remaining)
else:
    print("[ok] 全部修复")

print()
print("Godot 完全关闭重开，按 F5")