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