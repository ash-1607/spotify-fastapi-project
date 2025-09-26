import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import HomeScreen from "./src/screens/HomeScreen";
import PlaylistsScreen from "./src/screens/PlaylistsScreen";
import PlaylistDetailScreen from './src/screens/PlaylistDetailScreen'; 
import TopTracksScreen from './src/screens/TopTracksScreen';
import TopArtistsScreen from './src/screens/TopArtistsScreen';
import ForgottenGemsScreen from './src/screens/ForgottenGemsScreen';

export type RootStackParamList = {
  Home: undefined;
  Playlists: undefined;
  PlaylistDetail: {
    playlistId: string;
    playlistName: string;
  };
  TopTracks: undefined;
  TopArtists: undefined;
  ForgottenGems: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Playlists" component={PlaylistsScreen} />
        <Stack.Screen name="PlaylistDetail" component={PlaylistDetailScreen} />
        <Stack.Screen name="TopTracks" component={TopTracksScreen} options={{ title: 'Your Top Tracks' }}/>
        <Stack.Screen name="TopArtists" component={TopArtistsScreen} options={{ title: 'Your Top Artists' }}/>
        <Stack.Screen name="ForgottenGems" component={ForgottenGemsScreen} options={{ title: 'Forgotten Gems' }}/>
      </Stack.Navigator>
    </NavigationContainer>
  );
}
