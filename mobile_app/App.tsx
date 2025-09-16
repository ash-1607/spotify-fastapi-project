import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import HomeScreen from "./src/screens/HomeScreen";
import PlaylistsScreen from "./src/screens/PlaylistsScreen";

export type RootStackParamList = {
  Home: undefined;
  Playlists: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Playlists" component={PlaylistsScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
