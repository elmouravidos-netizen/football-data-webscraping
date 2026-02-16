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
