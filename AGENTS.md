# AI Coding Agent Guide - EmergentWorld

> 本文档面向 AI 编码助手。读完后应能理解项目意图、做设计规划、
> 写代码、跑起来、做测试。

## 项目意图

不是全自动宇宙，而是：

    模板 + 规则 + LLM + 评估器 + 离线演化

四条铁律：

1. 模板负责骨架，LLM 只填肉。
2. 实时用规则，离线用 LLM。
3. 所有生成物必须 Schema 校验。
4. 没有评估器的生成系统 = 垃圾制造机。

## 明确禁止

- LLM 实时控制 NPC 行为
- 3D 实时自动建模
- 在线自改代码
- 微服务 / K8s / Redis / 消息队列
- 重型前端框架
- 无法 Schema 校验的自由文本
- 游戏主循环里同步调用 LLM

## 技术栈

Python 3.11+ / FastAPI / SQLModel / Pydantic v2 / SQLite /
OpenAI SDK / pytest / ruff / black / mypy / Godot 4（客户端）

## 实现顺序

1. models/schemas.py + models/db.py
2. core/world.py + core/tick.py
3. tools/seed_world.py
4. generators/base.py
5. generators/npc.py + prompts/npc_gen.md
6. systems/behavior.py
7. systems/relationship.py + systems/memory.py
8. core/director.py + generators/event.py
9. core/evaluator.py
10. generators/reward.py + systems/economy.py
11. API
12. tools/evolve.py
13. Godot 客户端

每一步必须先写测试，再写实现。

## LLM 调用规范

- 统一封装 generators/base.py::LLMClient
- 必须带 JSON Schema 约束
- 必须可缓存（key = prompt hash + model）
- 必须在 evaluator 中校验
- 失败必须降级为模板默认值
- 必须异步，不得阻塞 tick

## 评估器三层

1. 规则层：实体存在、时间合法、奖励预算、无矛盾
2. LLM 层：抽样评审，评分 1-5
3. 日志层：被拒生成物写入 evaluation 表

## 测试规范

- 所有 LLM 调用必须 mock
- 无网络可运行
- pytest + pytest-asyncio
- 核心模块覆盖率 >= 70%
- 所有随机支持 seed 参数

## 常见坑

1. LLM 返回非法 JSON：校验 + 重试 + 降级
2. LLM 阻塞 tick：异步或预生成
3. 奖励通胀：走预算函数
4. 记忆矛盾：生成前检索记忆
5. 事件节奏失控：Director 维护张力
6. 内容重复：cooldown + 标签多样性
7. 评估器缺失：必然崩
8. 过早做 3D：MVP 禁止
9. 过早做多人：禁止
10. 在线自改代码：禁止

## 完成标准

有 Schema、有单测（mock LLM）、有降级、有日志、
通过 ruff + mypy、不阻塞主循环、可复现（固定种子）。
