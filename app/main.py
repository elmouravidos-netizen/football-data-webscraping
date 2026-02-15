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
