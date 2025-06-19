# Import all functions from dedicated files
from ytmusic.config import Config
from ytmusic.types import YTMusicPlaylistInfo
from ytmusic.setup_ytmusic import setup_ytmusic
from ytmusic.check_ytmusic_setup_oauth import check_ytmusic_setup_oauth
from ytmusic.check_ytmusic_setup_browser import check_ytmusic_setup_browser
from ytmusic.choose_auth_method import choose_auth_method
from ytmusic.list_user_playlists import list_user_playlists
from ytmusic.select_playlist import select_playlist
from ytmusic.get_ytmusic_track_details import get_ytmusic_track_details
from ytmusic.get_ytmusic_track_ids import get_ytmusic_track_ids
from ytmusic.create_playlist import create_playlist
from ytmusic.search_ytmusic_track import search_ytmusic_track
from ytmusic.select_match import select_match
from ytmusic.add_track_to_ytmusic import add_track_to_ytmusic

__all__ = [
    "Config",
    "YTMusicPlaylistInfo",
    "setup_ytmusic",
    "check_ytmusic_setup_oauth",
    "check_ytmusic_setup_browser",
    "choose_auth_method",
    "list_user_playlists",
    "select_playlist",
    "get_ytmusic_track_details",
    "get_ytmusic_track_ids",
    "create_playlist",
    "search_ytmusic_track",
    "select_match",
    "add_track_to_ytmusic",
]
