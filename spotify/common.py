import spotipy
from spotipy.oauth2 import SpotifyOAuth
from configparser import ConfigParser
from pathlib import Path
import inquirer
from typing import TypedDict

from logger import FileLogger

INI_PATH = "config.ini"
parser = ConfigParser()
logger = FileLogger("spotify.log")


class PlaylistInfo(TypedDict):
    name: str
    id: str
    track_count: int


class Config:
    def __init__(self) -> None:
        global parser
        parser.read(INI_PATH)
        # Remove escape characters from the path and convert to Path object
        raw_path = parser.get("common", "path").replace("\\", "")
        self.media_path = Path(raw_path)
        # Spotify config
        self.client_id = parser.get("spotify", "client_id")
        self.client_secret = parser.get("spotify", "client_secret")
        self.redirect_uri = parser.get("spotify", "redirect_uri")
        # Try to get playlist_id, None if not set
        self.playlist_id = parser.get("spotify", "playlist_id", fallback=None)

    @staticmethod
    def write() -> None:
        """write ini file, with current vars"""
        global parser
        with open(INI_PATH, "w") as f:
            parser.write(f)


def setup_spotify() -> spotipy.Spotify:
    """Initialize Spotify client with proper permissions"""
    config = Config()
    scope = "playlist-modify-public playlist-modify-private playlist-read-private user-library-read"
    logger.info("Initializing Spotify client...")
    logger.info(f"Using client_id: {config.client_id}")
    logger.info(f"Using redirect_uri: {config.redirect_uri}")
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=scope,
            open_browser=True,
            cache_path=".spotify_token_cache"
        )
    )


def list_user_playlists(sp: spotipy.Spotify) -> list[PlaylistInfo]:
    """Get all playlists owned by the user

    Returns:
        list: List of dicts containing playlist info (name, id, track_count)
    """
    logger.info("Fetching your Spotify playlists...")
    user_id = sp.current_user()["id"]

    # Filter playlists owned by user and format output
    user_playlists: list[PlaylistInfo] = []
    
    # Add Liked Songs as first option
    try:
        liked_tracks = sp.current_user_saved_tracks()
        user_playlists.append(
            {
                "name": "Liked Songs",
                "id": "liked",  # Special ID for liked songs
                "track_count": liked_tracks["total"],
            }
        )
    except Exception as e:
        logger.warning(f"Could not get liked songs count: {e}")

    # Add regular playlists with pagination
    playlists_response = sp.current_user_playlists(limit=50)  # Get max items per page
    while playlists_response:
        for playlist in playlists_response["items"]:
            if playlist["owner"]["id"] == user_id:
                user_playlists.append(
                    {
                        "name": playlist["name"],
                        "id": playlist["id"],
                        "track_count": playlist["tracks"]["total"],
                    }
                )
        
        # Get next page if available
        if playlists_response["next"]:
            playlists_response = sp.next(playlists_response)
        else:
            break

    return user_playlists


def select_playlist(sp: spotipy.Spotify, playlist_id: str | None = None) -> str:
    """Get playlist ID from config or prompt user to select one"""
    if playlist_id:
        try:
            if playlist_id == "liked":
                # Special case for Liked Songs
                liked_tracks = sp.current_user_saved_tracks()
                logger.success('Using Spotify playlist: "Liked Songs"')
                return playlist_id
            else:
                playlist = sp.playlist(playlist_id)
                logger.success(f'Using Spotify playlist: "{playlist["name"]}"')
                return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(sp)

    if not playlists:
        raise Exception("No playlists found for user")

    # Create choices list for inquirer with formatted display
    choices = [
        (f"{playlist['name']} ({playlist['track_count']} tracks)", playlist["id"])
        for playlist in playlists
    ]

    questions = [
        inquirer.List(
            "playlist_id",
            message="Select a Spotify playlist",
            choices=choices,
            carousel=True,  # Show all options without scrolling
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using Spotify playlist: "{selected_name}"')
    return selected_id
