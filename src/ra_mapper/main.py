"""Entrypoint for ra_mapper"""

import os
import sys
import time

from .config import load_overrides
from .db import DatabaseConnection
from .igdb import signin_igdb, scrape_to_csv
from .ra import download_console_list, download_game_list
from .mapper import attempt_game_mapping, attempt_system_mapping
from .utils import now_millis

def main() -> None:

    TEMP_DIR = "working"

    RA_API_KEY = os.getenv("RA_API_KEY")
    IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
    IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")

    assert(not (RA_API_KEY is None))
    assert(not (IGDB_CLIENT_ID is None))
    assert(not (IGDB_CLIENT_SECRET is None))

    conn = DatabaseConnection("ra.db")

    o_systems, o_games, o_subsets = load_overrides("overrides.json")

    access_token = signin_igdb(IGDB_CLIENT_ID, IGDB_CLIENT_SECRET)

    scrape_to_csv(f"{TEMP_DIR}/platforms.csv", IGDB_CLIENT_ID, access_token, "platforms", ["id","abbreviation","name"])
    scrape_to_csv(f"{TEMP_DIR}/game_engines.csv", IGDB_CLIENT_ID, access_token, "game_engines", ["id","name"])
    download_console_list(f"{TEMP_DIR}/consoles.json", RA_API_KEY)

    print("Attempting system mapping...")
    attempt_system_mapping(f"{TEMP_DIR}/platforms.csv", f"{TEMP_DIR}/game_engines.csv", f"{TEMP_DIR}/consoles.json", conn, o_systems)

    cursor = conn.cursor()
    cursor.execute("SELECT id, is_active, is_game_system FROM system")
    for row in cursor.fetchall():

        if not row[1] or not row[2]:
            continue

        cursor.execute("SELECT igdb_system.igdb_id, igdb_system.is_engine FROM system_mapping JOIN igdb_system ON igdb_system_id = igdb_system.id WHERE system_id = ?1", [row[0]])

        for mapping in cursor.fetchall():

            print(f"Attempting game mapping for {row[0]} -> {mapping[0]}_{mapping[1]}")

            igdb_csv = f"{TEMP_DIR}/games_{mapping[0]}_{mapping[1]}.csv"
            ra_json = f"{TEMP_DIR}/games_{row[0]}.json"

            where = f"game_engines = [{mapping[0]}]" if mapping[1] == 1 else f"platforms = [{mapping[0]}]"
            scrape_to_csv(igdb_csv, IGDB_CLIENT_ID, access_token, "games", ["id","name"], where)


            modify_time = 0 
            if os.path.exists(ra_json):
                modify_time = os.path.getmtime(ra_json) * 1000

            now = now_millis()
            if now - modify_time > (1000 * 60 * 60 * 24):
                cursor.execute("UPDATE system SET fetched_at = ?1 WHERE id = ?2", [ now, row[0] ])
                download_game_list(ra_json, row[0], RA_API_KEY)
            else:
                cursor.execute("UPDATE system SET fetched_at = ?1 WHERE id = ?2", [ modify_time, row[0] ])

            attempt_game_mapping(igdb_csv, ra_json, row[0], RA_API_KEY, conn, o_games, o_subsets)

            time.sleep(1.0)

if __name__ == "__main__":
    main()
