"""RetroAchivements functions for ra_mapper"""

import requests

def download_console_list(file, api_key):
    with open(file, 'wb') as f:
        f.write(requests.get(f"https://retroachievements.org/API/API_GetConsoleIDs.php?y={api_key}").content)

def download_game_list(file, console, api_key):
    with open(file, 'wb') as f:
        f.write(requests.get(f"https://retroachievements.org/API/API_GetGameList.php?i={console}&y={api_key}").content)

def get_game_extended(game_id, api_key):
    return requests.get(f"https://retroachievements.org/API/API_GetGameExtended.php?i={game_id}&y={api_key}").json()
