from sqlmodel import Session, SQLModel, create_engine

from server.models.db import ItemRow, dumps
from server.systems import inventory


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def _mk_item(session, item_id: str, owner: str = "") -> ItemRow:
    row = ItemRow(
        id=item_id,
        reward_id="rwd_x",
        event_id="evt_x",
        name="旧怀表",
        kind="饰物",
        affixes_json=dumps(["磨损的"]),
        story="x",
        value=0.3,
        owner_id=owner,
    )
    session.add(row)
    session.commit()
    return row


def test_give_and_list():
    engine = _engine()
    with Session(engine) as s:
        _mk_item(s, "itm_1", owner="")
        inventory.give_item(s, "itm_1", "npc_a")
        rows = inventory.list_items_by_owner(s, "npc_a")
        assert len(rows) == 1
        assert rows[0].id == "itm_1"


def test_take_item_to_player():
    engine = _engine()
    with Session(engine) as s:
        _mk_item(s, "itm_2", owner="npc_b")
        inventory.give_item(s, "itm_2", "player")
        rows = inventory.list_items_by_owner(s, "player")
        assert len(rows) == 1


def test_consume_hides_item():
    engine = _engine()
    with Session(engine) as s:
        _mk_item(s, "itm_3", owner="player")
        inventory.consume_item(s, "itm_3")
        rows = inventory.list_items_by_owner(s, "player")
        assert len(rows) == 0
        rows_all = inventory.list_items_by_owner(s, "player", include_consumed=True)
        assert len(rows_all) == 1
