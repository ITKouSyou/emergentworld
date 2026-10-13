"""时间推进。"""

from __future__ import annotations

import random

from sqlmodel import Session

from server.core import director
from server.core.world import save_world
from server.models.schemas import World
from server.systems import behavior, economy, weather


def tick(session: Session, world: World) -> None:
    rng = random.Random(world.seed * 99991 + world.tick)

    behavior.step(session, world)
    economy.settle(session, world)
    director.decay_tension(world)
    weather.update_weather(world, rng)

    world.hour += 1
    if world.hour >= 24:
        world.hour = 0
        world.day += 1
        world.social_count_today = 0
    world.tick += 1

    save_world(session, world)
