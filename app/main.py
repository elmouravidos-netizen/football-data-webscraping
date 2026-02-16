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
    # FIXED: This block must also be indented!
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
import requests
from bs4 import BeautifulSoup

@app.get("/realplayers")
def real_players():
url = "https://www.espn.com/nfl/freeagents"

```
headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")

players = []

for row in soup.select("tbody tr")[:10]:
    cols = row.find_all("td")
    if len(cols) > 1:
        name = cols[0].text.strip()
        position = cols[1].text.strip()

        players.append({
            "name": name,
            "position": position
        })

return players
```
