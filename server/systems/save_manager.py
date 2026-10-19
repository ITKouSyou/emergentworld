# 存档系统：复制 .db 文件 + json 元数据
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

from sqlmodel import Session

from server.config import settings
from server.db.session import engine
from server.models.db import PlayerRow, WorldRow

SAVE_DIR = settings.db_path.parent / "saves"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name.strip())
    return name[:64]


def _meta_path(name: str) -> Path:
    return SAVE_DIR / f"{name}.json"


def _db_path(name: str) -> Path:
    return SAVE_DIR / f"{name}.db"


def list_saves() -> list[dict]:
    """列出所有存档（按创建时间倒序）。"""
    result = []
    for f in SAVE_DIR.glob("*.db"):
        name = f.stem
        meta_file = _meta_path(name)
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        result.append({
            "name": name,
            "size": f.stat().st_size,
            "created_at": meta.get("created_at", 0),
            "player_name": meta.get("player_name", "?"),
            "level": meta.get("level", 1),
            "day": meta.get("day", 0),
            "tick": meta.get("tick", 0),
        })
    result.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return result


def create_save(name: str) -> dict:
    """把当前世界保存为一个新存档。"""
    name = _safe_name(name)
    if not name:
        return {"ok": False, "error": "名字不能为空"}

    target_db = _db_path(name)
    target_meta = _meta_path(name)

    # 采集元数据
    meta = {"created_at": time.time(), "name": name}
    with Session(engine) as s:
        world = s.get(WorldRow, "default")
        player = s.get(PlayerRow, "player")
        if world:
            meta["day"] = world.day
            meta["tick"] = world.tick
        if player:
            meta["player_name"] = player.name
            meta["level"] = player.level

    # 确保引擎释放写入锁
    engine.dispose()

    # 复制 db 文件
    if settings.db_path.exists():
        shutil.copy2(settings.db_path, target_db)
    else:
        return {"ok": False, "error": "当前世界数据库不存在"}

    target_meta.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {"ok": True, "name": name, "meta": meta}


def load_save(name: str) -> dict:
    """从存档恢复当前世界。"""
    name = _safe_name(name)
    source_db = _db_path(name)
    if not source_db.exists():
        return {"ok": False, "error": "存档不存在"}

    # 关键：先关闭所有现有连接
    engine.dispose()

    # 备份当前进度（万一读档失败可回滚）
    backup = settings.db_path.parent / f"{settings.db_path.name}.bak"
    if settings.db_path.exists():
        try:
            shutil.copy2(settings.db_path, backup)
        except Exception:
            pass

    # 覆盖主数据库
    shutil.copy2(source_db, settings.db_path)

    return {"ok": True, "name": name}


def delete_save(name: str) -> dict:
    name = _safe_name(name)
    for p in [_db_path(name), _meta_path(name)]:
        if p.exists():
            p.unlink()
    return {"ok": True, "name": name}


def current_save_info() -> dict:
    """返回当前世界的元数据。"""
    with Session(engine) as s:
        world = s.get(WorldRow, "default")
        player = s.get(PlayerRow, "player")
        return {
            "player_name": player.name if player else "?",
            "level": player.level if player else 1,
            "day": world.day if world else 0,
            "tick": world.tick if world else 0,
        }
