# Import all functions from dedicated files
from spotify.config import Config
from spotify.types import SpotifyPlaylistInfo
from spotify.setup_spotify import setup_spotify
from spotify.list_user_playlists import list_user_playlists
from spotify.select_playlist import select_playlist
from spotify.get_spotify_track_details import get_spotify_track_details
from spotify.get_spotify_track_ids import get_spotify_track_ids
from spotify.search_spotify_track import search_spotify_track
from spotify.select_match import select_match
from spotify.add_track_to_spotify import add_track_to_spotify

__all__ = [
    "Config",
    "SpotifyPlaylistInfo",
    "setup_spotify",
    "list_user_playlists",
    "select_playlist",
    "get_spotify_track_details",
    "get_spotify_track_ids",
    "search_spotify_track",
    "select_match",
    "add_track_to_spotify",
]
