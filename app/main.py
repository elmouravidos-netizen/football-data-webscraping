import requests
import os
import uvicorn
import json
import time
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import date
from upstash_redis import Redis

app = FastAPI(title="Soccer & NFL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# UPSTASH REDIS CONNECTION
# ─────────────────────────────────────────────
redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL", ""),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN", ""),
)

# ─────────────────────────────────────────────
# HEADERS
# ─────────────────────────────────────────────
SOFA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com"
}
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────────────────────
# REDIS CACHE HELPERS
# ─────────────────────────────────────────────
def redis_get(key: str):
    """Get from Upstash Redis. Returns None if missing or Redis is down."""
    try:
        val = redis.get(key)
        if val:
            print(f"[REDIS HIT] {key}")
            return json.loads(val)
    except Exception as e:
        print(f"[REDIS ERROR] get {key}: {e}")
    return None

def redis_set(key: str, data, ttl: int):
    """Save to Upstash Redis with TTL. Silent fail if Redis is down."""
    try:
        redis.set(key, json.dumps(data), ex=ttl)
        print(f"[REDIS SET] {key} TTL={ttl}s")
    except Exception as e:
        print(f"[REDIS ERROR] set {key}: {e}")

# ─────────────────────────────────────────────
# HTTP HELPER
# ─────────────────────────────────────────────
def safe_get(url: str, headers: dict, timeout: int = 10):
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[FETCH ERROR] {url}: {e}")
        return None

# ─────────────────────────────────────────────
# LEAGUE IDS
# ─────────────────────────────────────────────
LEAGUE_IDS = {
    "epl": 17, "laliga": 8, "seriea": 23,
    "bundesliga": 35, "ligue1": 34
}

# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────
@app.get("/")
def health():
    # Test Redis connection
    redis_ok = False
    try:
        redis.set("health_check", "ok", ex=10)
        redis_ok = redis.get("health_check") == "ok"
    except:
        pass
    return {
        "status": "ok",
        "date": date.today().isoformat(),
        "redis": "connected" if redis_ok else "disconnected"
    }

# ─────────────────────────────────────────────
# 1. LIVE SCORES  (TTL: 30s — changes fast)
# ─────────────────────────────────────────────
@app.get("/football/live")
def get_live_scores():
    key = "live_scores"
    cached = redis_get(key)
    if cached is not None:
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
            "is_live": status_code in [6, 7],
            "home_logo": f"https://api.sofascore.app/api/v1/team/{home_id}/image",
            "away_logo": f"https://api.sofascore.app/api/v1/team/{away_id}/image",
        })

    redis_set(key, result, ttl=30)
    return result

# ─────────────────────────────────────────────
# 2. TEAMS  (TTL: 6hrs — rarely changes)
# ─────────────────────────────────────────────
@app.get("/football/teams")
def get_teams(league: str = Query(default="epl")):
    key = f"teams_{league}"
    cached = redis_get(key)
    if cached is not None:
        return cached

    league_id = LEAGUE_IDS.get(league.lower(), 17)
    season_data = safe_get(
        f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/seasons",
        SOFA_HEADERS
    )
    if not season_data:
        return []

    season_id = season_data["seasons"][0]["id"]
    data = safe_get(
        f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/teams",
        SOFA_HEADERS
    )
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
        })

    redis_set(key, result, ttl=21600)
    return result

# ─────────────────────────────────────────────
# 3. PLAYERS  (TTL: 6hrs)
# ─────────────────────────────────────────────
@app.get("/football/players")
def get_players(team_id: int = Query(...)):
    key = f"players_{team_id}"
    cached = redis_get(key)
    if cached is not None:
        return cached

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return []

    result = []
    for entry in data.get("players", []):
        p = entry.get("player", {})
        pid = p.get("id")
        jersey = entry.get("jerseyNumber") or p.get("jerseyNumber") or "?"
        result.append({
            "id": pid,
            "name": p.get("name"),
            "short_name": p.get("shortName"),
            "position": p.get("position"),
            "jersey_number": jersey,
            "nationality": p.get("nationality"),
            "age": p.get("age"),
            "photo": f"https://api.sofascore.app/api/v1/player/{pid}/image",
            "team_logo": f"https://api.sofascore.app/api/v1/team/{team_id}/image",
        })

    redis_set(key, result, ttl=21600)
    return result

# ─────────────────────────────────────────────
# 4. STANDINGS  (TTL: 1hr)
# ─────────────────────────────────────────────
@app.get("/football/standings")
def get_standings(league: str = Query(default="epl")):
    key = f"standings_{league}"
    cached = redis_get(key)
    if cached is not None:
        return cached

    league_id = LEAGUE_IDS.get(league.lower(), 17)
    season_data = safe_get(
        f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/seasons",
        SOFA_HEADERS
    )
    if not season_data:
        return []

    season_id = season_data["seasons"][0]["id"]
    data = safe_get(
        f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/standings/total",
        SOFA_HEADERS
    )
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

    redis_set(key, result, ttl=3600)
    return result

# ─────────────────────────────────────────────
# 5. SQUAD BUILDER  (TTL: 6hrs)
# ─────────────────────────────────────────────
@app.get("/football/squad")
def get_squad(team_id: int = Query(...)):
    key = f"squad_{team_id}"
    cached = redis_get(key)
    if cached is not None:
        return cached

    url = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
    data = safe_get(url, SOFA_HEADERS)
    if not data:
        return {}

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
            "jersey_number": entry.get("jerseyNumber") or "?",
            "age": p.get("age"),
            "nationality": p.get("nationality"),
            "photo": f"https://api.sofascore.app/api/v1/player/{pid}/image",
        })

    redis_set(key, by_position, ttl=21600)
    return by_position

# ─────────────────────────────────────────────
# 6. NFL PLAYERS  (TTL: 12hrs)
# ─────────────────────────────────────────────
@app.get("/nfl/players")
def get_nfl_players():
    key = "nfl_players"
    cached = redis_get(key)
    if cached is not None:
        return cached

    teams_data = safe_get(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=32",
        ESPN_HEADERS
    )
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

        roster = safe_get(
            f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/roster",
            ESPN_HEADERS
        )
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
                })

    redis_set(key, all_players, ttl=43200)
    return all_players

# ─────────────────────────────────────────────
# 7. NFL SCORES  (TTL: 30s)
# ─────────────────────────────────────────────
@app.get("/nfl/scores")
def get_nfl_scores():
    key = "nfl_scores"
    cached = redis_get(key)
    if cached is not None:
        return cached

    data = safe_get(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
        ESPN_HEADERS
    )
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

    redis_set(key, games, ttl=30)
    return games

# ─────────────────────────────────────────────
# 8. IMAGE PROXY
# ─────────────────────────────────────────────
@app.get("/proxy/image")
def proxy_image(url: str = Query(...)):
    try:
        r = requests.get(url, headers=SOFA_HEADERS, timeout=5)
        return Response(content=r.content, media_type=r.headers.get("content-type", "image/png"))
    except:
        import base64
        empty = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
        return Response(content=empty, media_type="image/png")

# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

Delete all of this from your file:
```
```
---
## Verify it's working
After you deploy, visit your Railway URL and check the health endpoint:
```
https://YOUR-RAILWAY-URL/
