// src/screens/TopTracksScreen.tsx

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Image,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../api';
import { Track, TopTracksResponse } from '../types';

type TimeRange = 'short_term' | 'medium_term' | 'long_term';

// This component renders a single track row.
// It's almost identical to our 'TrackItem' from PlaylistDetailScreen.
const TrackRow = ({ item, index }: { item: Track; index: number }) => {
  return (
    <View style={styles.trackContainer}>
      <Text style={styles.trackNumber}>{index + 1}</Text>
      <Image
        source={{ uri: item.album.images[0]?.url || 'https://via.placeholder.com/50' }}
        style={styles.trackImage}
      />
      <View style={styles.trackTextContainer}>
        <Text style={styles.trackName} numberOfLines={1}>
          {item.name}
        </Text>
        <Text style={styles.trackArtist} numberOfLines={1}>
          {item.artists.map(artist => artist.name).join(', ')}
        </Text>
      </View>
    </View>
  );
};

// This is the main screen component
const TopTracksScreen = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tracks, setTracks] = useState<Track[]>([]);
  // 1. Add state for the time range, default to 'medium_term'
  const [timeRange, setTimeRange] = useState<TimeRange>('medium_term');

  // 2. This effect will re-run whenever 'timeRange' state changes
  useEffect(() => {
    const fetchTopTracks = async () => {
      setLoading(true);
      setError(null);
      try {
        // 3. Call our new backend endpoint, passing the timeRange as a query param
        const response = await api.get<TopTracksResponse>(
          `/me/top/tracks?time_range=${timeRange}`,
        );
        setTracks(response.data.items);
      } catch (err: any) {
        console.error('Failed to fetch top tracks:', err);
        setError(err.response?.data?.detail || 'Failed to load tracks.');
      } finally {
        setLoading(false);
      }
    };

    fetchTopTracks();
  }, [timeRange]); // <-- Dependency array ensures this runs when timeRange changes

  // Helper component for the toggle buttons
  const TimeRangeToggle = () => (
    <View style={styles.toggleContainer}>
      <TouchableOpacity
        style={[styles.toggleButton, timeRange === 'short_term' && styles.toggleActive]}
        onPress={() => setTimeRange('short_term')}>
        <Text style={[styles.toggleText, timeRange === 'short_term' && styles.toggleActiveText]}>
          Last 4 Weeks
        </Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.toggleButton, timeRange === 'medium_term' && styles.toggleActive]}
        onPress={() => setTimeRange('medium_term')}>
        <Text style={[styles.toggleText, timeRange === 'medium_term' && styles.toggleActiveText]}>
          Last 6 Months
        </Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.toggleButton, timeRange === 'long_term' && styles.toggleActive]}
        onPress={() => setTimeRange('long_term')}>
        <Text style={[styles.toggleText, timeRange === 'long_term' && styles.toggleActiveText]}>
          All Time
        </Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={tracks}
        renderItem={({ item, index }) => <TrackRow item={item} index={index} />}
        keyExtractor={(item, index) => `${index}-${item.id}`}
        ListHeaderComponent={
          <>
            <TimeRangeToggle />
            {loading && <ActivityIndicator size="large" style={{ marginVertical: 20 }} />}
            {error && <Text style={styles.errorText}>{error}</Text>}
          </>
        }
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  toggleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 10,
    backgroundColor: '#f8f8f8',
  },
  toggleButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
    backgroundColor: '#eee',
  },
  toggleActive: {
    backgroundColor: '#1DB954', // Spotify Green
  },
  toggleText: {
    fontWeight: '600',
    color: '#000',
  },
  toggleActiveText: {
    color: '#fff',
  },
  errorText: {
    color: 'red',
    textAlign: 'center',
    margin: 20,
  },
  trackContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  trackNumber: {
    fontSize: 16,
    color: '#666',
    width: 30,
    textAlign: 'center',
  },
  trackImage: {
    width: 50,
    height: 50,
    marginRight: 12,
    marginLeft: 4,
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

export default TopTracksScreen;