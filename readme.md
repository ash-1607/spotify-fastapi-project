# Spotify FastAPI Project

A simple FastAPI backend that integrates with the **Spotify Web API**.  
Supports OAuth login, profile fetch (`/me`), artist lookup by ID, and secure token refresh.

## Features
- Login with Spotify (OAuth)
- Get current user profile (`/me`)
- Fetch artist details by ID (`/artist/{id}`)
- Logout

## Tech Stack
- Python 3.8+
- FastAPI
- httpx
- Spotify Web API

## Setup
1. Clone this repo  
   ```bash
   git clone https://github.com/<your-username>/spotify-fastapi-project.git
   cd spotify-fastapi-project
