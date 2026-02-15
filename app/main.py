from fastapi import FastAPI

app = FastAPI()

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
