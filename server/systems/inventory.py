"""物品归属系统：给予 / 拿回 / 查询。"""

from __future__ import annotations

from sqlmodel import Session, select

from server.models.db import ItemRow, loads


PLAYER_OWNER = "player"
NO_OWNER = ""


def get_item_row(session: Session, item_id: str) -> ItemRow | None:
    return session.get(ItemRow, item_id)


def give_item(session: Session, item_id: str, owner_id: str) -> ItemRow | None:
    row = session.get(ItemRow, item_id)
    if row is None:
        return None
    row.owner_id = owner_id
    session.add(row)
    session.commit()
    return row


def drop_item(session: Session, item_id: str) -> ItemRow | None:
    """丢弃：设为无主。"""
    return give_item(session, item_id, NO_OWNER)


def consume_item(session: Session, item_id: str) -> ItemRow | None:
    row = session.get(ItemRow, item_id)
    if row is None:
        return None
    row.consumed = True
    session.add(row)
    session.commit()
    return row


def list_items_by_owner(
    session: Session,
    owner_id: str,
    include_consumed: bool = False,
) -> list[ItemRow]:
    stmt = select(ItemRow).where(ItemRow.owner_id == owner_id)
    if not include_consumed:
        stmt = stmt.where(ItemRow.consumed == False)  # noqa: E712
    return list(session.exec(stmt).all())


def list_all_items(session: Session, include_consumed: bool = False) -> list[ItemRow]:
    stmt = select(ItemRow)
    if not include_consumed:
        stmt = stmt.where(ItemRow.consumed == False)  # noqa: E712
    return list(session.exec(stmt).all())


def row_to_dict(row: ItemRow) -> dict:
    return {
        "id": row.id,
        "reward_id": row.reward_id,
        "event_id": row.event_id,
        "name": row.name,
        "kind": row.kind,
        "affixes": loads(row.affixes_json) or [],
        "story": row.story,
        "value": row.value,
        "owner_id": row.owner_id,
        "consumed": row.consumed,
        "durability": getattr(row, "durability", 100),
        "max_durability": getattr(row, "max_durability", 100),
    }
