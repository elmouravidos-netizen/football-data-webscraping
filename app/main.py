import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import os
import uvicorn

app = FastAPI(title="Multi-Sport API (NFL & Football)")

# --- PROFESSIONAL CORS CONFIGURATION ---
# This allows your Vercel app and local testing to communicate with Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all domains to connect (Best for development/Vercel)
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# 2026 Bypass Headers (Crucial for SofaScore)
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
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
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
    except Exception as e:
        return {"error": f"Match fetch failed: {str(e)}"}

@app.get("/football/matches")
def get_football_matches():
    """Fetches real-time soccer results for today."""
    today = date.today().isoformat()
    # FIXED URL: Added a slash '/' after .com
    url = f"https://api.sofascore.com{today}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
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
    except Exception as e:
        return {"error": f"Match fetch failed: {str(e)}"}

# --- SECTION 2: NFL ---

@app.get("/nfl/players")
def get_nfl_players():
    url = "https://site.web.api.espn.com"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        return [{"name": a['athlete']['displayName'], "team": a['athlete'].get('team', {}).get('displayName', 'Free Agent')} for a in data.get("items", [])]
    except:
        return {"error": "Failed to fetch NFL players"}

# --- RAILWAY DEPLOYMENT SETUP ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Using 0.0.0.0 is required for Railway to expose the port to the internet
    uvicorn.run(app, host="0.0.0.0", port=port)
