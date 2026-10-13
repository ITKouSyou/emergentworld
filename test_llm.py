import asyncio
import traceback

from server.generators.base import get_llm


async def main():
    llm = get_llm()
    try:
        result = await llm.text_json('返回 JSON：{"ok": true, "message": "hello"}')
        print("成功：", result)
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())