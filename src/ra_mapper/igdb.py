"""IGDB functions for ra_mapper"""

import os
import time

import requests
import csv

from .utils import now_millis

class IgdbPlatform:
    def __init__(self, platformId: int, name: str, slug: str, abbreviation: str):
        self.id = platformId
        self.name = name
        self.slug = slug
        self.abbreviation = abbreviation


class IgdbGame:
    def __init__(self, gameId: int, title: str, platforms: list[IgdbPlatform]):
        self.gameId = gameId
        self.title = title
        self.platforms = platforms


def signin_igdb(client_id, client_secret) -> str:

    access_token_url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"

    response = requests.post(access_token_url)
    response.raise_for_status()

    return response.json()["access_token"]


def scrape_to_csv(outputFile: str, client_id: str, access_token: str, resource: str, fields: list[str], where: str | None = None):

    if os.path.exists(outputFile):
        modify_time = os.path.getmtime(outputFile) * 1000
        if now_millis() - modify_time <= (1000 * 60 * 60 * 24):
            return

    highest_id = 0
    try:
        with open(outputFile, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, fieldnames=fields)
            header = next(reader)

            for row in reader:
                next_id = int(row["id"])
                if next_id > highest_id:
                    highest_id = next_id

    except FileNotFoundError:
        pass


    data_exists = os.path.exists(outputFile) and os.path.getsize(outputFile) > 0


    with open(outputFile, mode='a', newline='', encoding='utf-8') as f:
   
        writer = csv.DictWriter(f, fieldnames=fields)
        
        if not data_exists:
            writer.writeheader()

        while True:
            url = f"https://api.igdb.com/v4/{resource}"
            payload = f"fields {','.join(fields)}; limit 500; where id > {highest_id}"
            if not (where is None):
                payload += f" & {where}"

            payload += "; sort id asc;"
            
            headers = {
                "Client-ID": client_id,
                "Authorization": f"Bearer {access_token}"
            }

            response = requests.post(url, data=payload, headers=headers)
            json = response.json()

            if not json:
                break

            for obj in json:
                writer.writerow(obj)

            highest_id = json[-1]["id"]

            time.sleep(0.50)
