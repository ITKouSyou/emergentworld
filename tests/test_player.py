import random

from sqlmodel import Session, SQLModel, create_engine

from server.systems import player as player_sys


def _engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_create_player():
    engine = _engine()
    with Session(engine) as s:
        p = player_sys.create_player(s, "张铁柱", "male", "山里来的猎户")
        assert p.name == "张铁柱"
        assert p.gender == "male"
        assert p.created is True
        # 猎户给 strength +1, agility +2
        assert p.attributes["strength"] == 6
        assert p.attributes["agility"] == 7


def test_exp_and_level():
    engine = _engine()
    with Session(engine) as s:
        player_sys.create_player(s, "测试", "female")
        p, leveled = player_sys.add_exp(s, 150)
        assert leveled is True
        assert p.level == 2
        assert p.unspent_points == 2


def test_allocate_point():
    engine = _engine()
    with Session(engine) as s:
        p = player_sys.create_player(s, "测试", "female")
        # 给点经验升级
        player_sys.add_exp(s, 150)
        ok, err, p = player_sys.allocate_point(s, "strength", 1)
        assert ok, err
        assert p.attributes["strength"] == 6
        assert p.unspent_points == 1


def test_roll_check_success_and_failure():
    from server.models.schemas import Player
    p = Player(id="player", name="测试", attributes={
        "strength": 5, "agility": 5, "intelligence": 5,
        "perception": 5, "charisma": 5, "luck": 5,
    })
    # 全成功率：属性 20 + 骰子 10 = 30，远高于阈值
    p_strong = p.model_copy(update={"attributes": {**p.attributes, "strength": 20}})
    r = player_sys.roll_check(p_strong, "strength", "normal", random.Random(1))
    assert r["result"] in ("success", "critical")

    # 全失败率：属性 1，骰子最多 10，总 11 < 15 常见
    p_weak = p.model_copy(update={"attributes": {**p.attributes, "strength": 1}})
    r2 = player_sys.roll_check(p_weak, "strength", "heroic", random.Random(1))
    assert r2["result"] in ("partial", "failure")
