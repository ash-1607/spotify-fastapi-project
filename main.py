# app_step1.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse

# app_step2.py
import os
import secrets
from urllib.parse import urlencode
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")
SPOTIFY_SCOPES = os.getenv("SPOTIFY_SCOPES", "user-read-email")
AUTH_BASE = "https://accounts.spotify.com/authorize"

app = FastAPI(title="Spotify with login redirect")

def make_oauth_url(state: str) -> str:
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPES,
        "state": state,
        "show_dialog": "false",
    }
    return f"{AUTH_BASE}?{urlencode(params)}"

@app.get("/", response_class=HTMLResponse)
def root():
    return "<h3>Spotify FastAPI — Step 2</h3><p><a href='/login'>Login with Spotify</a></p>"
def root():
    return "<h3>Spotify FastAPI — Step 1</h3><p><a href='/health'>/health</a></p>"

@app.get("/login")
def login():
    # generate a random state token — we'll use a proper session next step
    state = secrets.token_urlsafe(16)
    # note: for now we don't persist state on the server (this is a simple dev example)
    return RedirectResponse(make_oauth_url(state))

@app.get("/health")
def health():
    return {"status": "ok"}