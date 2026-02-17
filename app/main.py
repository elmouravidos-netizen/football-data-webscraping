import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "API is running", "current_date": "2026-02-17"}

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
        {"home_team": "Kansas City Chiefs", "away_team": "Buffalo Bills", "score": "27-24", "date": "2026-02-10"},
        {"home_team": "Dallas Cowboys", "away_team": "Philadelphia Eagles", "score": "21-17", "date": "2026-02-09"},
        {"home_team": "San Francisco 49ers", "away_team": "Green Bay Packers", "score": "30-14", "date": "2026-02-08"}
    ]

@app.get("/realplayers")
def real_players():
    url = "https://fbref.com"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        players = []

        # Find the specific NFL stats table
        table = soup.find("table", {"id": "stats_standard"})
        if not table:
            return [{"error": "Stats table not found on FBref"}]

        rows = table.find("tbody").find_all("tr")
        for row in rows[:20]:
            # Skip the middle header rows FBref adds
            if "thead" in row.get("class", []):
                continue
                
            name_cell = row.find("td", {"data-stat": "player"})
            team_cell = row.find("td", {"data-stat": "team"})
            pos_cell = row.find("td", {"data-stat": "pos"})

            if name_cell:
                players.append({
                    "name": name_cell.text.strip(),
                    "team": team_cell.text.strip() if team_cell else "N/A",
                    "position": pos_cell.text.strip() if pos_cell else "N/A"
                })
        return players
    except Exception as e:
        return [{"error": f"Scraping failed: {str(e)}"}]
