import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import os
import uvicorn

app = FastAPI(title="Multi-Sport API (NFL & Football)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOFA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com"
}

ESPN_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


@app.get("/")
def health():
    return {"status": "Active", "sports": ["NFL", "Football"], "date": date.today().isoformat()}


# --- SECTION 1: FOOTBALL (SOCCER) ---
@app.get("/football/matches")
def get_football_matches():
    today = date.today().isoformat()
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
    try:
        r = requests.get(url, headers=SOFA_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        matches = []
        for event in data.get("events", []):
            home_id = event["homeTeam"]["id"]
            away_id = event["awayTeam"]["id"]
            matches.append({
                "id": event.get("id"),
                "league": event.get("tournament", {}).get("name"),
                "home_team": event.get("homeTeam", {}).get("name"),
                "away_team": event.get("awayTeam", {}).get("name"),
                "home_score": event.get("homeScore", {}).get("current", 0),
                "away_score": event.get("awayScore", {}).get("current", 0),
                "status": event.get("status", {}).get("description"),
                # FIXED: correct logo URL format
                "home_logo": f"https://api.sofascore.app/api/v1/team/{home_id}/image",
                "away_logo": f"https://api.sofascore.app/api/v1/team/{away_id}/image",
            })
        return matches
    except Exception as e:
        return {"error": f"Match fetch failed: {str(e)}"}


# --- SECTION 2: NFL ---
@app.get("/nfl/players")
def get_nfl_players():
    # FIXED: correct ESPN API endpoint
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/athletes?limit=1000"
    try:
        r = requests.get(url, headers=ESPN_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        players = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            # ESPN athlete list returns $ref links, not inline data
            # so we pull from the athlete object if available
            athlete = item.get("athlete", {})
            if not athlete:
                continue
            players.append({
                "name": athlete.get("displayName"),
                "position": athlete.get("position", {}).get("abbreviation"),
                "team": athlete.get("team", {}).get("displayName", "Free Agent"),
                "jersey": athlete.get("jersey"),
                "headshot": athlete.get("headshot", {}).get("href"),
            })
        return players
    except Exception as e:
        return {"error": f"Failed to fetch NFL players: {str(e)}"}


# --- BONUS: NFL Scoreboard (today's games) ---
@app.get("/nfl/scores")
def get_nfl_scores():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        r = requests.get(url, headers=ESPN_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        games = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            games.append({
                "id": event.get("id"),
                "name": event.get("name"),
                "status": event.get("status", {}).get("type", {}).get("description"),
                "home_team": home.get("team", {}).get("displayName"),
                "away_team": away.get("team", {}).get("displayName"),
                "home_score": home.get("score"),
                "away_score": away.get("score"),
                "home_logo": home.get("team", {}).get("logo"),
                "away_logo": away.get("team", {}).get("logo"),
            })
        return games
    except Exception as e:
        return {"error": f"Failed to fetch NFL scores: {str(e)}"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
