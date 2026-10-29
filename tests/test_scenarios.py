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


def test_brief_states_grid_bounds():
    from dmb.scenarios import build_samples

    sample = build_samples("forest_fire", seeds=[1])[0]
    assert "10x10" in sample.input
    assert "x=0..9, y=0..9" in sample.input
    assert "(0, 0)" in sample.input


def test_time_of_day_axis():
    import pytest

    from dmb.scenarios import build_samples

    sample = build_samples("flood", seeds=[2], time_of_day="night")[0]
    assert sample.id == "flood-seed-2-night"
    assert sample.metadata["time_of_day_active"] == "night"
    both = build_samples("forest_fire", seeds=[1], weather="clear", time_of_day="dusk")[0]
    assert both.id == "forest_fire-seed-1-clear-dusk"
    with pytest.raises(ValueError, match="time_of_day"):
        build_samples("flood", seeds=[2], time_of_day="eclipse")


def test_bands_cover_easy_medium_hard():
    from dmb.scenarios import build_samples, list_scenarios

    bands = set()
    for scenario in list_scenarios():
        for sample in build_samples(scenario, seeds=list(range(1, 31))):
            bands.add(sample.metadata["difficulty_score"]["band"])
    assert bands == {"easy", "medium", "hard"}
