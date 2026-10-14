# 单独测智谱 LLM 调用
import asyncio
import time
from pathlib import Path

async def main():
    from server.config import settings
    print("LLM_MODEL: %s" % settings.llm_model)
    print("LLM_BASE_URL: %s" % settings.llm_base_url)
    print("API_KEY 前缀：%s..." % settings.llm_api_key[:8])
    print()

    from server.generators.base import get_llm

    llm = get_llm()

    # 测试 1：简单 JSON
    print("=== 测试 1：简单 JSON 调用 ===")
    t0 = time.time()
    try:
        result = await asyncio.wait_for(
            llm.text_json('返回 JSON：{"ok": true, "msg": "hi"}'),
            timeout=20.0,
        )
        print("成功 (%.1fs): %r" % (time.time() - t0, result))
    except asyncio.TimeoutError:
        print("超时 >20s")
    except Exception as e:
        print("失败 (%.1fs): %s: %s" % (time.time() - t0, type(e).__name__, e))

    # 测试 2：看十秒内有没有拿到完整响应
    print()
    print("=== 测试 2：第二个调用（验证缓存/重试） ===")
    t0 = time.time()
    try:
        result = await asyncio.wait_for(
            llm.text_json('返回 JSON：{"n": 42}'),
            timeout=20.0,
        )
        print("成功 (%.1fs): %r" % (time.time() - t0, result))
    except asyncio.TimeoutError:
        print("超时 >20s")
    except Exception as e:
        print("失败 (%.1fs): %s: %s" % (time.time() - t0, type(e).__name__, e))

    # 测试 3：真实的 fill_event（不带 LLM）
    print()
    print("=== 测试 3：直接调 fill_event（会调 LLM）===")
    from sqlmodel import Session, SQLModel, create_engine
    from server.core.world import create_world, save_npc, save_world
    from server.generators.event import fill_event
    from server.models.schemas import EventTemplate, NPC
    import random

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        world = create_world("t", seed=1)
        save_world(s, world)
        npcs = [
            NPC(id="n1", name="张三", age=30),
            NPC(id="n2", name="李四", age=28),
        ]
        for n in npcs:
            save_npc(s, n)

    tpl = EventTemplate(
        id="test", tags=["daily"], weight=1.0, cooldown=0,
        params={"participant_count": 2},
    )
    t0 = time.time()
    try:
        evt = await asyncio.wait_for(
            fill_event(tpl, world, npcs, random.Random(1)),
            timeout=30.0,
        )
        print("成功 (%.1fs)" % (time.time() - t0))
        print("  summary: %s" % evt.payload.get("summary", "")[:60])
    except asyncio.TimeoutError:
        print("超时 >30s")
    except Exception as e:
        print("失败 (%.1fs): %s: %s" % (time.time() - t0, type(e).__name__, e))


if __name__ == "__main__":
    asyncio.run(main())