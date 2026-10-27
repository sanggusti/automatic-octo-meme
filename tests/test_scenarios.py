from dmb.scenarios import build_samples, list_scenarios, load_scenario, world_hash


def test_all_five_scenarios_load():
    assert sorted(list_scenarios()) == [
        "earthquake",
        "flash_flood",
        "flood",
        "forest_fire",
        "landslide",
        "tsunami",
    ]
    for name in list_scenarios():
        config = load_scenario(name)
        assert config.grid["width"] > 0


def test_samples_are_deterministic():
    first = build_samples("forest_fire", seeds=[7])
    second = build_samples("forest_fire", seeds=[7])
    assert first[0].metadata == second[0].metadata
    assert first[0].metadata["world_hash"] == world_hash(
        "forest_fire", 7, first[0].metadata["victim_placements"]
    )


def test_distinct_seeds_differ():
    a = build_samples("forest_fire", seeds=[1])[0].metadata["world_hash"]
    b = build_samples("forest_fire", seeds=[2])[0].metadata["world_hash"]
    assert a != b
