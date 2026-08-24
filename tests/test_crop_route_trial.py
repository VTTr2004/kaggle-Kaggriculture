from tools.crop_route_trial import _ongoing_harvest_routes, _service_assignments


def _observation_with_plants(day: int, plants: dict[tuple[int, int], dict]) -> dict:
    tiles = [[None for _ in range(10)] for _ in range(10)]
    for (x, y), plant in plants.items():
        tiles[y][x] = plant
    return {"day": day, "farms": [{"tiles": tiles}]}


def test_harvest_day_adds_one_extra_worker_per_ready_regrow_route():
    observation = _observation_with_plants(
        10,
        {
            (4, 3): {
                "kind": "PLANT",
                "crop": "TOMATO",
                "planted_day": 0,
                "yield_units": 1,
            },
            (5, 3): {
                "kind": "PLANT",
                "crop": "STRAWBERRY",
                "planted_day": 0,
                "yield_units": 1,
            },
        },
    )

    assert _ongoing_harvest_routes(observation) == (2, 3)
    assert _service_assignments(observation, 8) == (
        (0, True),
        (1, True),
        (2, True),
        (3, True),
        (4, True),
        (5, True),
        (2, False),
        (3, False),
    )
