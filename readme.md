# Full-Stack Spotify Demo (FastAPI + React Native)

A simple demo project that securely connects a React Native mobile app to the Spotify API using a FastAPI (Python) backend.

This project uses a **Backend-for-Frontend (BFF)** pattern: the mobile app *only* talks to our backend, and the backend handles all secure OAuth and Spotify API calls.

## Project Structure

This is a monorepo containing both the backend and frontend:

* `/backend`: The FastAPI (Python) server.
* `/mobile-app`: The React Native (TypeScript) mobile application.

## How to Run

You will need **3 terminals** running at the same time.

---

### Terminal 1: Run the Backend (FastAPI)

1.  Create a `.env` file in this folder with your Spotify API keys.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the server:

```bash
cd backend
uvicorn app_step3:app --host 0.0.0.0 --port 8000
```
### Terminal 2: Run the Tunnel (ngrok)

Spotify's API requires a public HTTPS URL.
```bash
ngrok http 8000
```

**IMPORTANT**: You must copy the https URL from ngrok and paste it into:

1. Your Spotify Developer Dashboard (as a Redirect URI).

2. Your backend/.env file.

3. Your mobile-app/src/api.ts file.

### Terminal 3: Run the Mobile App (React Native)
1. Install dependencies: 
```bash
npm cd mobile-app
```
2. Run the app
```bash
npx react-native run-ios
# OR
npx react-native run-android
```
