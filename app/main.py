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
    return {"status": "API is running", "date": "2026-02-16"}

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
url = "https://fbref.com/en/comps/21/stats/NFL-Stats"
headers = {"User-Agent": "Mozilla/5.0"}

```
try:
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    players = []

    table = soup.find("table")
    rows = table.find("tbody").find_all("tr")

    for row in rows[:20]:
        player = row.find("th").text.strip()
        cols = row.find_all("td")

        players.append({
            "name": player,
            "team": cols[2].text.strip() if len(cols) > 2 else "Unknown",
            "position": cols[1].text.strip() if len(cols) > 1 else "N/A"
        })

    return players

except Exception as e:
    return [{"error": str(e)}]
```
