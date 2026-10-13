"""修 main.gd 里 3 处 Variant 推断错误。

- 258 行：var akey := attr_keys[i]
- 278 行：var gender_zh := {...}.get(...)
- 1057 行：var result_zh := {...}.get(...)
"""
from pathlib import Path

p = Path("client/main.gd")
t = p.read_text(encoding="utf-8")

fixes = [
    # 1. akey
    (
        "\t\tvar akey := attr_keys[i]\n",
        "\t\tvar akey: String = str(attr_keys[i])\n",
    ),
    # 2. gender_zh
    (
        '\tvar gender_zh := {"male": "男", "female": "女"}.get(gender_s, "未知")\n',
        '\tvar gender_zh: String = {"male": "男", "female": "女"}.get(gender_s, "未知")\n',
    ),
    # 3. result_zh
    (
        '\t\t\tvar result_zh := {\n'
        '\t\t\t\t"critical": "大成功",\n'
        '\t\t\t\t"success": "成功",\n'
        '\t\t\t\t"partial": "勉强",\n'
        '\t\t\t\t"failure": "失败",\n'
        '\t\t\t}.get(str(check.get("result", "")), "")\n',
        '\t\t\tvar result_zh: String = {\n'
        '\t\t\t\t"critical": "大成功",\n'
        '\t\t\t\t"success": "成功",\n'
        '\t\t\t\t"partial": "勉强",\n'
        '\t\t\t\t"failure": "失败",\n'
        '\t\t\t}.get(str(check.get("result", "")), "")\n',
    ),
]

count = 0
for old, new in fixes:
    if old in t:
        t = t.replace(old, new, 1)
        count += 1
        print("[fix] %s" % old.strip().split("\n")[0][:60])
    else:
        print("[skip] 未匹配：%s" % old.strip().split("\n")[0][:60])

p.write_text(t, encoding="utf-8", newline="\n")
print()
print("共修 %d 处。回到 Godot 按 F5。" % count)