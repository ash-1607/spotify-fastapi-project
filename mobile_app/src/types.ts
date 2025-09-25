// src/types.ts
// This will give us full type-safety for the data we're getting from Spotify.

export interface SpotifyImage {
  url: string;
  height: number | null;
  width: number | null;
}

export interface PlaylistTrackInfo {
  total: number;
}

export interface PlaylistOwner {
  display_name: string;
  id: string;
}

// This is the individual playlist item
export interface SimplifiedPlaylist {
  id: string;
  name: string;
  images: SpotifyImage[];
  tracks: PlaylistTrackInfo;
  owner: PlaylistOwner;
}

// This is the full wrapper object our /playlists endpoint returns
export interface PlaylistPagingObject {
  items: SimplifiedPlaylist[];
  total: number;
  limit: number;
  offset: number;
  href: string;
  next: string | null;
  previous: string | null;
}

//FOR VIEWING TRACKS IN THE PLAYLIST
export interface Artist {
  id: string;
  name: string;
  images?: SpotifyImage[]; // Add this (make it optional)
  genres?: string[];      // Add this (make it optional)
}

export interface Album {
  id: string;
  name: string;
  images: SpotifyImage[];
}

export interface Track {
  id: string;
  name: string;
  album: Album;
  artists: Artist[];
}

export interface PlaylistItem {
  track: Track;
}

// This is the object our new /playlist/{id} endpoint will return
export interface PlaylistTracksResponse {
  items: PlaylistItem[];
}

// This is what our backend's /me/top/tracks endpoint returns
export interface TopTracksResponse {
  items: Track[];
  total: number;
  limit: number;
  offset: number;
}

// This is what our backend's /me/top/artists endpoint returns
export interface TopArtistsResponse {
  items: Artist[];
  total: number;
  limit: number;
  offset: number;
}

// This is the object returned by the /currently-playing endpoint
export interface NowPlayingResponse {
  is_playing: boolean;
  progress_ms: number;
  item: Track; // The full track object
}

export interface UserProfile {
  display_name: string;
  email: string;
  id: string;
}