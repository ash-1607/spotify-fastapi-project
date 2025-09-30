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
import { Artist, TopArtistsResponse } from '../types';

type TimeRange = 'short_term' | 'medium_term' | 'long_term';

// Component to render a single Artist row
const ArtistRow = ({ item, index }: { item: Artist; index: number }) => {
  // Artist images are often round in Spotify
  const imageUri = item.images?.[0]?.url || 'https://via.placeholder.com/50';
  const genre = item.genres?.[0] || 'artist'; // Show the first genre as a subtitle

  return (
    <View style={styles.artistContainer}>
      <Text style={styles.trackNumber}>{index + 1}</Text>
      <Image source={{ uri: imageUri }} style={styles.artistImage} />
      <View style={styles.trackTextContainer}>
        <Text style={styles.trackName} numberOfLines={1}>
          {item.name}
        </Text>
        <Text style={styles.trackArtist} numberOfLines={1}>
          {genre}
        </Text>
      </View>
    </View>
  );
};

// This is the main screen component
const TopArtistsScreen = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('medium_term');

  // This effect re-runs whenever 'timeRange' changes
  useEffect(() => {
    const fetchTopArtists = async () => {
      setLoading(true);
      setError(null);
      try {
        // Call the *same* backend endpoint, but with type='artists'
        const response = await api.get<TopArtistsResponse>(
          `/me/top/artists?time_range=${timeRange}`,
        );
        setArtists(response.data.items);
      } catch (err: any) {
        console.error('Failed to fetch top artists:', err);
        let errorMsg = 'Failed to load artists. Please try again.';
        if (err.response?.data?.detail?.error?.message) {
           errorMsg = err.response.data.detail.error.message;
        }
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchTopArtists();
  }, [timeRange]); // Dependency array

  // This toggle component is identical to the one in TopTracksScreen
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
        data={artists}
        renderItem={({ item, index }) => <ArtistRow item={item} index={index} />}
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

// We can reuse most of the styles from TopTracksScreen
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
  artistContainer: {
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
  artistImage: { // Artists often have round profile pics
    width: 50,
    height: 50,
    marginRight: 12,
    marginLeft: 4,
    borderRadius: 25, // Make it a circle
    backgroundColor: '#eee',
  },
  trackTextContainer: {
    flex: 1,
  },
  trackName: {
    fontSize: 16,
    fontWeight: '600',
  },
  trackArtist: { // Re-using style, but this is for 'genre'
    fontSize: 14,
    color: '#666',
    marginTop: 4,
    textTransform: 'capitalize', // Genres often look better capitalized
  },
});

export default TopArtistsScreen;