import React, { useState, useEffect } from "react";
import { Text, Button, StyleSheet, Linking, Alert, View, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import InAppBrowser from "react-native-inappbrowser-reborn";
import api, { setAuthToken } from "../api"; // 👈 Make sure to import setAuthToken
import AsyncStorage from '@react-native-async-storage/async-storage'; // Import AsyncStorage

// Define shapes
interface UserProfile {
  display_name: string;
  email: string;
  id: string;
}

interface AuthResponse {
  profile: UserProfile;
  token: string; // This is our new mobile session token
}

const STORAGE_KEY = 'spotify_session_token'; // Define key for AsyncStorage

export default function HomeScreen({ navigation }: any) {
  const [user, setUser] = useState<UserProfile | null>(null);
  // Add a new loading state for the initial session check
  const [loading, setLoading] = useState(true); // Start true to check session

  // --- NEW: Session Loading Effect ---
  // This effect runs ONCE when the app starts.
  useEffect(() => {
    const loadSession = async () => {
      try {
        // 1. Check if we have a token stored on the device
        const storedToken = await AsyncStorage.getItem(STORAGE_KEY);
        if (!storedToken) {
          console.log('No stored token found.');
          setLoading(false); // No token, stop loading, show login button
          return;
        }

        console.log('Found stored token, validating...');
        // 2. We found a token. Set it on our API instance.
        setAuthToken(storedToken);
        
        // 3. Validate the token by fetching the user profile from our NEW /me endpoint
        const response = await api.get<UserProfile>('/me');
        
        // 4. Success! The token is valid.
        setUser(response.data);
        console.log('Session restored successfully.');

      } catch (err: any) {
        // 5. This block runs if the token is expired/invalid (e.g., backend 401)
        console.error('Failed to restore session:', err.response?.data?.detail || err.message);
        // Clear the bad token from storage
        await AsyncStorage.removeItem(STORAGE_KEY);
        setAuthToken(null); // Clear header from api instance
      } finally {
        // Whether we succeeded or failed, we are done loading.
        setLoading(false);
      }
    };

    loadSession();
  }, []); // Empty array = runs only ONCE on app mount.

  useEffect(() => {
    Linking.getInitialURL().then(url => {
      if (url) handleDeepLink(url);
    });

    const sub = Linking.addEventListener("url", ({ url }) => handleDeepLink(url));
    return () => sub.remove();
  }, []);
  // Note: This is a separate effect just for the listener


  // 👇 REPLACE your old handleDeepLink function with this one
  const handleDeepLink = async (url: string) => {
    console.log("Deep link received:", url);

    // Check if this is the correct deep link before proceeding
    if (!url || !url.includes("myapp://auth/success?code=")) {
      return;
    }

    try {
      // 1. Parse the one-time code from the URL string
      const code = url.split("?code=")[1].split("&")[0];
      if (!code) {
        throw new Error("No code found in redirect URL");
      }

      // 2. Exchange the one-time code for profile + mobile session token
      //    This calls the NEW 'POST /auth/profile' backend endpoint we built
      const response = await api.post<AuthResponse>("/auth/profile", { code: code });

      const { profile, token } = response.data;

      // 3. SUCCESS! Set the profile to update the UI
      setUser(profile);

      // 4. CRITICAL: Save the session token in our api instance header.
      //    This makes ALL FUTURE requests (like /playlists) authenticated!
      setAuthToken(token);

      // *** NEW STEP: Save the token to persistent storage ***
      await AsyncStorage.setItem(STORAGE_KEY, token);
      console.log('New session token saved to storage.');

    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || "Could not fetch profile after login.";
      Alert.alert("Error", errorDetail);
      console.error(err);
    }
  };

  const handleLogin = async () => {
    try {
      if (await InAppBrowser.isAvailable()) {
        await InAppBrowser.open(`${api.defaults.baseURL}/login`);
      } else {
        Linking.openURL(`${api.defaults.baseURL}/login`);
      }
    } catch (err) {
      console.error("Login error", err);
    }
  };

  // --- NEW: Logout Handler ---
  const handleLogout = async () => {
    try {
      // 1. Tell the backend to invalidate this token (good security practice)
      await api.post('/auth/logout'); 
      console.log('Server session invalidated.');
    } catch (err: any) {
      console.error("Error logging out from server, continuing client-side logout.", err.response?.data);
    } finally {
      // 2. Clear the token from the API header
      setAuthToken(null);
      // 3. Clear the token from device storage
      await AsyncStorage.removeItem(STORAGE_KEY);
      // 4. Clear the user from React state (this shows the login button again)
      setUser(null);
    }
  };


  // const fetchProfile = async () => {
  //   try {
  //     const response = await axios.get<UserProfile>(`${api.defaults.baseURL}/me`, {
  //       withCredentials: true,
  //     });
  //     setUser(response.data);
  //   } catch (err) {
  //     console.error("Error fetching profile", err);
  //   }
  // };


  // --- RENDER LOGIC ---

  // Show a full-screen loader while we check for an existing session
  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" />
        <Text style={styles.text}>Restoring session...</Text>
      </SafeAreaView>
    );
  }

  // If NOT loading, and no user exists, show Login button
  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.title}>🎵 Spotify FastAPI Demo</Text>
        <Button title="Login with Spotify" onPress={handleLogin} />
      </SafeAreaView>
    );
  }

  // Otherwise, we ARE logged in. Show the profile and other buttons.
  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>✅ Logged in as</Text>
      <Text style={styles.text}>{user.display_name}</Text>
      <Text style={styles.text}>{user.email}</Text>
      
      <View style={styles.buttonContainer}>
        <Button
          title="View My Playlists"
          onPress={() => navigation.navigate('Playlists')}
        />

        <Button
          title="View Top Tracks"
          onPress={() => navigation.navigate('TopTracks')}
        />

        <Button
          title="View Top Artists"
          onPress={() => navigation.navigate('TopArtists')}
        />

        <Button
          title="Logout"
          onPress={handleLogout}
          color="#FF5A5F"
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
    // backgroundColor: "#000000ff",
  },
  title: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 20,
    // backgroundColor: "#ffffff"
  },
  text: {
    fontSize: 16,
    marginTop: 10,
    // backgroundColor: "#ffffff"
  },
  buttonContainer: {
    marginTop: 30,
    width: '80%',
    gap: 15, // Adds vertical spacing between buttons
  }
});
