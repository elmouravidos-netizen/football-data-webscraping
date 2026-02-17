import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import os
import uvicorn

app = FastAPI(title="Multi-Sport API (NFL & Football)")

# 1. CORS Setup for your React App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

# 2. 2026 Bypass Headers (Crucial for SofaScore)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.sofascore.com",
    "Origin": "https://www.sofascore.com"
}

@app.get("/")
def health():
    return {"status": "Active", "sports": ["NFL", "Football"], "date": date.today().isoformat()}

# --- SECTION 1: FOOTBALL (SOCCER) ---

@app.get("/football/matches")
def get_football_matches():
    """Fetches real-time soccer results for today."""
    today = date.today().isoformat()
    url = f"https://api.sofascore.com{today}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        matches = []
        for event in data.get("events", []):
            matches.append({
                "id": event.get("id"),
                "league": event.get("tournament", {}).get("name"),
                "home_team": event.get("homeTeam", {}).get("name"),
                "away_team": event.get("awayTeam", {}).get("name"),
                "home_score": event.get("homeScore", {}).get("current", 0),
                "away_score": event.get("awayScore", {}).get("current", 0),
                "status": event.get("status", {}).get("description"),
                "home_logo": f"https://api.sofascore.app{event['homeTeam']['id']}/image",
                "away_logo": f"https://api.sofascore.app{event['awayTeam']['id']}/image"
            })
        return matches
    except:
        return {"error": "Failed to fetch matches"}

@app.get("/football/standings/premier-league")
def get_pl_standings():
    """Fetches Premier League Table using IDs from your screenshot (17 / 76986)."""
    url = "https://api.sofascore.com"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        # Navigate to the correct 'standings' index
        rows = data.get("standings", [{}])[0].get("rows", [])
        table = []
        for row in rows:
            table.append({
                "rank": row.get("position"),
                "team": row.get("team", {}).get("name"),
                "logo": f"https://api.sofascore.app{row['team']['id']}/image",
                "played": row.get("matches"),
                "gd": row.get("scoresFor", 0) - row.get("scoresAgainst", 0),
                "points": row.get("points")
            })
        return table
    except:
        return {"error": "Failed to fetch standings"}

@app.get("/football/rankings")
def get_fifa_rankings():
    """Fetches Top 20 FIFA World Rankings."""
    url = "https://api.sofascore.com"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        return [{"rank": t.get("rowNumber"), "team": t.get("team", {}).get("name"), "points": t.get("points")} for t in data.get("rankings", [])[:20]]
    except:
        return {"error": "Failed to fetch rankings"}

# --- SECTION 2: NFL (AMERICAN FOOTBALL) ---

@app.get("/nfl/players")
def get_nfl_players():
    url = "https://site.web.api.espn.com"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return [{"name": a['athlete']['displayName'], "team": a['athlete'].get('team', {}).get('displayName', 'Free Agent')} for a in data.get("items", [])]
    except:
        return {"error": "Failed to fetch NFL players"}

# --- RAILWAY RUNNER ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
