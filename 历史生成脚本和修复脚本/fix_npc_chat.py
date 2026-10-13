"""修 npc_chat.md 的 JSON 花括号转义问题。

在 str.format() 里，字面量花括号必须写成 {{ 和 }}，
否则会被当成占位符，导致 KeyError。
"""
from pathlib import Path

NEW_CONTENT = r'''你是游戏里两个 NPC 对话的生成器。

**所有输出必须是简体中文，并输出为合法 JSON。**

结构：
{{"topic": "话题主题（4-8 字）", "lines": [{{"speaker": "名字", "text": "台词"}}, ...]}}

规则：
- lines 里 2 到 4 句对话，双方轮流说话
- 每句不超过 40 字
- 台词符合角色性格与目标
- speaker 必须使用真实名字（{name_a} 或 {name_b}）
- 不要输出 markdown，不要输出解释

场景：
  地点：{location}
  两人关系：{relation}

角色 A：{name_a}
  目标：{goals_a}

角色 B：{name_b}
  目标：{goals_b}
'''

p = Path("server/prompts/npc_chat.md")
if not p.exists():
    print("找不到 server/prompts/npc_chat.md")
    raise SystemExit(1)

p.write_text(NEW_CONTENT, encoding="utf-8", newline="\n")
print("[fix] server/prompts/npc_chat.md 已修正")

# 顺便扫描其它 prompt 文件是否有类似问题
print()
print("扫描其它 prompt 文件...")
import re

prompt_dir = Path("server/prompts")
for f in sorted(prompt_dir.glob("*.md")):
    text = f.read_text(encoding="utf-8")
    # 找未被 {{ 或 }} 包住的孤立 {xxx} 作为 .format 字段名（排除 {{）
    # 简化检查：找出所有单 { 单 } 的实例
    single_open = len(re.findall(r'(?<!\{)\{(?!\{)', text))
    single_close = len(re.findall(r'(?<!\})\}(?!\})', text))
    # 允许的字段名占位（在文件名里可能合法）
    # 简单报告
    if single_open != single_close:
        print("  [!] %s  单{=%d  单}=%d  （可能不平衡）" % (f.name, single_open, single_close))
    else:
        print("  [ok] %s  单{=%d" % (f.name, single_open))

print()
print("再跑：pytest -v")