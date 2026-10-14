from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

problems = 0
for i, line in enumerate(t.split("\n")):
    s = line.lstrip()
    # 顶格的 api. 行
    if s.startswith("api.") and line == s and ".connect(" in s:
        print("[孤儿] 行 %d: %s" % (i+1, line[:80]))
        problems += 1
    # 顶格的缩进可疑行
    if line.startswith("    ") and not line.startswith("\t"):
        if s and not s.startswith("#"):
            # 4 空格缩进（可能和 Tab 混用）
            if i > 0:
                prev = t.split("\n")[i-1]
                if prev.startswith("\t"):
                    print("[混用] 行 %d: %s" % (i+1, line[:80]))
                    problems += 1

if problems == 0:
    print("[ok] 没发现问题")