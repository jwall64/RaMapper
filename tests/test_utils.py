from ra_mapper.utils import normalize_name, str_distance, parse_ra_name

import pytest


@pytest.mark.parametrize(
    "raw, normalized",
    [ 
        # Real Titles
        ("Chrono Trigger", "chrono trigger"),
        ("Portal 2", "portal 2"),
        ("The Legend of Zelda: Ocarina of Time", "the legend of zelda ocarina of time"),
        ("Harvest Moon 64", "harvest moon 64"),
        ("Super Smash Bros. Melee", "super smash bros melee"),
     
        # Theoretical Titles
        ("Test™ Game", "test game"),
        ("Test® Game: Deluxe (Nintendo Switch 2 Edition) + Test® DLC", "test game deluxe nintendo switch 2 edition test dlc")
    ]
)
def test_normalize_name(raw, normalized):
    assert normalize_name(raw) == normalized


@pytest.mark.parametrize(
    "str1, str2, expected_distance",
    [
        ("Hello", "Hello", 0),
        ("World", "World", 0),
        ("Hello", "World", 4),
        ("World", "Hello", 4),
        ("World", "Worl", 1),
        ("World", "Wor", 2),
        ("World", "Wo", 3),
        ("World", "W", 4),
        ("World", "", 5),
        ("World", "d", 4),
        ("World", "ld", 3),
        ("World", "rld", 2),
        ("World", "orld", 1),
        ("Hello", "", 5),
    ]
)
def test_str_distance(str1, str2, expected_distance):
    assert str_distance(str1, str2) == expected_distance


@pytest.mark.parametrize(
    "unparsed, expected_title, expected_subset, expected_tags",
    [
        # Real Titles 
        ("Super Mario Galaxy", "Super Mario Galaxy", "", ""),
        ("Super Mario Galaxy 2", "Super Mario Galaxy 2", "", ""),
        ("~Hack~ Super Mario Galaxy 63", "Super Mario Galaxy 63", "", ["Hack"]),
        ("~Homebrew~ ~Demo~ Super Mario Galaxy DS", "Super Mario Galaxy DS", "", ["Homebrew", "Demo"]),
        ("Super Mario Galaxy [Subset - Coin Collector]", "Super Mario Galaxy", "Coin Collector", []),
        ("Super Mario Galaxy 2 [Subset - Time Attack]", "Super Mario Galaxy 2", "Time Attack", []),

        # Theorecial Titles (Do not exist in the database, but titles with similar form could exist, and they should be valid)
        ("~Tag~ And Title [Subset - And Subset]", "And Title", "And Subset", ["Tag"]),
        ("Title[With Brackets]", "Title[With Brackets]", "", []),
        ("Title[With Brackets] [And more brackets]", "Title[With Brackets] [And more brackets]", "", []),
        ("Title[With Brackets] [Subset - And Subset]", "Title[With Brackets]", "And Subset", []),
        ("Title[With Brackets] [And more brackets] [Subset - And Subset]", "Title[With Brackets] [And more brackets]", "And Subset", []),
        ("~One Tag~ ~Two Tags~ ~Three Tags~ Title[With Brackets] [And more brackets] [Subset - And Subset]", "Title[With Brackets] [And more brackets]", "And Subset", [ "One Tag", "Two Tags", "Three Tags" ])
    ]
)
def test_parse_ra_name(unparsed, expected_title, expected_subset, expected_tags):
    title, subset, tags = parse_ra_name(unparsed)
    assert title == expected_title
    assert subset == expected_subset
    assert len(tags) == len(expected_tags)

    for i in range(len(expected_tags)):
        assert tags[i] == expected_tags[i]


