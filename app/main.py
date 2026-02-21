import requests
import os
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from functools import lru_cache
import time

app = FastAPI(title="Soccer & NFL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOFA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com"
}

ESPN_HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────────────────────
# SIMPLE IN-MEMORY CACHE (backs up Redis on BE)
# ─────────────────────────────────────────────
_cache: dict = {}

def cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    return None

def cache_set(key: str, data, ttl: int = 60):
    _cache[key] = {"data": data, "expires": time.time() + ttl}

def safe_get(url: str, headers: dict, timeout: int = 10):
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERROR] GET {url} → {e}")
        return None

# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "date": date.today().isoformat()}

# ─────────────────────────────────────────────
# 1. LIVE SCORES
# ─────────────────────────────────────────────
@app.get("/football/live")
def get_live_scores():
    key = "live_scores"
    cached = cache_get(key)
    if cached:
        return cached

    today = date.today().isoformat()
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return []

    result = []
    for event in data.get("events", []):
        home_id = event["homeTeam"]["id"]
        away_id = event["awayTeam"]["id"]
        status_code = event.get("status", {}).get("code", 0)
        result.append({
            "id": event.get("id"),
            "league": event.get("tournament", {}).get("name"),
            "country": event.get("tournament", {}).get("category", {}).get("name"),
            "home_team": event["homeTeam"]["name"],
            "away_team": event["awayTeam"]["name"],
            "home_score": event.get("homeScore", {}).get("current"),
            "away_score": event.get("awayScore", {}).get("current"),
            "status": event.get("status", {}).get("description"),
            "minute": event.get("time", {}).get("currentPeriodStartTimestamp"),
            "is_live": status_code in [6, 7],      # 6=1st half, 7=2nd half
            "home_logo": f"https://api.sofascore.app/api/v1/team/{home_id}/image",
            "away_logo": f"https://api.sofascore.app/api/v1/team/{away_id}/image",
        })

    cache_set(key, result, ttl=30)   # live data: short TTL
    return result

# ─────────────────────────────────────────────
# 2. TEAMS  (by league)
# League IDs: EPL=17, La Liga=8, Serie A=23,
#             Bundesliga=35, Ligue 1=34
# ─────────────────────────────────────────────
LEAGUE_IDS = {
    "epl": 17, "laliga": 8, "seriea": 23,
    "bundesliga": 35, "ligue1": 34
}

@app.get("/football/teams")
def get_teams(league: str = Query(default="epl")):
    key = f"teams_{league}"
    cached = cache_get(key)
    if cached:
        return cached

    league_id = LEAGUE_IDS.get(league.lower(), 17)
    # Get current season
    season_url = f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/seasons"
    season_data = safe_get(season_url, SOFA_HEADERS)
    if not season_data:
        return []

    season_id = season_data["seasons"][0]["id"]

    url = f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/teams"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return []

    result = []
    for team in data.get("teams", []):
        tid = team["id"]
        result.append({
            "id": tid,
            "name": team.get("name"),
            "short_name": team.get("shortName"),
            "country": team.get("country", {}).get("name"),
            "logo": f"https://api.sofascore.app/api/v1/team/{tid}/image",
            "venue": team.get("venue", {}).get("name") if team.get("venue") else None,
        })

    cache_set(key, result, ttl=3600)
    return result

# ─────────────────────────────────────────────
# 3. PLAYERS  (by team)
# ─────────────────────────────────────────────
@app.get("/football/players")
def get_players(team_id: int = Query(..., description="SofaScore team ID")):
    key = f"players_{team_id}"
    cached = cache_get(key)
    if cached:
        return cached

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return []

    result = []
    for entry in data.get("players", []):
        p = entry.get("player", {})
        pid = p.get("id")

        # Jersey number lives on the entry, not the player object
        jersey = entry.get("jerseyNumber") or p.get("jerseyNumber") or "?"

        result.append({
            "id": pid,
            "name": p.get("name"),
            "short_name": p.get("shortName"),
            "position": p.get("position"),
            "jersey_number": jersey,
            "nationality": p.get("nationality"),
            "age": p.get("age"),
            "market_value": p.get("proposedMarketValue"),
            # FIXED: correct player image URL format
            "photo": f"https://api.sofascore.app/api/v1/player/{pid}/image",
            # BONUS: also send team logo so Angular has it available
            "team_logo": f"https://api.sofascore.app/api/v1/team/{team_id}/image",
        })

    cache_set(key, result, ttl=3600)
    return result
# ─────────────────────────────────────────────
# 4. STANDINGS
# ─────────────────────────────────────────────
@app.get("/football/standings")
def get_standings(league: str = Query(default="epl")):
    key = f"standings_{league}"
    cached = cache_get(key)
    if cached:
        return cached

    league_id = LEAGUE_IDS.get(league.lower(), 17)
    season_url = f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/seasons"
    season_data = safe_get(season_url, SOFA_HEADERS)
    if not season_data:
        return []

    season_id = season_data["seasons"][0]["id"]
    url = f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/standings/total"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return []

    result = []
    rows = data.get("standings", [{}])[0].get("rows", [])
    for row in rows:
        team = row.get("team", {})
        tid = team.get("id")
        result.append({
            "position": row.get("position"),
            "team_id": tid,
            "team": team.get("name"),
            "logo": f"https://api.sofascore.app/api/v1/team/{tid}/image",
            "played": row.get("matches"),
            "wins": row.get("wins"),
            "draws": row.get("draws"),
            "losses": row.get("losses"),
            "goals_for": row.get("scoresFor"),
            "goals_against": row.get("scoresAgainst"),
            "goal_diff": row.get("scoreDiffFormatted"),
            "points": row.get("points"),
        })

    cache_set(key, result, ttl=3600)
    return result

# ─────────────────────────────────────────────
# 5. SQUAD BUILDER — returns full squad for a team
#    (same as /players but named for Squad Builder UI)
# ─────────────────────────────────────────────
@app.get("/football/squad")
def get_squad(team_id: int = Query(..., description="SofaScore team ID")):
    key = f"squad_{team_id}"
    cached = cache_get(key)
    if cached:
        return cached

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return []

    by_position = {"Goalkeepers": [], "Defenders": [], "Midfielders": [], "Forwards": []}
    pos_map = {"G": "Goalkeepers", "D": "Defenders", "M": "Midfielders", "F": "Forwards"}

    for entry in data.get("players", []):
        p = entry.get("player", {})
        pid = p.get("id")
        pos_key = pos_map.get(p.get("position", ""), "Midfielders")
        by_position[pos_key].append({
            "id": pid,
            "name": p.get("name"),
            "short_name": p.get("shortName"),
            "position": p.get("position"),
            "jersey_number": entry.get("jerseyNumber"),
            "age": p.get("age"),
            "nationality": p.get("nationality"),
            "photo": f"https://api.sofascore.app/api/v1/player/{pid}/image",
        })

    cache_set(key, by_position, ttl=3600)
    return by_position

# ─────────────────────────────────────────────
# 6. NFL — Full rosters (all 32 teams, cached)
# ─────────────────────────────────────────────
_nfl_roster_cache = {"data": None, "expires": 0}

@app.get("/nfl/players")
def get_nfl_players():
    if _nfl_roster_cache["data"] and time.time() < _nfl_roster_cache["expires"]:
        return _nfl_roster_cache["data"]

    # Step 1: get all 32 teams
    teams_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=32"
    teams_data = safe_get(teams_url, ESPN_HEADERS)
    if not teams_data:
        return []

    teams = (teams_data.get("sports", [{}])[0]
             .get("leagues", [{}])[0]
             .get("teams", []))

    all_players = []
    for team_entry in teams:
        team = team_entry.get("team", {})
        team_id = team.get("id")
        team_name = team.get("displayName")
        abbr = team.get("abbreviation")

        roster_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/roster"
        roster = safe_get(roster_url, ESPN_HEADERS)
        if not roster:
            continue

        for group in roster.get("athletes", []):
            for athlete in group.get("items", []):
                all_players.append({
                    "id": athlete.get("id"),
                    "name": athlete.get("displayName"),
                    "position": athlete.get("position", {}).get("abbreviation"),
                    "jersey": athlete.get("jersey"),
                    "team": team_name,
                    "team_abbr": abbr,
                    "age": athlete.get("age"),
                    "headshot": athlete.get("headshot", {}).get("href"),
                    "status": athlete.get("status", {}).get("type"),
                })

    # Cache for 6 hours — rosters don't change often
    _nfl_roster_cache["data"] = all_players
    _nfl_roster_cache["expires"] = time.time() + 21600
    return all_players

@app.get("/nfl/scores")
def get_nfl_scores():
    cached = cache_get("nfl_scores")
    if cached:
        return cached

    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    data = safe_get(url, ESPN_HEADERS)
    if not data:
        return []

    games = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
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

    cache_set("nfl_scores", games, ttl=30)
    return games
from fastapi.responses import Response

# ─── IMAGE PROXY ───
@app.get("/proxy/image")
def proxy_image(url: str = Query(...)):
    """
    Proxies SofaScore images so browser doesn't get blocked.
    Usage: /proxy/image?url=https://api.sofascore.app/api/v1/player/123/image
    """
    try:
        r = requests.get(url, headers=SOFA_HEADERS, timeout=5)
        return Response(
            content=r.content,
            media_type=r.headers.get("content-type", "image/png")
        )
    except:
        # Return a transparent 1x1 PNG so UI doesn't break
        import base64
        empty = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
        return Response(content=empty, media_type="image/png")
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
