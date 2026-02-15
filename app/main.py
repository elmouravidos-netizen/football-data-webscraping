from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API is running"}

@app.get("/players")
def players():
return [
    {"name": "Lionel Messi", "club": "Inter Miami"},
    {"name": "Cristiano Ronaldo", "club": "Al Nassr"},
    {"name": "Kylian Mbappe", "club": "PSG"}
]
