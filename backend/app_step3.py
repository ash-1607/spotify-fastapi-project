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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel 

# for playlists fetching
import logging
from fastapi import Depends, Header
from starlette.status import HTTP_401_UNAUTHORIZED
# Add this line near your other global variables to get the logger
logger = logging.getLogger("uvicorn")

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

print("Redirect URI in use:", SPOTIFY_REDIRECT_URI)

AUTH_BASE = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

app = FastAPI(title="Spotify — Step 3 (OAuth + /me)") 

# Simple session cookie to hold oauth tokens (good enough for local dev)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_KEY, max_age=7*24*3600)

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

# @app.get("/login")
# def login(request: Request):
#     state = secrets.token_urlsafe(16)
#     # store state in the session to validate in callback (simple CSRF protection)
#     request.session["oauth_state"] = state
#     return RedirectResponse(oauth_url(state))
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

# @app.get("/callback")
# async def callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
#     if error:
#         raise HTTPException(400, f"Spotify returned error: {error}")
#     if not code or not state:
#         raise HTTPException(400, "Missing code or state")
#     saved_state = request.session.get("oauth_state")
#     if not saved_state or saved_state != state:
#         raise HTTPException(400, "Invalid state (possible CSRF)")
    
#     # Exchange code for tokens
#     async with httpx.AsyncClient() as client:
#         data = {
#             "grant_type": "authorization_code",
#             "code": code,
#             "redirect_uri": SPOTIFY_REDIRECT_URI,
#         }
#         r = await client.post(TOKEN_URL, data=data, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
#         if r.status_code != 200:
#             raise HTTPException(400, f"Token exchange failed: {r.text}")
#         tokens = r.json()
#         tokens["expires_at"] = int(time.time()) + int(tokens.get("expires_in", 3600)) - 30
#         request.session["spotify_tokens"] = tokens
#         # remove oauth_state (no longer needed)
#         request.session.pop("oauth_state", None)
#     return RedirectResponse("/")

# --- ADD ALL THIS CODE TO app_step3.py ---


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
    
# @app.get("/auth/profile")
# async def auth_profile(code: Optional[str] = None):
#     """
#     Exchange a one-time code (issued at /callback) for the user's Spotify profile.
#     Single-use and short-lived.
#     """
#     if not code:
#         raise HTTPException(400, "Missing code")

#     entry = AUTH_CODES.pop(code, None)  # single-use: pop immediately
#     if not entry or entry.get("expires_at", 0) < time.time():
#         raise HTTPException(400, "Invalid or expired code")

#     tokens = entry["tokens"]
#     access_token = tokens.get("access_token")
#     if not access_token:
#         raise HTTPException(400, "No access token available")

#     # call Spotify /me with the stored access token
#     async with httpx.AsyncClient() as client:
#         r = await client.get(API_BASE + "/me", headers={"Authorization": f"Bearer {access_token}"})
#         if r.status_code != 200:
#             # pass through error
#             raise HTTPException(r.status_code, r.text)
#         return r.json()


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