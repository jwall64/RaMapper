import json


class SystemOverride:
    def __init__(self, igdb: list[int], is_engine: bool):
        self.igdb = igdb
        self.is_engine = is_engine


class GameOverride:
    def __init__(self, igdb: int):
        self.igdb = igdb


class SubsetOverride:
    def __init__(self, games: list[int]):
        self.games = games


def _load_systems(override_list) -> dict[int,SystemOverride]:
    out = {}
    for obj in override_list:
        ra_id = int(obj["ra"])
        igdb_id = int(obj["igdb"])
        engine = "engine" in obj and obj["engine"]

        if ra_id in out:
            out[ra_id].igdb.append(igdb_id)
        else:
            out[ra_id] = SystemOverride([igdb_id], engine)
    return out


def _load_games(override_list) -> dict[int,GameOverride]:
    out = {}
    for obj in override_list:
        ra_id = int(obj["ra"])
        igdb_id = int(obj["igdb"])

        if ra_id in out:
            raise ValueError(f"2+ overrides exist for game: {ra_id}")
        else:
            out[ra_id] = GameOverride(igdb_id)
    return out


def _load_subsets(override_list) -> dict[int,SubsetOverride]:
    out = {}
    for obj in override_list:
        ra_id = int(obj["ra"])
        parent_id = int(obj["igdb"])

        if ra_id in out:
            out[ra_id].games.append(parent_id)
        else:
            out[ra_id] = SubsetOverride([parent_id])
    return out


def load_overrides(file) -> tuple[dict[int, SystemOverride],dict[int, GameOverride], dict[int,SubsetOverride]]:
    try: 
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)

            systems = _load_systems(data.get("systems", []))
            games = _load_games(data.get("games", []))
            subsets = _load_subsets(data.get("subsets", []))

            return systems, games, subsets

    except FileNotFoundError:
        print(f"Overrides file {file} not found")

    except json.JSONDecodeError as e:
        print(f"An error occurred while parsing the overrides file ({file}): {e}")

    return {}, {}, {}
        

