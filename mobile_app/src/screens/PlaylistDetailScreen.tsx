// src/screens/PlaylistDetailScreen.tsx

import React, { useEffect, useState, useLayoutEffect } from 'react';
import {
  FlatList,
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Image,
} from 'react-native';
import { useRoute, RouteProp, useNavigation } from '@react-navigation/native';
import { RootStackParamList } from '../../App'; // Adjust path if needed
import api from '../api';
import { PlaylistItem, PlaylistTracksResponse, Track } from '../types';
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

const PlaylistDetailScreen = () => {
  const route = useRoute<PlaylistDetailRouteProp>();
  const navigation = useNavigation();
  const { playlistId, playlistName } = route.params;

  const [tracks, setTracks] = useState<PlaylistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Set the screen title to the playlist name
  useLayoutEffect(() => {
    navigation.setOptions({
      title: playlistName,
    });
  }, [navigation, playlistName]);

  useEffect(() => {
    const fetchTracks = async () => {
      try {
        setLoading(true);
        setError(null);
        // Call our new backend endpoint
        const response = await api.get<PlaylistTracksResponse>(
          `/playlist/${playlistId}`,
        );
        //TO LOG AND CHECK WHAT THE RESPONSE IS RETURNING FOR NULL SONGS
        console.log(JSON.stringify(response.data.items, null, 2));

        // This will correctly filter out those "broken" gap items.
        const validTracks = response.data.items.filter(item => item.track.name);
        setTracks(validTracks);
      } catch (err: any) {
        console.error('Failed to fetch playlist tracks:', err);
        setError(err.response?.data?.detail || 'Failed to load tracks.');
      } finally {
        setLoading(false);
      }
    };

    fetchTracks();
  }, [playlistId]); // Re-run if the playlistId ever changes

  if (loading) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.centered}>
        <Text style={styles.errorText}>{error}</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={tracks}
        renderItem={TrackItem}
        keyExtractor={(item, index) => `${index}-${item.track.id}`}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    flex: 1,
  },
  errorText: {
    color: 'red',
  },
  trackContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
  },
  trackImage: {
    width: 50,
    height: 50,
    marginRight: 12,
    borderRadius: 4,
  },
  trackTextContainer: {
    flex: 1,
  },
  trackName: {
    fontSize: 16,
    fontWeight: '600',
  },
  trackArtist: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
});

export default PlaylistDetailScreen;