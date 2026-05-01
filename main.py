from fastapi import FastAPI
import httpx
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = os.getenv("RIOT_API_KEY")
LOCKFILE_PATH = "/Applications/League of Legends.app/Contents/LoL/lockfile"

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"message": "server is running"}

@app.get("/player/{summoner_name}/{tagline}")
async def get_player(summoner_name: str, tagline: str, region: str = "na"):
    region_map = {
        "na": ("na1", "americas"),
        "euw": ("euw1", "europe"),
    }
    platform, riot_region = region_map[region]
    return await get_player_info_solo(summoner_name, tagline, platform, riot_region)

async def get_player_info_solo(summoner_name: str, tagline: str, platform: str, region: str):
    headers = {"X-Riot-Token": API_KEY}
    
    async with httpx.AsyncClient() as client:
        puuidurl = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}"
        puuidraw = await client.get(puuidurl, headers=headers)
        puuid = puuidraw.json()['puuid']
        
        statsurl = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        statsraw = await client.get(statsurl, headers=headers)
        stats = statsraw.json()
    
    solo_entries = [e for e in stats if e['queueType'] == 'RANKED_SOLO_5x5']

    if not stats or not solo_entries:
        return {
            'name': summoner_name,
            'tagline': tagline,
            'rank': 'Unranked',
            'lp': 0,
            'wins': 0,
            'losses': 0,
            'winrate': 0.0
        }
    
    solo_duo = solo_entries[0]
    rank = str(solo_duo['tier']) + ' ' + str(solo_duo['rank'])
    lp = solo_duo['leaguePoints']
    wins = solo_duo['wins']
    losses = solo_duo['losses']
    winrate = (wins/(wins+losses)) * 100

    return{
        'name':summoner_name,
        'tagline': tagline,
        'rank': rank,
        'lp': lp,
        'wins': wins,
        'losses': losses,
        'winrate': round(winrate,1)
    }

class Player(BaseModel):
    name: str
    tagline: str

@app.post("/players")
async def get_players(players: list[Player], region: str = "na"):
    region_map = {
        "na": ("na1", "americas"),
        "euw": ("euw1", "europe"),
    }
    platform, riot_region = region_map[region]
    
    calls = [get_player_info_solo(p.name, p.tagline, platform, riot_region) for p in players]
    results = await asyncio.gather(*calls)
    return results

def get_lcu_credentials():
    with open(LOCKFILE_PATH, "r") as f:
        contents = f.read()
    parts = contents.split(":")
    return parts[2], parts[3]

def get_champ_select_players():
    try:
        port, password = get_lcu_credentials()
        url = f"https://127.0.0.1:{port}/lol-champ-select/v1/session"
        response = httpx.get(url, auth=("riot", password), verify=False)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        players = data['myTeam'] + data['theirTeam']
        return [
            {"name": p['gameName'], "tagline": p['tagLine']}
            for p in players if p['gameName']
        ]
    except (FileNotFoundError, Exception):
        return None

@app.get("/champ-select")
async def champ_select(region: str = "na"):
    players = get_champ_select_players()
    if not players:
        return {"in_champ_select": False, "players": []}
    
    region_map = {
        "na": ("na1", "americas"),
        "euw": ("euw1", "europe"),
    }
    platform, riot_region = region_map[region]
    
    calls = [get_player_info_solo(p["name"], p["tagline"], platform, riot_region) for p in players]
    results = await asyncio.gather(*calls)
    
    return {"in_champ_select": True, "players": results}