import random

from server.models.schemas import World
from server.systems import weather


def test_season_for_day_cycles():
    assert weather.season_for_day(0) == "spring"
    assert weather.season_for_day(7) == "summer"
    assert weather.season_for_day(14) == "autumn"
    assert weather.season_for_day(21) == "winter"
    assert weather.season_for_day(28) == "spring"


def test_update_weather_changes_season():
    world = World(id="w", seed=1, day=0, season="spring")
    rng = random.Random(1)
    weather.update_weather(world, rng)
    assert world.season == "spring"
    world.day = 7
    weather.update_weather(world, rng)
    assert world.season == "summer"


def test_update_weather_picks_from_season_pool():
    world = World(id="w", seed=1, day=7, season="summer", tick=100)
    world.weather_changed_tick = 0
    rng = random.Random(1)
    weather.update_weather(world, rng)
    allowed = set(weather.WEATHER_WEIGHTS["summer"].keys())
    assert world.weather in allowed
