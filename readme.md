# Spotify FastAPI Project

A simple FastAPI backend that integrates with the **Spotify Web API**.  
Supports OAuth login, profile fetch (`/me`), artist lookup by ID, and secure token refresh.

---

## Features
- 🔑 Login with Spotify (OAuth2 Authorization Code flow)
- 👤 Get current user profile (`/me`)
- 🎵 Fetch artist details by ID (`/artist/{id}`)
- 🚪 Logout and clear session
- 🔄 Automatic token refresh when expired

---

## Tech Stack
- **Python 3.8+**
- **FastAPI** (backend framework)
- **httpx** (async HTTP client)
- **Uvicorn** (ASGI server)
- **Spotify Web API**

---

## Setup

### 1. Clone this repo
```bash
git clone https://github.com/<your-username>/spotify-fastapi-project.git
cd spotify-fastapi-project

### 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

### 3. Install dependencies
pip install -r requirements.txt

### 4. Set up environment variables (Create a .env file in the project root)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/callback
APP_SECRET_KEY=your_random_secret_key

### 5. Run the server
uvicorn app_step3:app --reload
```