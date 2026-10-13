"""嵌入客户端：把文本转成向量。

未配置 EMBEDDING_API_KEY 时，返回空向量（[]），
调用方应回退到其它检索方式。
"""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache

from openai import AsyncOpenAI

from server.config import settings


def _hash_fallback(text: str, dim: int = 64) -> list[float]:
    """无 embedding 服务时的确定性哈希向量。

    用于测试和极端兜底。词义相似度很差，但至少能跑通流程。
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec: list[float] = []
    for i in range(dim):
        b = h[i % len(h)]
        vec.append((b / 255.0) * 2.0 - 1.0)
    return vec


class EmbeddingClient:
    def __init__(self) -> None:
        self.enabled = settings.embedding_enabled
        self.model = settings.embedding_model
        if self.enabled:
            self.client = AsyncOpenAI(
                api_key=settings.embedding_api_key,
                base_url=settings.embedding_base_url,
            )
        else:
            self.client = None

    async def embed(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            return []
        if not self.enabled or self.client is None:
            return _hash_fallback(text)
        try:
            resp = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return list(resp.data[0].embedding)
        except Exception:
            return _hash_fallback(text)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def serialize(vec: list[float]) -> str:
    return json.dumps(vec, ensure_ascii=False)


def deserialize(s: str) -> list[float]:
    if not s:
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [float(x) for x in v]
    except Exception:
        pass
    return []


@lru_cache(maxsize=1)
def get_embedding() -> EmbeddingClient:
    return EmbeddingClient()
