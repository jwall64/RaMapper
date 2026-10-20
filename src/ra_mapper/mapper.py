"""Helpers for mapping IGDB objects to RetroAchievements objects"""

import json
import csv

from .ra import get_game_extended
from .utils import normalize_name, now_millis, parse_ra_date, parse_ra_name, str_distance
from .config import SystemOverride, GameOverride, SubsetOverride

def attempt_system_mapping(igdb_platform_csv, igdb_engine_csv, ra_json, connection, overrides: dict[int, SystemOverride] = {}):

    cursor = connection.cursor()

    with open(igdb_platform_csv, mode='r', newline='', encoding='utf-8') as igdb_platform_file, \
         open(igdb_engine_csv, mode='r', newline='', encoding='utf-8') as igdb_engine_file, \
         open(ra_json, mode='r', encoding='utf-8') as ra_file:

        console_list = json.load(ra_file)
        for console in console_list:

            ra_id = console["ID"]

            ra_og_name = console["Name"]
            ra_active = console["Active"]
            ra_system = console["IsGameSystem"]

            if not ra_system:
                continue

            cursor.execute("""
INSERT INTO system (id, name, is_active, is_game_system, fetched_at) 
VALUES (?1, ?2, ?3, ?4, ?5) 
ON CONFLICT (id) DO 
UPDATE SET name = ?2, is_active = ?3, is_game_system = ?4;
                """,
                [ ra_id, ra_og_name, ra_active, ra_system, 0 ]
            )

            if ra_id in overrides:
                for o in overrides[ra_id].igdb:

                    if o == -1:
                        continue

                    cursor.execute("""
INSERT INTO igdb_system (igdb_id, is_engine) 
VALUES (?1, ?2) 
ON CONFLICT (igdb_id, is_engine) DO 
UPDATE SET igdb_id = excluded.igdb_id
RETURNING id;
                        """,
                        [ o, overrides[ra_id].is_engine ]
                    )
                    db_id = cursor.fetchone()[0]

                    cursor.execute("""
INSERT INTO system_mapping (system_id, igdb_system_id) 
VALUES (?1, ?2) 
ON CONFLICT (system_id, igdb_system_id) DO NOTHING;
                        """,
                        [ ra_id, db_id ]
                    )
            else:

                ra_names = [normalize_name(name) for name in ra_og_name.split('/')]
                for ra_name in ra_names:

                    igdb_platform_file.seek(0)
                    reader = csv.DictReader(igdb_platform_file, ["id","abbreviation","name"])
                    header = next(reader)

                    for row in reader:
                        igdb_id = row["id"]
                        igdb_abs = [normalize_name(ab) for ab in row["abbreviation"].split('/')]
                        igdb_names = [normalize_name(name) for name in row["name"].split('/')]

                        all_names = [name for name in igdb_names]
                        if len(igdb_abs) > 0 and len(igdb_abs[0]) > 0:
                            all_names.extend([ab for ab in igdb_abs])

                        distances = [str_distance(ra_name, name) for name in all_names]
                        min_distance = min(distances)
                        
                        if min_distance == 0:
                            print(f"Found a match: {ra_name} = {igdb_names[0]}")

                            cursor.execute("""
INSERT INTO igdb_system (igdb_id, is_engine) 
VALUES (?1, 0) 
ON CONFLICT (igdb_id, is_engine) DO 
UPDATE SET igdb_id = excluded.igdb_id
RETURNING id;
                            """,
                                [ igdb_id ]
                            )
                            db_id = cursor.fetchone()[0]

                            cursor.execute("""
INSERT INTO system_mapping (system_id, igdb_system_id) 
VALUES (?1, ?2) 
ON CONFLICT (system_id, igdb_system_id) DO NOTHING;
                                """,
                                [ ra_id, db_id ]
                            )
                    
                    igdb_engine_file.seek(0)
                    reader = csv.DictReader(igdb_engine_file, ["id","name"])
                    header = next(reader)

                    for row in reader:
                        igdb_id = row["id"]
                        igdb_names = [normalize_name(name) for name in row["name"].split('/')]

                        all_names = [name for name in igdb_names]

                        distances = [str_distance(ra_name, name) for name in all_names]
                        min_distance = min(distances)

                        if min_distance == 0:
                            print(f"Found a match: {ra_name} = {igdb_names[0]}")

                            cursor.execute("""
INSERT INTO igdb_system (igdb_id, is_engine) 
VALUES (?1, 1) 
ON CONFLICT (igdb_id, is_engine) DO
UPDATE SET igdb_id = excluded.igdb_id
RETURNING id;
                            """,
                                [ igdb_id ]
                            )
                            db_id = cursor.fetchone()[0]

                            cursor.execute("""
INSERT INTO system_mapping (system_id, igdb_system_id) 
VALUES (?1, ?2) 
ON CONFLICT (system_id, igdb_system_id) DO NOTHING;
                                """,
                                [ ra_id, db_id ]
                            )

        connection.commit()



def _handle_subset(cursor, system_id, ra_id, ra_title, ra_subset, ra_updated, prev_ra_id, prev_ra_title):
    if prev_ra_title == ra_title:
        cursor.execute(
            "INSERT INTO subset_parent (subset_id, game_id) VALUES (?,?) ON CONFLICT (subset_id, game_id) DO NOTHING;",
            [ ra_id, prev_ra_id ]
        )
    else:
        cursor.execute("SELECT id FROM game WHERE title=?1 AND system_id=?2;", [ra_title, system_id])
        parent_row = cursor.fetchone()
        if parent_row is None:

            if " | " in ra_title:
                print(f"{ra_title} might have multiple titles")
                success = True
                for title in ra_title.split(" | "):
                    success = success and _handle_subset(cursor, system_id, ra_id, title, ra_subset, ra_updated, prev_ra_id, prev_ra_title)
                return success

            return False

        cursor.execute(
            "INSERT INTO subset_parent (subset_id, game_id) VALUES (?,?) ON CONFLICT (subset_id, game_id) DO NOTHING;",
            [ ra_id, parent_row[0] ]
        )

    return True



def attempt_game_mapping(igdb_csv, ra_json, system_id, api_key, connection, overrides: dict[int, GameOverride] = {}, subset_overrides: dict[int, SubsetOverride] = {}):
    
    cursor = connection.cursor()

    with open(igdb_csv, mode='r', newline='', encoding='utf-8') as igdb_file, \
         open(ra_json, mode='r', encoding='utf-8') as ra_file:

        game_list = json.load(ra_file)

        prev_ra_id = None
        prev_ra_title = None

        for game in game_list:
            ra_id = game["ID"]
            ra_raw_title = game["Title"]

            ra_title, ra_subset, ra_tags = parse_ra_name(ra_raw_title)

            if "Z" in ra_tags:
                continue

            ra_normalized_title = normalize_name(ra_title)
            ra_updated = parse_ra_date(game["DateModified"])

            if ra_updated is None:
                ra_updated = 0


            if not (ra_subset is None) and len(ra_subset) > 0:

                cursor.execute(
                    "INSERT INTO subset (id, name, updated_at) VALUES (?,?,?) ON CONFLICT (id) DO NOTHING;",
                    [ ra_id, ra_subset, ra_updated ]
                )
                if ra_id in subset_overrides:
                    for o in subset_overrides[ra_id].games:
                        if o == -1:
                            continue
                        cursor.execute(
                            "INSERT INTO subset_parent (subset_id, game_id) VALUES (?,?) ON CONFLICT (subset_id, game_id) DO NOTHING;",
                            [ ra_id, o ]
                        )
                else: 
                    if not _handle_subset(cursor, system_id, ra_id, ra_title, ra_subset, ra_updated, prev_ra_id, prev_ra_title):
                        print(f"WARNING: Unable to find parent for subset: {ra_raw_title} ({ra_id}) Attempting to fetch from RA...")

                        extended = get_game_extended(ra_id, api_key)
                        parent_id = extended["ParentGameID"]

                        if parent_id is None:
                            print(f"WARNING: No ParentGameID in extended details for subset: {ra_raw_title} ({ra_id})")
                            continue

                        cursor.execute(
                            "INSERT INTO subset_parent (subset_id, game_id) VALUES (?,?) ON CONFLICT (subset_id, game_id) DO NOTHING;",
                            [ ra_id, parent_id ]
                        )

            else:  
                cursor.execute(
                    "INSERT INTO game (id, system_id, title, updated_at) VALUES (?,?,?,?) ON CONFLICT (id) DO NOTHING;",
                    [ ra_id, system_id, ra_title, ra_updated ]
                )
                if ra_id in overrides:
                    o = overrides[ra_id].igdb
                    if o == -1:
                        continue
                    cursor.execute(
                        "INSERT INTO game_mapping (game_id, igdb_id) VALUES (?,?) ON CONFLICT (game_id, igdb_id) DO NOTHING;",
                        [ ra_id, o ]
                    )
                prev_ra_id = ra_id
                prev_ra_title = ra_title


                igdb_file.seek(0)
                reader = csv.DictReader(igdb_file, ["id","name"])
                header = next(reader)

                for row in reader:
                    igdb_id = row["id"]
                    igdb_name = normalize_name(row["name"])

                    if igdb_name == ra_normalized_title:
                        cursor.execute(
                            "INSERT INTO game_mapping (game_id, igdb_id) VALUES (?,?) ON CONFLICT (game_id, igdb_id) DO NOTHING;",
                            [ ra_id, igdb_id ]
                        )

        connection.commit()
