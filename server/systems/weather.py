"""季节与天气系统。"""

from __future__ import annotations

import random

from server.models.schemas import World

SEASONS = ["spring", "summer", "autumn", "winter"]
DAYS_PER_SEASON = 7

WEATHER_KINDS = ["clear", "rain", "fog", "snow", "storm"]

WEATHER_WEIGHTS: dict[str, dict[str, int]] = {
    "spring": {"clear": 4, "rain": 3, "fog": 1},
    "summer": {"clear": 5, "rain": 2, "storm": 1},
    "autumn": {"clear": 3, "fog": 3, "rain": 2},
    "winter": {"snow": 4, "fog": 2, "clear": 2},
}

WEATHER_DURATION_TICKS = 6


def season_for_day(day: int) -> str:
    idx = (day // DAYS_PER_SEASON) % len(SEASONS)
    return SEASONS[idx]


def _weighted_choice(weights: dict[str, int], rng: random.Random) -> str:
    total = sum(weights.values())
    r = rng.random() * total
    acc = 0.0
    for k, w in weights.items():
        acc += w
        if r <= acc:
            return k
    return next(iter(weights))


def update_weather(world: World, rng: random.Random) -> bool:
    """根据季节与时间更新天气。返回是否发生变化。"""
    new_season = season_for_day(world.day)
    season_changed = new_season != world.season
    world.season = new_season

    if world.tick - world.weather_changed_tick < WEATHER_DURATION_TICKS:
        return season_changed

    weights = WEATHER_WEIGHTS.get(world.season, {"clear": 1})
    new_weather = _weighted_choice(weights, rng)
    if new_weather != world.weather:
        world.weather = new_weather
        world.weather_changed_tick = world.tick
        return True
    world.weather_changed_tick = world.tick
    return False
