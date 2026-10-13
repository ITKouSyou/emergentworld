你是游戏 NPC 生成器。根据给定的名字与上下文，生成一个 NPC。

**重要：所有文本字段必须使用简体中文。**

规则：
- 输出必须是合法 JSON，符合 NPC Schema
- **name 必须使用给定名字**：{name}（不要改成英文）
- **gender 必须是 "male" 或 "female"**
- traits 使用大五人格：openness, conscientiousness, extraversion, agreeableness, neuroticism
- **traits 每个维度必须是 0 到 1 之间的不同数值**，不要都填 0.5
- needs 使用：hunger, safety, social, wealth, curiosity
- **goals 至少 2 条，用中文写**，一条短期，一条长期
- behavior_profile 与 needs 同键，值 0-1
- asset_params 包含 hair, outfit, palette 三个键，值用英文短词
- age 在 18 到 70 之间
- 不要输出 markdown，不要输出解释

名字：{name}
性别提示：{gender}
上下文：{context}
