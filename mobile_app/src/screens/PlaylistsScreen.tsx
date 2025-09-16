// src/screens/PlaylistsScreen.tsx

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Image,
  // SafeAreaView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context'; // <--- ADD THIS NEW LINE
import api from '../api'; // Import our central, AUTHENTICATED api instance
import { SimplifiedPlaylist, PlaylistPagingObject } from '../types'; // Import our types

/**
 * A reusable component to render a single row in our playlist.
 */
const PlaylistItem = ({ item }: { item: SimplifiedPlaylist }) => (
  // We'll make this a button later to navigate to a PlaylistDetail screen
  <TouchableOpacity style={styles.itemContainer} activeOpacity={0.7}>
    <Image
      // Use the first image URL, or a placeholder if no image exists
      source={{ uri: item.images[0]?.url || 'https://via.placeholder.com/60' }}
      style={styles.playlistImage}
    />
    <View style={styles.textContainer}>
      <Text style={styles.playlistName} numberOfLines={1}>
        {item.name}
      </Text>
      <Text style={styles.trackInfo} numberOfLines={1}>
        By {item.owner.display_name} • {item.tracks.total} tracks
      </Text>
    </View>
  </TouchableOpacity>
);

/**
 * This is the main screen component.
 */
const PlaylistsScreen = () => {
  const [playlists, setPlaylists] = useState<SimplifiedPlaylist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // This useEffect hook runs once when the component (screen) mounts
  useEffect(() => {
    const fetchPlaylists = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // This is the API call. It already has the Auth header thanks to our
        // login flow in HomeScreen! This calls our FastAPI /playlists endpoint.
        const response = await api.get<PlaylistPagingObject>('/playlists');
        
        // Save the 'items' array from the response into our state
        setPlaylists(response.data.items);
      } catch (err: any) {
        console.error('Failed to fetch playlists:', err);
        const detail = err.response?.data?.detail || 'Failed to load playlists.';
        setError(`Error: ${detail}`);
        Alert.alert("Error fetching playlists", detail);
      } finally {
        // Whether it succeeded or failed, stop loading
        setLoading(false);
      }
    };

    fetchPlaylists();
  }, []); // The empty array [] means this effect runs only once on mount

  // Render a loading spinner while data is being fetched
  if (loading) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>Loading your playlists...</Text>
      </SafeAreaView>
    );
  }

  // Render an error message if the API call failed
  if (error) {
    return (
      <SafeAreaView style={styles.centered}>
        <Text style={styles.errorText}>{error}</Text>
      </SafeAreaView>
    );
  }

  // Render the list of playlists
  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={playlists}
        renderItem={PlaylistItem} // Use our custom row component
        keyExtractor={item => item.id}
        ListHeaderComponent={<Text style={styles.header}>Your Playlists</Text>}
        contentContainerStyle={{ paddingBottom: 20 }}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#fff',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#333',
  },
  errorText: {
    color: 'red',
    fontSize: 16,
    textAlign: 'center',
  },
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    fontSize: 28,
    fontWeight: 'bold',
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 10,
    color: '#111'
  },
  itemContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    alignItems: 'center',
  },
  playlistImage: {
    width: 60,
    height: 60,
    marginRight: 12,
    borderRadius: 4, // Spotify playlist images are often square, but rounded edges look good
    backgroundColor: '#eee', // Placeholder bg color
  },
  textContainer: {
    flex: 1, // Allows text to truncate correctly
    justifyContent: 'center',
  },
  playlistName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
  },
  trackInfo: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
});

export default PlaylistsScreen;