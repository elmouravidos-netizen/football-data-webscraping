import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
import os

app = FastAPI()

# Match your React frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2026 Bypass Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.sofascore.com",
    "Origin": "https://www.sofascore.com"
}

@app.get("/")
def home():
    return {"status": "API Active", "date": date.today().isoformat()}

@app.get("/matches")
def get_live_results():
    """Fetches real football matches and scores for today."""
    today = date.today().isoformat()
    # Official SofaScore internal API for daily events
    url = f"https://api.sofascore.com{today}"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        cleaned_matches = []
        for event in data.get("events", []):
            # Extracting logos using SofaScore's image CDN
            home_id = event.get("homeTeam", {}).get("id")
            away_id = event.get("awayTeam", {}).get("id")
            
            cleaned_matches.append({
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
        return cleaned_matches

    except Exception as e:
        return {"error": f"Scraper failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
