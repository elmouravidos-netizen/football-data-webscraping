import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"]

app.add_middleware(
CORSMiddleware,
allow_origins=origins,
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

@app.get("/")
def home():
return {"status": "API is running"}

@app.get("/players")
def get_players():
return [
{"name": "Lionel Messi", "team": "Inter Miami"},
{"name": "Cristiano Ronaldo", "team": "Al Nassr"},
{"name": "Kylian Mbappe", "team": "Real Madrid"}
]

@app.get("/matches")
def get_matches():
return [
{
"home_team": "Kansas City Chiefs",
"away_team": "Buffalo Bills",
"score": "27 - 24",
"date": "2026-02-10"
},
{
"home_team": "Dallas Cowboys",
"away_team": "Philadelphia Eagles",
"score": "21 - 17",
"date": "2026-02-09"
},
{
"home_team": "San Francisco 49ers",
"away_team": "Green Bay Packers",
"score": "30 - 14",
"date": "2026-02-08"
}
]

@app.get("/realplayers")
def real_players():
url = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes?limit=20"
headers = {"User-Agent": "Mozilla/5.0"}

```
try:
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()

    players = []
    items = data.get("items", [])

    for athlete in items:
        player = athlete.get("athlete", {})

        players.append({
            "name": player.get("displayName"),
            "position": player.get("position", {}).get("abbreviation", "N/A"),
            "team": player.get("team", {}).get("displayName", "Free Agent")
        })

    return players

except Exception as e:
    return [{"error": str(e)}]
```
