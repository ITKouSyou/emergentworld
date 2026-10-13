"""经济系统：货币总量、通胀、奖励预算。"""

from __future__ import annotations

from sqlmodel import Session

from server.models.schemas import World


def settle(session: Session, world: World) -> None:
    world.economy.total_currency *= 1.0005
    world.economy.inflation = max(1.0, world.economy.total_currency / 1000.0)
