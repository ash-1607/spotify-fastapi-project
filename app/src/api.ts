// import axios from "axios";

// const API_BASE = "https://658a2340decb.ngrok-free.app";

// const api = axios.create({
//   baseURL: API_BASE,
//   withCredentials: true,
// });

// export default api;

// src/api.ts
import axios from 'axios';

// ✅ This URL looks correct for now.
// WARNING: Remember to update this every time you restart ngrok!
const API_BASE_URL = 'https://groovifyspotifyapiproject.vercel.app';

const api = axios.create({
  baseURL: API_BASE_URL,
  // ❌ DO NOT include 'withCredentials: true'.
  // Our new mobile auth flow uses Bearer Tokens (in the Authorization header),
  // not cookies. Keeping this will cause CORS errors.
});

/**
 * This is the crucial helper function our login logic needs.
 * It takes the mobile session token we get from '/auth/profile'
 * and dynamically adds it as the default 'Authorization' header for
 * ALL future requests made with this 'api' instance (e.g., /playlists).
 */
export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    // If logging out, remove the header
    delete api.defaults.headers.common['Authorization'];
  }
};

export default api;