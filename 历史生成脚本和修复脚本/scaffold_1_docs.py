r"""EmergentWorld scaffold - Part 1/3: 文档、配置、目录。

运行：
    python scaffold_1_docs.py
    python scaffold_1_docs.py --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

FILES: dict[str, str] = {}

FILES["README.md"] = r'''# EmergentWorld

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
'''

FILES["AGENTS.md"] = r'''# AI Coding Agent Guide - EmergentWorld

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
'''

FILES["pyproject.toml"] = r'''[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "emergentworld"
version = "0.1.0"
description = "A generative single-player game with LLM-driven emergent content"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlmodel>=0.0.16",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "openai>=1.30",
    "pyyaml>=6.0",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=8.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "black>=24.4",
    "mypy>=1.10",
]

[tool.setuptools.packages.find]
include = ["server*"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra -q"
'''

FILES[".env.example"] = r'''LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
DB_PATH=data/world.db
CACHE_DIR=.cache/llm
SEED=42
LOG_LEVEL=INFO
'''

FILES[".gitignore"] = r'''__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage

data/*.db
data/*.db-journal
.cache/
.env

.DS_Store
Thumbs.db
'''

FILES[".gitattributes"] = r'''* text=auto
*.py   text eol=lf
*.sh   text eol=lf
*.yaml text eol=lf
*.yml  text eol=lf
*.md   text eol=lf
*.toml text eol=lf
'''

FILES["server/__init__.py"] = '"""EmergentWorld server package."""\n'
FILES["server/models/__init__.py"] = '"""Pydantic schemas and SQLModel tables."""\n'
FILES["server/core/__init__.py"] = '"""Core loop: world, tick, director, evaluator."""\n'
FILES["server/generators/__init__.py"] = '"""LLM-driven content generators."""\n'
FILES["server/systems/__init__.py"] = '"""Rule-based simulation systems."""\n'
FILES["tests/__init__.py"] = '"""Test suite for EmergentWorld."""\n'

DIRS = [
    "server/models", "server/core", "server/generators",
    "server/prompts", "server/systems",
    "content/templates/events", "content/templates/rewards",
    "content/templates/npcs", "content/assets",
    "tools", "tests", "data", ".cache/llm",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"root: {root}")

    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    for rel, content in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            print(f"[skip]  {rel}")
            continue
        p.write_text(content, encoding="utf-8", newline="\n")
        print(f"[write] {rel}")

    print("\nPart 1/3 done.")


if globals().get('__name__') == '__main__':
    main()