# 修 npc_gen.md 的 prompt 示例
from pathlib import Path

new_prompt = '''你是游戏 NPC 生成器。根据给定的名字与上下文，生成一个 NPC。

**重要：所有文本字段必须使用简体中文。**

规则：
- 输出必须是合法 JSON，符合 NPC Schema
- name 必须使用给定名字：{name}
- gender 必须是 "male" 或 "female"
- traits 使用大五人格：openness, conscientiousness, extraversion, agreeableness, neuroticism
- traits 每个维度必须是 0 到 1 之间的不同数值（不能全 0.5）
- needs 使用：hunger, safety, social, wealth, curiosity
- **goals 必须至少 2 条，用中文写。必须具体、有画面感、独一无二**
  - ❌ 禁止用套话：安稳度日、照顾好家人、过好日子、平平安安
  - ✅ 应该像这样：
    - "攒钱赎回被典当的祖传玉佩"
    - "找到失踪三年的哥哥"
    - "在村东头开一间豆腐坊"
    - "学会用弓箭，赢下秋猎"
  - 一条短期（几周内），一条长期（几年）
- behavior_profile 与 needs 同键，值 0-1
- asset_params 包含 hair, outfit, palette 三个键，值用英文短词
- age 在 18 到 70 之间
- **不要重复他人的 goals，必须与名字/上下文匹配**
- 不要输出 markdown，不要输出解释

名字：{name}
性别提示：{gender}
上下文：{context}
'''

p = Path("server/prompts/npc_gen.md")
p.write_text(new_prompt, encoding="utf-8")
print("[fix] npc_gen.md 重写")
print()
print("现在 prompts 目录：")
for f in sorted(Path("server/prompts").glob("*.md")):
    print("  %s (%d bytes)" % (f.name, f.stat().st_size))