import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import os
import uvicorn

app = FastAPI(title="Multi-Sport API (NFL & Football)")

# --- PROFESSIONAL CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# 2026 Bypass Headers (Crucial for SofaScore)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.sofascore.com/",
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
    # FIXED: Added the full API path and required slashes
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        matches = []
        for event in data.get("events", []):
            home_id = event['homeTeam']['id']
            away_id = event['awayTeam']['id']
            matches.append({
                "id": event.get("id"),
                "league": event.get("tournament", {}).get("name"),
                "home_team": event.get("homeTeam", {}).get("name"),
                "away_team": event.get("awayTeam", {}).get("name"),
                "home_score": event.get("homeScore", {}).get("current", 0),
                "away_score": event.get("awayScore", {}).get("current", 0),
                "status": event.get("status", {}).get("description"),
                "home_logo": f"https://api.sofascore.app{home_id}/image",
                "away_logo": f"https://api.sofascore.app{away_id}/image"
                
            })
        return matches
    except Exception as e:
        return {"error": f"Match fetch failed: {str(e)}"}

# --- SECTION 2: NFL ---

@app.get("/nfl/players")
def get_nfl_players():
    # FIXED: Added correct full endpoint for NFL athletes
    url = "https://site.web.api.espn.com"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return [{"name": a['athlete']['displayName'], "team": a['athlete'].get('team', {}).get('displayName', 'Free Agent')} for a in data.get("items", [])]
    except Exception as e:
        return {"error": f"Failed to fetch NFL players: {str(e)}"}

# --- RAILWAY DEPLOYMENT SETUP ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Binding to 0.0.0.0 is required for external access on Railway
    uvicorn.run(app, host="0.0.0.0", port=port)
