// src/screens/AIAnalysisScreen.tsx

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Button,
//   SafeAreaView,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../api';

const AIAnalysisScreen = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<string | null>(null);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    try {
      const response = await api.get<{ ai_analysis: string }>('/me/ai-analysis');
      setAnalysis(response.data.ai_analysis);
    } catch (err: any) {
      console.error('Failed to fetch AI analysis:', err);
      setError(err.response?.data?.detail || 'Failed to get analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Text style={styles.title}>Your Personal AI Music Analyst</Text>
        <Text style={styles.description}>
          Get a unique analysis of your music taste based on your top
          artists and tracks, written by Generative AI.
        </Text>
        
        <View style={styles.buttonWrapper}>
          <Button
            title={loading ? 'Thinking...' : 'Analyze My Taste!'}
            onPress={fetchAnalysis}
            disabled={loading}
          />
        </View>

        {loading && <ActivityIndicator size="large" style={styles.loading} />}

        {error && <Text style={styles.errorText}>{error}</Text>}

        {analysis && (
          <View style={styles.analysisBox}>
            <Text style={styles.analysisText}>{analysis}</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollContainer: {
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
  },
  buttonWrapper: {
    width: '80%',
    marginVertical: 20,
  },
  loading: {
    marginVertical: 20,
  },
  errorText: {
    color: 'red',
    fontSize: 16,
    textAlign: 'center',
  },
  analysisBox: {
    marginTop: 20,
    backgroundColor: '#f8f8f8',
    borderRadius: 10,
    padding: 20,
    width: '100%',
  },
  analysisText: {
    fontSize: 17,
    color: '#333',
    lineHeight: 25,
  },
});

export default AIAnalysisScreen;