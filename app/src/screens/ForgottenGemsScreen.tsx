// src/screens/ForgottenGemsScreen.tsx

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Button,
  SafeAreaView,
  Linking,
  Alert,
} from 'react-native';
import api from '../api';

interface NewPlaylist {
  name: string;
  external_urls: {
    spotify: string;
  };
}

const ForgottenGemsScreen = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newPlaylist, setNewPlaylist] = useState<NewPlaylist | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setNewPlaylist(null);
    try {
      const response = await api.post<NewPlaylist>('/features/forgotten-gems');
      setNewPlaylist(response.data);
    } catch (err: any) {
      console.error('Failed to create playlist:', err);
      const errorDetail = err.response?.data?.detail?.error?.message || 'Could not create playlist.';
      setError(errorDetail);
      Alert.alert('Error', errorDetail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Rediscover Your Favorites</Text>
        <Text style={styles.description}>
          This feature analyzes your all-time top songs and compares them to
          your recent listening history. It will create a new private playlist
          for you, filled with songs you used to love but haven't heard in a while.
        </Text>

        <View style={styles.buttonWrapper}>
          <Button
            title={loading ? 'Curating Your Playlist...' : 'Find My Forgotten Gems'}
            onPress={handleGenerate}
            disabled={loading}
          />
        </View>

        {loading && <ActivityIndicator size="large" style={styles.loading} />}

        {newPlaylist && (
          <View style={styles.successBox}>
            <Text style={styles.successTitle}>Success! ✅</Text>
            <Text style={styles.successText}>
              Your new playlist, "{newPlaylist.name}", has been created in your
              Spotify library.
            </Text>
            <Button
              title="Open in Spotify"
              onPress={() => Linking.openURL(newPlaylist.external_urls.spotify)}
            />
          </View>
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  description: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginVertical: 15,
    lineHeight: 24,
  },
  buttonWrapper: {
    width: '80%',
    marginVertical: 20,
  },
  loading: {
    marginVertical: 20,
  },
  successBox: {
    marginTop: 30,
    backgroundColor: '#E8F5E9', // Light green
    borderRadius: 10,
    padding: 20,
    width: '100%',
    alignItems: 'center',
  },
  successTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  successText: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
});

export default ForgottenGemsScreen;