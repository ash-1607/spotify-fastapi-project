// src/screens/PlaylistDetailScreen.tsx

import React, { useEffect, useState, useLayoutEffect } from 'react';
import {
  FlatList,
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Image,
  TouchableOpacity,
  Alert
} from 'react-native';
import { useRoute, RouteProp, useNavigation } from '@react-navigation/native';
import { RootStackParamList } from '../../App'; // Adjust path if needed
import api from '../api';
import { PlaylistItem, PlaylistTracksResponse, SimplifiedPlaylist } from '../types';
import { SafeAreaView } from 'react-native-safe-area-context';

// Define the type for our route parameters
type PlaylistDetailRouteProp = RouteProp<
  RootStackParamList,
  'PlaylistDetail'
>;

// A new component to render a single Track item
const TrackItem = ({ item }: { item: PlaylistItem }) => {
  const { track } = item;
  if (!track) return null; // Some playlist items might be null (e.g., deleted)

  return (
    <View style={styles.trackContainer}>
      <Image
        source={{ uri: track.album.images[0]?.url || 'https://via.placeholder.com/50' }}
        style={styles.trackImage}
      />
      <View style={styles.trackTextContainer}>
        <Text style={styles.trackName} numberOfLines={1}>
          {track.name}
        </Text>
        <Text style={styles.trackArtist} numberOfLines={1}>
          {track.artists.map(artist => artist.name).join(', ')}
        </Text>
      </View>
    </View>
  );
};

// --- NEW HEADER COMPONENT ---
// This will display the cover art and description at the top of the list.
const PlaylistHeader = ({ playlist }: { playlist: SimplifiedPlaylist | null }) => {
  if (!playlist) return <ActivityIndicator style={{ marginVertical: 20 }} />;
  return (
    <View style={styles.headerContainer}>
      <Image
        source={{ uri: playlist.images[0]?.url || 'https://via.placeholder.com/150' }}
        style={styles.playlistImage}
      />
      <Text style={styles.playlistName}>{playlist.name}</Text>
      <Text style={styles.playlistDescription}>
        {playlist.description || 'No description provided. Tap 📝 to generate one!'}
      </Text>
    </View>
  );
};


const PlaylistDetailScreen = () => {
  const route = useRoute<PlaylistDetailRouteProp>();
  const navigation = useNavigation();
  const { playlistId, playlistName } = route.params;

  // --- 1. UPDATED STATE ---
  const [playlist, setPlaylist] = useState<SimplifiedPlaylist | null>(null);
  const [tracks, setTracks] = useState<PlaylistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isGeneratingDesc, setIsGeneratingDesc] = useState(false);
  const [isGeneratingCover, setIsGeneratingCover] = useState(false);

  // Set the screen title to the playlist name
  useLayoutEffect(() => {
    navigation.setOptions({
      title: playlistName,
    });
  }, [navigation, playlistName]);

  // useEffect(() => {
  //   const fetchTracks = async () => {
  //     try {
  //       setLoading(true);
  //       setError(null);
  //       // Call our new backend endpoint
  //       const response = await api.get<PlaylistTracksResponse>(
  //         `/playlist/${playlistId}`,
  //       );
  //       //TO LOG AND CHECK WHAT THE RESPONSE IS RETURNING FOR NULL SONGS
  //       console.log(JSON.stringify(response.data.items, null, 2));

  //       // This will correctly filter out those "broken" gap items.
  //       const validTracks = response.data.items.filter(item => item.track.name);
  //       setTracks(validTracks);
  //     } catch (err: any) {
  //       console.error('Failed to fetch playlist tracks:', err);
  //       setError(err.response?.data?.detail || 'Failed to load tracks.');
  //     } finally {
  //       setLoading(false);
  //     }
  //   };

  //   fetchTracks();
  // }, [playlistId]); // Re-run if the playlistId ever changes

  // if (loading) {
  //   return (
  //     <SafeAreaView style={styles.centered}>
  //       <ActivityIndicator size="large" />
  //     </SafeAreaView>
  //   );
  // }

  // if (error) {
  //   return (
  //     <SafeAreaView style={styles.centered}>
  //       <Text style={styles.errorText}>{error}</Text>
  //     </SafeAreaView>
  //   );
  // }

  // --- 2. UPDATED DATA FETCHING ---
  const fetchPlaylistData = async () => {
    setLoading(true);
    try {
      // Fetch both details and tracks at the same time for better performance
      const [detailsResponse, tracksResponse] = await Promise.all([
        api.get<SimplifiedPlaylist>(`/playlist/${playlistId}/details`),
        api.get<PlaylistTracksResponse>(`/playlist/${playlistId}/tracks`),
      ]);
      
      setPlaylist(detailsResponse.data);

      const validTracks = tracksResponse.data.items.filter(
        item => item.track && item.track.album && item.track.artists && item.track.name !== ""
      );
      setTracks(validTracks);

    } catch (err: any) {
      console.error('Failed to fetch playlist data:', err);
      setError(err.response?.data?.detail || 'Failed to load playlist.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlaylistData();
  }, [playlistId]);

  // --- 4. NEW HANDLER FUNCTIONS ---
  const handleGenerateDescription = async () => {
    setIsGeneratingDesc(true);
    try {
      const response = await api.post<{ description: string }>(`/playlist/${playlistId}/ai-description`);
      // Update local state to show new description instantly
      setPlaylist(prev => (prev ? { ...prev, description: response.data.description } : null));
    } catch (err: any) {
      Alert.alert('Error', err.response?.data?.detail || 'Could not generate description.');
    } finally {
      setIsGeneratingDesc(false);
    }
  };

  const handleGenerateCover = async () => {
    setIsGeneratingCover(true);
    try {
      const response = await api.post<{ imageUrl: string }>(`/playlist/${playlistId}/ai-cover`);
      // Update local state to show new image instantly
      setPlaylist(prev => (prev ? { ...prev, images: [{ url: response.data.imageUrl, height: null, width: null }] } : null));
    } catch (err: any) {
      Alert.alert('Error', err.response?.data?.detail || 'Could not generate cover.');
    } finally {
      setIsGeneratingCover(false);
    }
  };

  if (loading) {
    return <SafeAreaView style={styles.centered}><ActivityIndicator size="large" /></SafeAreaView>;
  }

  if (error) {
    return <SafeAreaView style={styles.centered}><Text style={styles.errorText}>{error}</Text></SafeAreaView>;
  }

  
  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={tracks}
        renderItem={TrackItem}
        keyExtractor={(item, index) => `${index}-${item.track.id}`}
        // --- 3. UPDATED UI (HEADER) ---
        ListHeaderComponent={<PlaylistHeader playlist={playlist} />}
      />

      {/* --- 3. UPDATED UI (FLOATING BUTTONS) --- */}
      <View style={styles.fabContainer}>
        <TouchableOpacity style={styles.fab} onPress={handleGenerateDescription} disabled={isGeneratingDesc || isGeneratingCover}>
          {isGeneratingDesc ? <ActivityIndicator color="#fff" /> : <Text style={styles.fabText}>📝</Text>}
        </TouchableOpacity>
        <TouchableOpacity style={styles.fab} onPress={handleGenerateCover} disabled={isGeneratingDesc || isGeneratingCover}>
          {isGeneratingCover ? <ActivityIndicator color="#fff" /> : <Text style={styles.fabText}>🎨</Text>}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  container: { flex: 1 },
  errorText: { color: 'red' },
  trackContainer: { flexDirection: 'row', alignItems: 'center', padding: 12 },
  trackImage: { width: 50, height: 50, marginRight: 12, borderRadius: 4 },
  trackTextContainer: { flex: 1 },
  trackName: { fontSize: 16, fontWeight: '600' },
  trackArtist: { fontSize: 14, color: '#666', marginTop: 4 },
  // --- NEW STYLES ---
  headerContainer: {
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 30,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  playlistImage: {
    width: 180,
    height: 180,
    borderRadius: 8,
    marginBottom: 15,
  },
  playlistName: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  playlistDescription: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
  },
  fabContainer: {
    position: 'absolute',
    bottom: 30,
    right: 20,
    flexDirection: 'column',
    gap: 15,
  },
  fab: {
    backgroundColor: '#1DB954', // Spotify Green
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8, // Android shadow
    shadowColor: '#000', // iOS shadow
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  fabText: {
    fontSize: 24,
  },
});

export default PlaylistDetailScreen;