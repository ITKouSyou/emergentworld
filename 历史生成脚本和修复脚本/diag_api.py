# 打印 api.gd 关键区域
from pathlib import Path

p = Path("client/api.gd")
t = p.read_text(encoding="utf-8")
lines = t.split("\n")

print("总行数：%d" % len(lines))
print()

# 找 _cleanup_http
i = t.find("func _cleanup_http")
if i >= 0:
    start_line = t[:i].count("\n") + 1
    end = t.find("\nfunc ", i + 1)
    if end < 0:
        end = len(t)
    end_line = t[:end].count("\n") + 1
    print("=== _cleanup_http (行 %d-%d) ===" % (start_line, end_line))
    print(t[i:end])
    print()
else:
    print("[!] 找不到 _cleanup_http")

# 找 _on_response 里加的日志
i = t.find("func _on_response")
if i >= 0:
    start_line = t[:i].count("\n") + 1
    end = t.find("\nfunc ", i + 1)
    if end < 0:
        end = len(t)
    end_line = t[:end].count("\n") + 1
    print("=== _on_response (行 %d-%d) ===" % (start_line, end_line))
    print(t[i:end])
    print()

# 找 _request
i = t.find("func _request")
if i >= 0:
    start_line = t[:i].count("\n") + 1
    end = t.find("\nfunc ", i + 1)
    if end < 0:
        end = len(t)
    end_line = t[:end].count("\n") + 1
    print("=== _request (行 %d-%d) ===" % (start_line, end_line))
    print(t[i:end])

# 全文件扫切片语法
import re
print()
print("=== 疑似切片语法 ===")
found = False
for i, line in enumerate(lines):
    # 匹配 [数字:数字] 或 [expr:expr] 但不含 http:// 之类
    if re.search(r"\[\s*\w[^\]:]*\s*:\s*[^\]]*\]", line) and "://" not in line and "[url" not in line:
        print("行 %d: %s" % (i+1, line.strip()[:100]))
        found = True
if not found:
    print("(无)")