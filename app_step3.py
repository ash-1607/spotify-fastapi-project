# app_step3.py
import os
import time
import secrets
from typing import Optional
from urllib.parse import urlencode

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")
SPOTIFY_SCOPES = os.getenv("SPOTIFY_SCOPES", "user-read-email")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", secrets.token_urlsafe(32))
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

AUTH_BASE = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

app = FastAPI(title="Spotify — Step 3 (OAuth + /me)") 

# Simple session cookie to hold oauth tokens (good enough for local dev)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_KEY, max_age=7*24*3600)


def oauth_url(state: str) -> str:
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPES,
        "state": state,
        "show_dialog": "true",   # 👈 force Spotify to ask again
    }
    return f"{AUTH_BASE}?{urlencode(params)}"

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if "spotify_tokens" in request.session:
        return "<p>✅ Logged in — <a href='/me'>/me</a> | <a href='/logout'>Logout</a></p>"
    return "<p>❌ Not logged in — <a href='/login'>Login with Spotify</a></p>"

@app.get("/login")
def login(request: Request):
    state = secrets.token_urlsafe(16)
    # store state in the session to validate in callback (simple CSRF protection)
    request.session["oauth_state"] = state
    return RedirectResponse(oauth_url(state))

@app.get("/callback")
async def callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        raise HTTPException(400, f"Spotify returned error: {error}")
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    saved_state = request.session.get("oauth_state")
    if not saved_state or saved_state != state:
        raise HTTPException(400, "Invalid state (possible CSRF)")
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        }
        r = await client.post(TOKEN_URL, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
        if r.status_code != 200:
            raise HTTPException(400, f"Token exchange failed: {r.text}")
        tokens = r.json()
        tokens["expires_at"] = int(time.time()) + int(tokens.get("expires_in", 3600)) - 30
        request.session["spotify_tokens"] = tokens
        # remove oauth_state (no longer needed)
        request.session.pop("oauth_state", None)
    return RedirectResponse("/")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/me")
async def me(request: Request):
    tokens = request.session.get("spotify_tokens")
    if not tokens:
        raise HTTPException(401, "Not logged in")
    # refresh if expired
    if int(time.time()) >= int(tokens.get("expires_at", 0)):
        async with httpx.AsyncClient() as client:
            data = {"grant_type": "refresh_token", "refresh_token": tokens.get("refresh_token")}
            r = await client.post(TOKEN_URL, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
            if r.status_code != 200:
                raise HTTPException(400, f"Token refresh failed: {r.text}")
            new = r.json()
            new["expires_at"] = int(time.time()) + int(new.get("expires_in", 3600)) - 30
            new.setdefault("refresh_token", tokens.get("refresh_token"))
            request.session["spotify_tokens"] = new
            tokens = new
    # call Spotify /me
    async with httpx.AsyncClient() as client:
        r = await client.get(API_BASE + "/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.text)
        return r.json()
    

@app.get("/artist/{artist_id}")
async def get_artist(artist_id:str, request: Request):
    tokens = request.session.get("spotify_tokens")

    if not tokens:
        raise HTTPException(401, "Not logged in")
    
    # Refresh access token if expired (same logic as /me)
    if int(time.time()) >= int(tokens.get("expires_at", 0)):
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.get("refresh_token")
            }
            r = await client.post(TOKEN_URL, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
            if r.status_code != 200:
                raise HTTPException(400, f"Token refresh failed: {r.text}")
            new = r.json()
            new["expires_at"] = int(time.time()) + int(new.get("expires_in", 3600)) - 30
            new.setdefault("refresh_token", tokens.get("refresh_token"))
            request.session["spotify_tokens"] = new
            tokens = new

    # Call Spotify artist endpoint
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{API_BASE}/artists/{artist_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.text)
        return r.json()