"""LLM 客户端封装。异步、可缓存、强制 JSON Schema。"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from server.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = settings.llm_model
        self.cache_dir = settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 缓存 ----------

    def _cache_key(self, prompt: str, schema_name: str) -> str:
        h = hashlib.sha256(f"{self.model}|{schema_name}|{prompt}".encode())
        return h.hexdigest()

    def _cache_get(self, key: str) -> Any | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _cache_set(self, key: str, data: Any) -> None:
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 调用 ----------

    async def _call_raw(self, prompt: str, schema_json: dict | None = None) -> str:
        """调用 LLM。使用 openai client 自带 timeout，避免 tenacity+asyncio 死锁。"""
        import time as _time
        t0 = _time.time()
        print("[llm] 开始调用 len=%d" % len(prompt))
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a game content generator. "
                            "Always answer with valid JSON. "
                            "No prose, no markdown fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.9,
                timeout=30.0,
            )
            content = resp.choices[0].message.content or "{}"
            print("[llm] 完成 %.1fs len=%d" % (_time.time() - t0, len(content)))
            return content
        except Exception as e:
            print("[llm] 失败 %.1fs: %s: %s" % (
                _time.time() - t0, type(e).__name__, str(e)[:120]))
            raise

    async def text(self, prompt: str) -> str:
        """纯文本调用。"""
        import time as _time
        t0 = _time.time()
        print("[llm.text] 开始 len=%d" % len(prompt))
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                timeout=30.0,
            )
            content = resp.choices[0].message.content or ""
            print("[llm.text] 完成 %.1fs" % (_time.time() - t0))
            return content
        except Exception as e:
            print("[llm.text] 失败 %.1fs: %s" % (_time.time() - t0, type(e).__name__))
            raise

    async def _call_raw(self, prompt: str) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a game content generator. "
                        "Always answer with valid JSON. "
                        "No prose, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},  # 固定为 json_object
            temperature=0.9,
        )
        return resp.choices[0].message.content or "{}"

    async def json(
        self,
        prompt: str,
        schema: type[T],
        *,
        fallback: T | None = None,
    ) -> T:
        key = self._cache_key(prompt, schema.__name__)
        cached = self._cache_get(key)
        if cached is not None:
            try:
                return schema.model_validate(cached)
            except Exception:
                pass
        try:
            raw = await self._call_raw(prompt)
            data = json.loads(raw)
            obj = schema.model_validate(data)
            self._cache_set(key, obj.model_dump())
            return obj
        except Exception:
            if fallback is not None:
                return fallback
            raise

    async def text_json(self, prompt: str) -> Any:
        key = self._cache_key(prompt, "text_json")
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        raw = await self._call_raw(prompt)
        data = json.loads(raw)
        self._cache_set(key, data)
        return data

    async def text(self, prompt: str) -> str:
        resp = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
            ),
            timeout=25.0,
        )
        return resp.choices[0].message.content or ""


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


def load_prompt(name: str) -> str:
    import sys
    # 判断是不是打包后的 exe 环境
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
        # 尝试几个可能的位置（onedir 模式下数据可能在 _internal 里）
        for try_path in [
            base_dir / "server" / "prompts" / name,
            base_dir / "_internal" / "server" / "prompts" / name,
            base_dir / "prompts" / name
        ]:
            if try_path.exists():
                return try_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Prompt not found: {name}")
    else:
        # 开发环境
        path = Path("server/prompts") / name
        return path.read_text(encoding="utf-8")


def reset_llm() -> None:
    """重置 LLM 单例，用于前端修改 API Key 后刷新客户端。"""
    global _llm
    _llm = None
