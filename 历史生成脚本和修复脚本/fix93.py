# 确保 /item API 返回 category
from pathlib import Path

p = Path("server/main.py")
t = p.read_text(encoding="utf-8")

# 找 _row_to_item 函数
start = t.find("def _row_to_item(")
if start < 0:
    print("[fail] 找不到 _row_to_item")
    raise SystemExit(1)

end = t.find("\n\ndef ", start + 1)
if end < 0:
    end = t.find("\n@app", start + 1)
if end < 0:
    end = len(t)

body = t[start:end]
print("--- 当前 _row_to_item ---")
print(body)

# 检查是否有 category
if "category" in body:
    print()
    print("[ok] _row_to_item 已含 category")
else:
    print()
    print("[!] _row_to_item 缺少 category，插入")

    # 在 return 字典末尾（"consumed": ... 那行的后面）加 category
    import re
    # 找 consumed 行
    m = re.search(r'(\s+"consumed":\s*r\.consumed,\s*\n)', body)
    if m:
        indent = "        "
        insert = (
            indent + '"category": getattr(r, "category", "material") or "material",\n'
            + indent + '"slot": getattr(r, "slot", "") or "",\n'
        )
        body_new = body[:m.end()] + insert + body[m.end():]
        t = t[:start] + body_new + t[end:]
        p.write_text(t, encoding="utf-8")
        print("[fix] 已插入 category + slot 字段")
    else:
        print("[fail] 找不到 consumed 行，手动加：")
        print('    "category": getattr(r, "category", "material") or "material",')