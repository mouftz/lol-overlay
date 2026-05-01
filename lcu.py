import requests
import urllib3
import time

LOCKFILE_PATH = "/Applications/League of Legends.app/Contents/LoL/lockfile"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_lcu_credentials():
    with open(LOCKFILE_PATH, "r") as f:
        contents = f.read()
    parts = contents.split(":")
    port = parts[2]
    password = parts[3]
    return port, password

def extract_players(session_data):
    players = session_data['myTeam'] + session_data['theirTeam']
    filteredplayers = []
    for p in players:
        filteredplayers.append(
            {
                'name': p['gameName'],
                'tagline': p['tagLine'],
                'puuid': p['puuid']
            }
        )
    return filteredplayers

def get_current_champ_select_players():
    port, password = get_lcu_credentials()
    url = f"https://127.0.0.1:{port}/lol-champ-select/v1/session"
    response = requests.get(url, auth=("riot", password), verify=False)
    
    if response.status_code != 200:
        return None  # not in champ select
    
    return extract_players(response.json())

last_state = None 

while True:
    players = get_current_champ_select_players()
    
    if players and last_state != "in_champ_select":
        print("CHAMP SELECT STARTED!")
        
        # send players to our FastAPI backend
        payload = [{"name": p["name"], "tagline": p["tagline"]} for p in players if p["name"]]
        response = requests.post("http://127.0.0.1:8000/players?region=euw", json=payload)
        
        print("Player stats:")
        for stats in response.json():
            print(f"{stats['name']}#{stats['tagline']} - {stats['rank']} ({stats['winrate']}% WR)")
        
        last_state = "in_champ_select"
        
    elif not players and last_state == "in_champ_select":
        print("Champ select ended.")
        last_state = None
    
    time.sleep(2)