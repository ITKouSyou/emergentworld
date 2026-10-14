# 修 _cleanup_http 的切片语法
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")

old = '''func _cleanup_http() -> void:
	var http_children: Array = []
	for c in get_children():
		if c is HTTPRequest:
			http_children.append(c)
	if http_children.size() > 15:
		for old_http in http_children[:http_children.size() - 5]:
			if is_instance_valid(old_http):
				old_http.queue_free()'''

new = '''func _cleanup_http() -> void:
	var http_children: Array = []
	for c in get_children():
		if c is HTTPRequest:
			http_children.append(c)
	if http_children.size() > 15:
		var keep_from := http_children.size() - 5
		for i in range(0, keep_from):
			var old_http = http_children[i]
			if is_instance_valid(old_http):
				old_http.queue_free()'''

if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("[fix] _cleanup_http 去掉切片语法")
else:
    # 尝试直接用函数名重写
    start = t.find("func _cleanup_http() -> void:")
    if start >= 0:
        end = t.find("\n\n", start + 1)
        if end < 0:
            end = len(t)
        t = t[:start] + new + t[end:]
        p.write_text(t, encoding="utf-8")
        print("[fix] _cleanup_http 强制重写")
    else:
        print("[skip] 找不到 _cleanup_http")

# 顺便扫一下 api.gd 里还有没有切片语法
t2 = p.read_text(encoding="utf-8")
import re
slices = []
for i, line in enumerate(t2.split("\n")):
    if re.search(r"\w+\[[^\]]*:[^\]]*\]", line) and "[url" not in line:
        slices.append((i+1, line.strip()))

if slices:
    print()
    print("[warn] 还有 %d 处疑似切片语法：" % len(slices))
    for ln, l in slices[:5]:
        print("  行 %d: %s" % (ln, l[:80]))
else:
    print()
    print("[ok] 没有切片语法")