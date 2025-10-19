# app_step3.py
import os
import time
import secrets
from typing import Optional
from urllib.parse import urlencode
from io import BytesIO
from PIL import Image
import pathlib

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel 
from typing import Optional

# for playlists fetching
import logging
from fastapi import Depends, Header
from starlette.status import HTTP_401_UNAUTHORIZED

# for forgotten gems feature
import datetime

# for ai analysis
# import google.generativeai as genai
import asyncio

import base64
import json

logger = logging.getLogger(__name__)

# Add this line near your other global variables to get the logger
# logger = logging.getLogger("uvicorn")

load_dotenv()

# temporary in-memory store for one-time auth codes -> tokens
AUTH_CODES = {}  # map code -> {"tokens": {...}, "expires_at": epoch_seconds}
AUTH_CODE_TTL = 300  # seconds (5 minutes)
# NEW: Add the persistent store for mobile sessions
# This will map our new mobile_session_token -> spotify_token_dict
AUTH_SESSIONS = {}

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SPOTIFY_SCOPES = os.getenv("SPOTIFY_SCOPES", "user-read-email")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", secrets.token_urlsafe(32))
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("Redirect URI in use:", SPOTIFY_REDIRECT_URI)

AUTH_BASE = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

app = FastAPI(title="Spotify — Step 3 (OAuth + /me)") 

# Simple session cookie to hold oauth tokens (good enough for local dev)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_KEY, max_age=7*24*3600)

# --- GOOD PRACTICE: Define field masks as constants near the top ---
# We use this to ask Spotify for *only* the data we need.
TOP_TRACKS_FIELDS = "items(id,name,duration_ms,album(images),artists(name))"
TOP_ARTISTS_FIELDS = "items(id,name,genres,images)"

# ✅ Add this for React Native / mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    # generate a state just to include in the URL (optional)
    state = secrets.token_urlsafe(16)
    # NOTE: for dev/demo we are NOT saving state in the session to avoid ngrok/session cookie issues
    return RedirectResponse(oauth_url(state))

@app.get("/callback")
async def callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        raise HTTPException(400, f"Spotify returned error: {error}")
    if not code:
        raise HTTPException(400, "Missing code")

    # ==== NO state/session validation here (dev/demo only) ====

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
        # Create one-time code and store tokens server-side for the mobile app to fetch
        one_time = secrets.token_urlsafe(24)
        AUTH_CODES[one_time] = {"tokens": tokens, "expires_at": time.time() + AUTH_CODE_TTL}

        # Redirect the browser to the mobile app deep link with the one-time code
        # (Do NOT include the tokens in the URL)
        redirect_to_app = f"myapp://auth/success?code={one_time}"
        html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <title>Login complete</title>
        </head>
        <body>
            <p>Login complete. Redirecting back to app…</p>
            <script>
            // Try to open the app via the custom URI scheme
            window.location = "{redirect_to_app}";

            // Fallback: after a short time show a link the user can tap
            setTimeout(function() {{
                document.body.innerHTML += '<p>If the app did not open, <a href="{redirect_to_app}">click here</a>.</p>';
            }}, 1000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        # if any oauth_state exists, remove it (clean up)
    #     request.session.pop("oauth_state", None)
    # return RedirectResponse("/")


# 1. NEW REUSABLE REFRESH FUNCTION
# We copied this logic directly from your /me endpoint and made it a reusable helper.
async def check_and_refresh_token(session_data: dict) -> bool:
    """
    Checks if the token is expired, refreshes it if needed.
    Updates the session_data dict IN-PLACE. Returns True if refresh happened.
    """
    if int(time.time()) >= int(session_data.get("expires_at", 0)):
        logger.info("Spotify token expired, refreshing...")
        try:
            async with httpx.AsyncClient() as client:
                data = {"grant_type": "refresh_token", "refresh_token": session_data.get("refresh_token")}
                r = await client.post(TOKEN_URL, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
                
                r.raise_for_status()  # Raise an exception for 4xx/5xx errors
                
                new_data = r.json()
                # Update the session dict IN-PLACE
                session_data["access_token"] = new_data["access_token"]
                session_data["expires_at"] = int(time.time()) + int(new_data.get("expires_in", 3600)) - 30
                # Spotify sometimes issues a new refresh token, sometimes not. Be sure to save it if it exists.
                session_data["refresh_token"] = new_data.get("refresh_token", session_data.get("refresh_token"))
                
                logger.info("Token refresh successful.")
                return True
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            # Could not refresh, the session is invalid
            return False
    return False  # No refresh was needed


# 2. NEW DEPENDENCY for all mobile-authenticated routes
async def get_current_mobile_session(authorization: str = Header(None)) -> dict:
    """
    This is our FastAPI "Dependency". Any endpoint that depends on this
    will first run this code to validate the user.
    It reads the 'Authorization: Bearer <token>' header, validates our mobile token,
    finds the Spotify tokens, and refreshes them if needed.
    """
    if not authorization:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail="Authorization header missing"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail="Invalid authorization scheme. Must be 'Bearer <token>'"
        )

    # Look up the session token in our persistent mobile store
    session_data = AUTH_SESSIONS.get(token)
    if not session_data:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail="Invalid session token"
        )

    # CRITICAL STEP: Check if the token is expired and refresh it.
    # This function updates session_data in-place, which also updates
    # the entry inside the global AUTH_SESSIONS dict.
    await check_and_refresh_token(session_data)

    # Finally, return the valid (and possibly refreshed) session data
    return session_data

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

# --- DELETE your old @app.get("/me") function ---
# --- ADD this new version. It's almost identical to your /playlists endpoint ---

@app.get("/me")
async def get_user_profile_mobile(session_data: dict = Depends(get_current_mobile_session)):
    """
    Fetches the current user's profile from Spotify.
    This route is now protected by our mobile auth dependency,
    which validates the Bearer token and handles refresh.
    This is used by the mobile app to "validate" a stored session on startup.
    """
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/me", headers=headers)
            response.raise_for_status()  # Let Spotify's error pass through
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error fetching /me: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
    

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

# --- DELETE your old @app.get("/auth/profile") ---
# --- ADD this new version in its place ---

class MobileAuthBody(BaseModel):
    """The shape of the POST body our RN app will send"""
    code: str

class MobileAuthResponse(BaseModel):
    """The shape of the JSON we will send back to the RN app"""
    profile: dict  # The full Spotify user profile object
    token: str     # Our new, persistent mobile session token

@app.post("/auth/profile", response_model=MobileAuthResponse)
async def auth_profile_mobile(body: MobileAuthBody):
    """
    This is the new mobile-specific auth endpoint.
    The RN app POSTs the one-time 'code' from the deep link here.
    This endpoint:
    1. Validates the one-time code.
    2. Fetches the Spotify profile.
    3. Creates a NEW persistent mobile session token.
    4. Stores the Spotify tokens (access, refresh) against that new token.
    5. Returns both the profile AND the new session token to the app.
    """
    code = body.code
    if not code:
        raise HTTPException(400, "Missing code")

    # 1. Pop the code. It's single-use.
    entry = AUTH_CODES.pop(code, None)
    if not entry or entry.get("expires_at", 0) < time.time():
        raise HTTPException(400, "Invalid, expired, or already-used code")

    # Get the tokens we stored during /callback
    spotify_tokens = entry["tokens"]
    access_token = spotify_tokens.get("access_token")

    # 2. Get profile from Spotify
    async with httpx.AsyncClient() as client:
        r = await client.get(API_BASE + "/me", headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code != 200:
            # Token might be bad or something else went wrong
            raise HTTPException(r.status_code, r.text)
        profile_json = r.json()

    # 3. CRITICAL NEW STEP: Create the persistent mobile session
    mobile_session_token = secrets.token_urlsafe(32)
    
    # 4. Store the Spotify tokens (which we got from AUTH_CODES)
    #    in our new persistent mobile session store (AUTH_SESSIONS).
    AUTH_SESSIONS[mobile_session_token] = spotify_tokens
    
    # 5. Return BOTH the profile AND our new session token
    return {
        "profile": profile_json,
        "token": mobile_session_token
    }
    
# 3. THIS IS THE NEW /playlists ENDPOINT YOU WERE MISSING
@app.get("/playlists")
async def get_user_playlists(session_data: dict = Depends(get_current_mobile_session)):
    """
    Fetches the current user's (first 50) playlists from Spotify.
    This route is now protected by our new mobile auth dependency.
    """
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    api_url = f"{API_BASE}/me/playlists?limit=50"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()  # Let Spotify's error pass through if it fails
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error fetching playlists: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

# --- ADD THIS NEW ENDPOINT to app_step3.py ---

@app.get("/playlist/{playlist_id}")
async def get_playlist_tracks(playlist_id: str, session_data: dict = Depends(get_current_mobile_session)):
    """
    Fetches the tracks for a specific playlist from Spotify.
    Protected by our mobile 'Bearer <token>' dependency.
    """
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # We use the 'fields' param to ask Spotify for *only* the data we need.
    # This makes our app faster by reducing payload size.
    fields = "items(track(id,name,album(images),artists(name)))"
    api_url = f"{API_BASE}/playlists/{playlist_id}/tracks?limit=100&fields={fields}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error fetching playlist tracks: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

# --- ADD this new mobile logout endpoint ---

@app.post("/auth/logout")
async def auth_logout_mobile(authorization: str = Header(None)):
    """
    Logs out the mobile user by invalidating their session token.
    It manually parses the token from the header and POPS it from AUTH_SESSIONS.
    We don't need the full dependency here, since we're just deleting the key.
    """
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
        
        # Pop the session from the store. Returns None if not found, which is fine.
        popped_session = AUTH_SESSIONS.pop(token, None)
        
        if popped_session:
            logger.info(f"Invalidated session for token starting with: {token[:6]}...")
        else:
            logger.warning(f"Logout attempt for unknown token starting with: {token[:6]}...")

        return {"status": "logged_out"}

    except Exception as e:
        logger.error(f"Error during mobile logout: {e}")
        # Fail gracefully
        raise HTTPException(status_code=400, detail="Invalid authorization header for logout")
    

# TOP TRACKS/ARTISTS
@app.get("/me/top/{type}")
async def get_top_stats(
    type: str, 
    time_range: Optional[str] = "medium_term", 
    session_data: dict = Depends(get_current_mobile_session)
    ):
    # 2. Add validation for the type
    if type not in ["artists", "tracks"]:
        raise HTTPException(status_code=400, detail="Invalid type. Must be 'artists' or 'tracks'.")
    
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Dynamically choose the correct fields mask
    fields = TOP_TRACKS_FIELDS if type == "tracks" else TOP_ARTISTS_FIELDS

    # 4. Build our query params for Spotify. httpx will handle encoding this.
    params = {
        "limit": 50,
        "time_range": time_range,
        "fields": fields
    }

    api_url = f"{API_BASE}/me/top/{type}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error fetching /me/top/{type}: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.get("/currently-playing")
async def get_currently_playing(session_data: dict = Depends(get_current_mobile_session)):
    """
    Gets the user's currently playing track.
    Requires the 'user-read-currently-playing' scope.
    """
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # This Spotify endpoint includes 'market' to get the correct track data
    api_url = f"{API_BASE}/me/player/currently-playing?market=US"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)

            # --- SPECIAL HANDLING ---
            # If nothing is playing, Spotify returns a 204 No Content.
            # We will catch this and return a clean "not playing" object.
            if response.status_code == 204:
                return JSONResponse(content={"is_playing": False}, status_code=200)
            
            response.raise_for_status() # Raise errors for anything else
            
            # If status is 200, something is playing
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error fetching currently-playing: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
    

@app.post("/features/forgotten-gems")
async def create_forgotten_gems_playlist(session_data: dict = Depends(get_current_mobile_session)):
    """
    Creates a new playlist for the user containing their "Forgotten Gems"
    (tracks from their all-time top 50 that are not in their recent top 50).
    """
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Get Top 50 All-Time (long_term)
            long_term_resp = await client.get(
                f"{API_BASE}/me/top/tracks?time_range=long_term&limit=50", headers=headers
            )
            long_term_resp.raise_for_status()
            long_term_tracks = {track['id']: track for track in long_term_resp.json()['items']}

            # 2. Get Top 50 Recent (short_term)
            short_term_resp = await client.get(
                f"{API_BASE}/me/top/tracks?time_range=short_term&limit=50", headers=headers
            )
            short_term_resp.raise_for_status()
            short_term_track_ids = {track['id'] for track in short_term_resp.json()['items']}

            # 3. Find the "Forgotten Gems" using a set difference
            gem_ids = long_term_tracks.keys() - short_term_track_ids
            if not gem_ids:
                return JSONResponse(content={"name": "No forgotten gems found!", "external_urls": {"spotify": ""}}, status_code=200)

            gem_track_uris = [f"spotify:track:{id}" for id in gem_ids]

            # 4. Get the User ID
            user_profile_resp = await client.get(f"{API_BASE}/me", headers=headers)
            user_profile_resp.raise_for_status()
            user_id = user_profile_resp.json()['id']
            
            # 5. Create a new, empty playlist
            today = datetime.date.today().strftime("%b %d, %Y")
            playlist_data = {
                "name": f"Forgotten Gems ({today})",
                "description": "Your top songs from the past that you haven't listened to in a while. Curated by Rewind.",
                "public": False
            }
            create_playlist_resp = await client.post(
                f"{API_BASE}/users/{user_id}/playlists", headers=headers, json=playlist_data
            )
            create_playlist_resp.raise_for_status()
            new_playlist = create_playlist_resp.json()
            new_playlist_id = new_playlist['id']

            # 6. Add the "gem" tracks to the new playlist
            await client.post(
                f"{API_BASE}/playlists/{new_playlist_id}/tracks", headers=headers, json={"uris": gem_track_uris}
            )
            
            return new_playlist

    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error creating forgotten gems: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

@app.get("/me/ai-analysis")
async def get_ai_analysis(session_data: dict = Depends(get_current_mobile_session)):
    """
    Fetches user's Spotify data, builds a prompt, calls the Grok model
    via OpenRouter, and returns the AI-generated analysis.
    """
    access_token = session_data["access_token"]
    headers_spotify = {"Authorization": f"Bearer {access_token}"}
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    logger.info("Initialising...")

    if not openrouter_key:
        raise HTTPException(status_code=500, detail="AI service is not configured.")

    try:
        # 1. Fetch Spotify data concurrently
        async with httpx.AsyncClient() as client:
            artist_task = client.get(f"{API_BASE}/me/top/artists?limit=5&time_range=medium_term", headers=headers_spotify)
            track_task = client.get(f"{API_BASE}/me/top/tracks?limit=10&time_range=medium_term", headers=headers_spotify)
            artist_resp, track_resp = await asyncio.gather(artist_task, track_task)
            artist_resp.raise_for_status()
            track_resp.raise_for_status()

            # 2. Extract data and build the prompt from your test script's logic
            top_artists = [a.get("name", "") for a in artist_resp.json().get("items", [])]
            top_tracks = [t.get("name", "") for t in track_resp.json().get("items", [])]
            
            # --- CHANGE 2: Format tracks to include their artists ---
            top_tracks_with_artists = []
            for track in track_resp.json().get("items", []):
                if track and track.get('name') and track.get('artists'):
                    artist_names = ', '.join([a.get('name', '') for a in track['artists']])
                    top_tracks_with_artists.append(f"'{track['name']}' by {artist_names}")

            prompt = (
                f"- Top 5 Artists: {', '.join(top_artists)}\n"
                f"- Top 10 Tracks: {'; '.join(top_tracks_with_artists)}\n\n"
                "Write a witty, friendly ~100-word summary of this user's listening habits. "
                "Use light humor (no profanity), mention one clear observation (favorite artist or mood), "
                "and keep it punchy and personable. For mentioning artists, primarily use the Top 5 artists, but in case you are referring to a particular song or trying to associate an artist with a song, then you can mention the artist of that particular song. Keep output under 100 words (NOTE: do not mention the number of words used in your output)."
            )

            # 3. Call the OpenRouter API
            headers_openrouter = {
                "Authorization": f"Bearer {openrouter_key}",
            }
            # Note: httpx's `json` parameter automatically sets 'Content-Type: application/json'
            payload = {
                "model": "deepseek/deepseek-chat-v3.1:free", 
                "messages": [{"role": "user", "content": prompt}],
            }
            logger.info("Sending request...")
            response_ai = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers_openrouter,
                json=payload,
                timeout=30.0 # Give it a generous timeout
            )
            # helpful debug logging before raising
            logger.info("OpenRouter status: %s", response_ai.status_code)
            logger.info("OpenRouter body: %s", response_ai.text)
            response_ai.raise_for_status()
            
            ai_text = response_ai.json()["choices"][0]["message"]["content"].strip()

            idx = ai_text.rfind('.')

            ai_text = ai_text[: idx + 1].strip()
            
            # 4. Return the result
            return {"analysis": ai_text}

    except httpx.HTTPStatusError as e:
        logger.error(f"API error during AI analysis: {e.response.text}")
        if "openrouter" in str(e.request.url):
            raise HTTPException(status_code=502, detail="AI provider error.")
        else:
            raise HTTPException(status_code=e.response.status_code, detail="Could not fetch Spotify data.")
    except Exception as e:
        logger.exception(f"Unhandled error during AI analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during AI analysis.")


# ENDPOINT 1: Get basic playlist details
@app.get("/playlist/{playlist_id}/details")
async def get_playlist_details(playlist_id: str, session_data: dict = Depends(get_current_mobile_session)):
    """
    Gets the main playlist object (name, description, cover image) from Spotify.
    """
    access_token = session_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    api_url = f"{API_BASE}/playlists/{playlist_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Spotify API error fetching playlist details: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

# ENDPOINT 2: Generate and save AI description
@app.post("/playlist/{playlist_id}/ai-description")
async def generate_ai_description(playlist_id: str, session_data: dict = Depends(get_current_mobile_session)):
    """
    Generates a new playlist description using AI and saves it to Spotify.
    """
    access_token = session_data["access_token"]
    headers_spotify = {"Authorization": f"Bearer {access_token}"}
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if not openrouter_key:
        raise HTTPException(status_code=500, detail="AI service is not configured.")

    try:
        async with httpx.AsyncClient() as client:
            # 1. Get first 15 tracks from the playlist for context
            tracks_resp = await client.get(f"{API_BASE}/playlists/{playlist_id}/tracks?limit=15", headers=headers_spotify)
            tracks_resp.raise_for_status()
            track_names = [item['track']['name'] for item in tracks_resp.json().get('items', []) if item.get('track')]

            # 2. Build prompt and call text AI (Grok)
            prompt = f"Playlist songs: {'; '.join(track_names)}. Write a short, punchy 40-60 word playlist description that sells the vibe and suggests when to play it."
            
            headers_openrouter = {"Authorization": f"Bearer {openrouter_key}"}
            payload = {"model": "deepseek/deepseek-chat-v3.1:free", "messages": [{"role": "user", "content": prompt}]}
            response_ai = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers_openrouter, json=payload, timeout=30.0)
            response_ai.raise_for_status()
            ai_description = response_ai.json()["choices"][0]["message"]["content"].strip()

            idx = ai_description.rfind('.')

            ai_description = ai_description[: idx + 1].strip()
            
            # 3. Save the new description back to Spotify
            update_payload = {"description": ai_description}
            await client.put(f"{API_BASE}/playlists/{playlist_id}", headers=headers_spotify, json=update_payload)
            
            # 4. Return the new description to the app
            return {"description": ai_description}

    except Exception as e:
        logger.exception(f"Error generating AI description: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate playlist description.")

# Refined endpoint
@app.post("/playlist/{playlist_id}/ai-cover")
async def generate_ai_cover(playlist_id: str, session_data: dict = Depends(get_current_mobile_session)):
    access_token = session_data["access_token"]
    headers_spotify = {"Authorization": f"Bearer {access_token}"}
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    clipdrop_key = os.getenv("CLIPDROP_API_KEY")

    if not openrouter_key or not clipdrop_key:
        raise HTTPException(status_code=500, detail="AI services are not configured.")

    # Debug file paths (dev only) - change on Windows (e.g., C:\\temp\\...)
    debug_dir = "/tmp/grokai_debug"
    pathlib.Path(debug_dir).mkdir(parents=True, exist_ok=True)
    raw_debug_path = os.path.join(debug_dir, f"{playlist_id}_raw")
    jpeg_debug_path = os.path.join(debug_dir, f"{playlist_id}_jpeg.jpg")

    MAX_BYTES = 256 * 1024  # spotify limit

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 1) Fetch playlist name for context
            playlist_resp = await client.get(f"{API_BASE}/playlists/{playlist_id}", headers=headers_spotify)
            playlist_resp.raise_for_status()
            playlist_name = playlist_resp.json().get("name", "a playlist")
            logger.info(f"Generating cover for playlist '{playlist_name}' ({playlist_id})")

            # 2) Ask OpenRouter (Grok) for a short visual prompt
            prompt_input = (
                f"Based on a playlist named '{playlist_name}', write a 15-word visually descriptive prompt "
                "for an image AI to generate a cover art. Focus on mood and style. No text in the image."
            )
            headers_openrouter = {"Authorization": f"Bearer {openrouter_key}"}
            payload = {
                "model": "deepseek/deepseek-chat-v3.1:free",
                "messages": [{"role": "user", "content": prompt_input}],
                "max_tokens": 50,
            }
            resp_prompt = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers_openrouter,
                json=payload,
                timeout=30.0,
            )
            resp_prompt.raise_for_status()
            visual_prompt = resp_prompt.json()["choices"][0]["message"]["content"].strip()

            idx = visual_prompt.rfind('.')

            visual_prompt = visual_prompt[: idx + 1].strip()

            logger.info("Got visual prompt from AI.")
            logger.debug(f"Visual prompt: {visual_prompt}")

            # 3) Call Clipdrop to generate image (send JSON)
            clipdrop_url = "https://clipdrop-api.co/text-to-image/v1"
            headers_clipdrop = {"x-api-key": clipdrop_key, "Content-Type": "application/json"}
            clip_payload = {"prompt": visual_prompt}
            resp_image = await client.post(clipdrop_url, headers=headers_clipdrop, json=clip_payload, timeout=120.0)
            resp_image.raise_for_status()
            image_bytes = resp_image.content
            ct = resp_image.headers.get("content-type", "<unknown>")
            logger.info(f"Clipdrop returned content-type={ct}, size_bytes={len(image_bytes)}")

            # Save raw clipdrop bytes for inspection (dev)
            try:
                with open(raw_debug_path, "wb") as f:
                    f.write(image_bytes)
                logger.debug(f"Saved raw Clipdrop bytes to {raw_debug_path}")
            except Exception as e:
                logger.warning(f"Could not save raw debug image: {e}")

            # 4) Convert to JPEG and compress until <= MAX_BYTES
            jpeg_bytes = None
            try:
                img = Image.open(BytesIO(image_bytes)).convert("RGB")
            except Exception as e:
                logger.exception("Failed to open image returned by Clipdrop")
                raise HTTPException(status_code=500, detail="Generated image unreadable (format error).")

            # Try progressive quality reduction
            quality = 95
            while quality >= 25:
                buf = BytesIO()
                try:
                    img.save(buf, format="JPEG", quality=quality, optimize=True)
                except Exception:
                    # fallback if optimize not supported
                    img.save(buf, format="JPEG", quality=quality)
                data = buf.getvalue()
                logger.debug(f"Try quality={quality} -> size={len(data)}")
                if len(data) <= MAX_BYTES:
                    jpeg_bytes = data
                    break
                quality -= 10

            # If still too large, try resizing once and recompressing
            if jpeg_bytes is None:
                try:
                    w, h = img.size
                    img2 = img.resize((int(w * 0.8), int(h * 0.8)), Image.LANCZOS)
                    buf = BytesIO()
                    img2.save(buf, format="JPEG", quality=60, optimize=True)
                    data = buf.getvalue()
                    logger.debug(f"After resize -> size={len(data)}")
                    if len(data) <= MAX_BYTES:
                        jpeg_bytes = data
                        img = img2
                except Exception as e:
                    logger.exception("Resize attempt failed")

            if jpeg_bytes is None:
                logger.error("Generated image >256KB and compression/resizing failed")
                raise HTTPException(status_code=500, detail="Generated image too large for Spotify (>256 KB). Try a simpler prompt or enable Pillow compression.")

            # Save debug JPEG
            try:
                with open(jpeg_debug_path, "wb") as f:
                    f.write(jpeg_bytes)
                logger.info(f"Saved compressed debug image to {jpeg_debug_path} (size={len(jpeg_bytes)})")
            except Exception as e:
                logger.warning(f"Could not write compressed debug image: {e}")

            # 5) Upload to Spotify (raw JPEG bytes)
            b64_image = base64.b64encode(jpeg_bytes).decode("utf-8")

            headers_upload = headers_spotify.copy()
            headers_upload["Content-Type"] = "image/jpeg"
            upload_resp = await client.put(
                f"{API_BASE}/playlists/{playlist_id}/images",
                headers=headers_upload,
                content=b64_image,   # ✅ base64 string
                timeout=30.0,
            )

            if upload_resp.status_code not in (200, 202):
                logger.error("Spotify upload failed", {"status": upload_resp.status_code, "text": upload_resp.text})
                raise HTTPException(status_code=upload_resp.status_code, detail=f"Spotify image upload failed: {upload_resp.text}")

            logger.info("Spotify upload accepted.")

            # 6) Wait briefly for Spotify CDN to update, then fetch playlist details
            await asyncio.sleep(2)
            final_details_resp = await client.get(f"{API_BASE}/playlists/{playlist_id}", headers=headers_spotify)
            final_details_resp.raise_for_status()
            images = final_details_resp.json().get("images", [])
            new_image_url = images[0]["url"] if images else None

            logger.info(f"Returning imageUrl: {new_image_url}")
            return {"imageUrl": new_image_url}

    except httpx.HTTPStatusError as e:
        # external API error: Clipdrop/OpenRouter/Spotify network response with error code
        logger.exception(f"Error generating AI cover - HTTP: {e.response.status_code} {e.response.text}")
        # If it's an external provider error, surface the message but map to 502 (bad gateway)
        raise HTTPException(status_code=502, detail=f"External API error: {e.response.text}")
    except HTTPException:
        # re-raise HTTPErrors we created above
        raise
    except Exception as e:
        logger.exception(f"Unhandled error generating AI cover: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate playlist cover.")