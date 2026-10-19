# 为所有 NPC 下载头像（基于 DiceBear）
# 无需任何 API Key，直接从开源 API 下载
from pathlib import Path
import urllib.request
import time

from sqlmodel import Session, create_engine, select

from server.config import settings
from server.models.db import NPCRow

AVATAR_DIR = Path("content/assets/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# 风格选项：adventurer / pixel-art / bottts / lorelei / micah
STYLE = "adventurer"


def download_avatar(npc_id: str, name: str) -> Path:
    target = AVATAR_DIR / f"{npc_id}.png"
    if target.exists():
        return target

    # 种子用名字，保证每次生成一样
    seed = urllib.parse.quote(name)
    url = "https://api.dicebear.com/7.x/%s/png?seed=%s&size=128" % (STYLE, seed)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            target.write_bytes(data)
            print("  [avatar] %s -> %s" % (name, target.name))
            return target
    except Exception as e:
        print("  [avatar] %s 失败：%s" % (name, e))
        return None


def main():
    engine = create_engine(f"sqlite:///{settings.db_path}")
    with Session(engine) as s:
        npcs = s.exec(select(NPCRow)).all()
        print("为 %d 个 NPC 生成头像..." % len(npcs))
        for npc in npcs:
            download_avatar(npc.id, npc.name)
            time.sleep(0.2)  # 防限流
    print("完成。")


if __name__ == "__main__":
    import urllib.parse
    main()
