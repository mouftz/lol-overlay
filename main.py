from fastapi import FastAPI
import httpx
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
import urllib3
import time
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

_cache = {}

def cache_get(key):
    """Return cached value if not expired, else None."""
    if key in _cache:
        value, expiry = _cache[key]
        if time.time() < expiry:
            return value
        else:
            del _cache[key]  # expired, clean up
    return None

def cache_set(key, value, ttl_seconds):
    """Store value in cache with expiry."""
    _cache[key] = (value, time.time() + ttl_seconds)

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

async def get_recent_matches(puuid: str, region: str, queue_id: int, count: int = 10):
    cache_key = f"matches:{puuid}:{region}:{queue_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    headers = {"X-Riot-Token": API_KEY}
    
    async with httpx.AsyncClient() as client:
        valid_queues = {420, 440, 400, 450}
        if queue_id in valid_queues:
            ids_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue_id}&count={count}"
        else:
            ids_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
        
        ids_response = await client.get(ids_url, headers=headers)
        
        if ids_response.status_code != 200:
            return {"results": [], "winrate": 0.0}
        
        match_ids = ids_response.json()
        
        if not match_ids:
            empty = {"results": [], "winrate": 0.0}
            cache_set(cache_key, empty, ttl_seconds=600)
            return empty
        
        match_calls = [
            client.get(f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}", headers=headers)
            for match_id in match_ids
        ]
        match_responses = await asyncio.gather(*match_calls)
        
        results = []
        for resp in match_responses:
            if resp.status_code != 200:
                continue
            data = resp.json()
            if 'info' not in data:
                continue
            participants = data['info']['participants']
            me = next((p for p in participants if p['puuid'] == puuid), None)
            if me is not None:
                results.append(me['win'])
        
        wins = sum(1 for r in results if r)
        winrate = round((wins / len(results)) * 100, 1) if results else 0.0
        
        result = {"results": results, "winrate": winrate}
        cache_set(cache_key, result, ttl_seconds=600)  # 10 min
        return result

async def get_player_info_solo(summoner_name: str, tagline: str, platform: str, region: str, queue_id: int = 420):
    # Cache key includes everything that affects the result
    cache_key = f"player:{summoner_name}:{tagline}:{region}:{queue_id}"
    
    # Check cache first
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    
    headers = {"X-Riot-Token": API_KEY}
    
    async with httpx.AsyncClient() as client:
        puuidurl = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}"
        puuidraw = await client.get(puuidurl, headers=headers)
        
        if puuidraw.status_code != 200:
            unknown = {
                'name': summoner_name, 'tagline': tagline, 'rank': 'Unknown',
                'lp': 0, 'wins': 0, 'losses': 0, 'winrate': 0.0,
                'recent_matches': {"results": [], "winrate": 0.0}
            }
            return unknown  # don't cache errors
        
        puuid = puuidraw.json()['puuid']
        
        statsurl = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        statsraw = await client.get(statsurl, headers=headers)
        
        if statsraw.status_code != 200:
            unknown = {
                'name': summoner_name, 'tagline': tagline, 'rank': 'Unknown',
                'lp': 0, 'wins': 0, 'losses': 0, 'winrate': 0.0,
                'recent_matches': {"results": [], "winrate": 0.0}
            }
            return unknown
        
        stats = statsraw.json()
    
    solo_entries = [e for e in stats if e['queueType'] == 'RANKED_SOLO_5x5']

    if not stats or not solo_entries:
        result = {
            'name': summoner_name, 'tagline': tagline, 'rank': 'Unranked',
            'lp': 0, 'wins': 0, 'losses': 0, 'winrate': 0.0,
            'recent_matches': await get_recent_matches(puuid, region, queue_id)
        }
        cache_set(cache_key, result, ttl_seconds=300)  # 5 min
        return result
    
    solo_duo = solo_entries[0]
    rank = str(solo_duo['tier']) + ' ' + str(solo_duo['rank'])
    lp = solo_duo['leaguePoints']
    wins = solo_duo['wins']
    losses = solo_duo['losses']
    winrate = (wins/(wins+losses)) * 100
    matches = await get_recent_matches(puuid, region, queue_id)

    result = {
        'name': summoner_name,
        'tagline': tagline,
        'rank': rank,
        'lp': lp,
        'wins': wins,
        'losses': losses,
        'winrate': round(winrate, 1),
        'recent_matches': matches
    }
    cache_set(cache_key, result, ttl_seconds=300)  # 5 min
    return result

class Player(BaseModel):
    name: str
    tagline: str

@app.post("/players")
async def get_players(players: list[Player], region: str = "na", queue_id: int = 420):
    region_map = {
        "na": ("na1", "americas"),
        "euw": ("euw1", "europe"),
    }
    platform, riot_region = region_map[region]
    
    calls = [get_player_info_solo(p.name, p.tagline, platform, riot_region, queue_id) for p in players]
    results = await asyncio.gather(*calls)
    return results

def get_lcu_region():
    """Detect which region the running League client is on."""
    try:
        port, password = get_lcu_credentials()
        url = f"https://127.0.0.1:{port}/riotclient/region-locale"
        response = httpx.get(url, auth=("riot", password), verify=False)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        # data['region'] is e.g. 'NA', 'EUW', 'KR', etc.
        return data['region'].lower()
    except Exception:
        return None
    
def get_gameflow_phase():
    """Get the current LCU gameflow phase (Lobby, ChampSelect, InProgress, etc)."""
    try:
        port, password = get_lcu_credentials()
        url = f"https://127.0.0.1:{port}/lol-gameflow/v1/gameflow-phase"
        response = httpx.get(url, auth=("riot", password), verify=False, timeout=2.0)
        
        if response.status_code != 200:
            return None
        
        return response.json()
    except Exception:
        return None

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
        queue_id = data.get('queueId', 0)  
        
        player_list = [
            {"name": p['gameName'], "tagline": p['tagLine']}
            for p in players if p['gameName']
        ]
        
        return {"players": player_list, "queue_id": queue_id} 
     except (FileNotFoundError, Exception):
        return None

def get_live_game_data():
    """Fetch live in-game data. Returns None if not in a game."""
    try:
        gamestats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
        playerlist_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
        
        gamestats_resp = httpx.get(gamestats_url, verify=False, timeout=2.0)
        if gamestats_resp.status_code != 200:
            return None
        
        playerlist_resp = httpx.get(playerlist_url, verify=False, timeout=2.0)
        if playerlist_resp.status_code != 200:
            return None
        
        gamestats = gamestats_resp.json()
        playerlist = playerlist_resp.json()
        
        live_players = {}
        for p in playerlist:
            key = f"{p['riotIdGameName']}#{p['riotIdTagLine']}"
            live_players[key] = {
                "champion": p['championName'],
                "level": p['level'],
                "kills": p['scores']['kills'],
                "deaths": p['scores']['deaths'],
                "assists": p['scores']['assists'],
                "cs": p['scores']['creepScore'],
                "items": [item['displayName'] for item in p.get('items', [])],
                "team": p['team'],
                "is_dead": p['isDead'],
                "respawn_timer": p['respawnTimer'],
                "is_bot": p['isBot'],
            }
        
        return {
            "game_time": gamestats['gameTime'],
            "game_mode": gamestats['gameMode'],
            "players": live_players
        }
    except (httpx.ConnectError, httpx.TimeoutException):
        return None
    except Exception:
        return None

@app.get("/champ-select")
async def champ_select(region: str = None):
    if region is None:
        region = get_lcu_region() or "na"
    
    region_map = {
        "na": ("na1", "americas"),
        "euw": ("euw1", "europe"),
        "kr": ("kr", "asia"),
        "eune": ("eun1", "europe"),
    }
    
    if region not in region_map:
        return {"state": "idle", "players": [], "region": region, "error": f"Unsupported region: {region}"}
    
    platform, riot_region = region_map[region]
    phase = get_gameflow_phase()
    
    if phase == "InProgress":
        live = get_live_game_data()
        
        if live is None:
            # Loading screen — game launched but Live Client API isn't up yet.
            cs_result = get_champ_select_players()
            if cs_result:
                cs_players = cs_result["players"]
                queue_id = cs_result["queue_id"]
                calls = [get_player_info_solo(p["name"], p["tagline"], platform, riot_region, queue_id) for p in cs_players]
                results = await asyncio.gather(*calls)
                return {
                    "state": "loading",
                    "players": results,
                    "region": region,
                    "queue_id": queue_id
                }
            # No champ-select so just idle
            return {"state": "loading", "players": [], "region": region}
        
        # Game actually running 
        return {"state": "in_game", "players": [], "region": region, "game_time": live["game_time"]}
    
    if phase == "ChampSelect":
        cs_result = get_champ_select_players()
        if cs_result:
            cs_players = cs_result["players"]
            queue_id = cs_result["queue_id"]
            calls = [get_player_info_solo(p["name"], p["tagline"], platform, riot_region, queue_id) for p in cs_players]
            results = await asyncio.gather(*calls)
            return {
                "state": "champ_select",
                "players": results,
                "region": region,
                "queue_id": queue_id
            }
    
    return {"state": "idle", "players": [], "region": region}

@app.get("/live-game")
def live_game():
    """Fetch live in-game data from the Live Client API."""
    try:
        # Live Client API runs on a fixed port, no auth, self-signed cert
        gamestats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
        playerlist_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
        
        gamestats_resp = httpx.get(gamestats_url, verify=False, timeout=2.0)
        if gamestats_resp.status_code != 200:
            return {"in_game": False}
        
        playerlist_resp = httpx.get(playerlist_url, verify=False, timeout=2.0)
        if playerlist_resp.status_code != 200:
            return {"in_game": False}
        
        gamestats = gamestats_resp.json()
        playerlist = playerlist_resp.json()
        
        live_players = {}
        for p in playerlist:
            key = f"{p['riotIdGameName']}#{p['riotIdTagLine']}"
            live_players[key] = {
                "champion": p['championName'],
                "level": p['level'],
                "kills": p['scores']['kills'],
                "deaths": p['scores']['deaths'],
                "assists": p['scores']['assists'],
                "cs": p['scores']['creepScore'],
                "items": [item['displayName'] for item in p.get('items', [])],
                "team": p['team'],  # "ORDER" or "CHAOS"
                "is_dead": p['isDead'],
                "respawn_timer": p['respawnTimer'],
                "is_bot": p['isBot'],
            }
        
        return {
            "in_game": True,
            "game_time": gamestats['gameTime'],
            "game_mode": gamestats['gameMode'],
            "players": live_players
        }
    except (httpx.ConnectError, httpx.TimeoutException):
        # Not in a game — Live Client API isn't running
        return {"in_game": False}
    except Exception as e:
        return {"in_game": False, "error": str(e)}