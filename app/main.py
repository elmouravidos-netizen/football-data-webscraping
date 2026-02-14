from fastapi import FastAPI
from fbref.fbref_player_data import load_fbref_player_data

app = FastAPI()

@app.get("/")
def home():
return {"status": "API is running"}

@app.get("/players")
def players():
url = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
df = load_fbref_player_data(url)
return df.head(20).to_dict(orient="records")
