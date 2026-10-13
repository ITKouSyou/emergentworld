# EmergentWorld

一个单人可完成的生成式单机游戏。事件、NPC、奖励由模板 + LLM 生成，
NPC 行为由规则系统驱动，世界可离线演化。

## 核心理念

- 模板负责骨架，LLM 负责血肉
- 实时用规则，离线用 LLM
- 所有生成物必须 Schema 校验
- 评估器比生成器更重要

## 快速开始

    python -m venv .venv
    source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
    pip install -e ".[dev]"

    cp .env.example .env               # Windows: copy .env.example .env
    # 编辑 .env 填入 LLM_API_KEY

    python tools/seed_world.py --npc 20
    uvicorn server.main:app --reload

## 测试

    pytest -v

## 离线演化

    python tools/evolve.py --days 30

## 明确不做

- 不做实时 3D 自动建模
- 不做 LLM 实时控制 NPC 行为
- 不做在线自改代码
- 不做微服务 / K8s / 消息队列
