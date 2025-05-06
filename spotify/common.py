import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pathlib import Path
import inquirer
from typing import TypedDict
import tomllib

from logger import FileLogger

TOML_PATH = "config.toml"
logger = FileLogger("spotify.log")


class PlaylistInfo(TypedDict):
    name: str
    id: str
    track_count: int


class Config:
    def __init__(self) -> None:
        with open(TOML_PATH, "rb") as f:
            config = tomllib.load(f)
        
        # Remove escape characters from the path and convert to Path object
        raw_path = config["common"]["path"].replace("\\", "")
        self.media_path = Path(raw_path)
        
        # Spotify config
        spotify_config = config["spotify"]
        self.client_id = spotify_config["client_id"]
        self.client_secret = spotify_config["client_secret"]
        self.redirect_uri = spotify_config["redirect_uri"]
        # Try to get playlist_id, None if not set
        self.playlist_id = spotify_config.get("playlist_id")

    @staticmethod
    def write(config_data: dict) -> None:
        """write toml file with current vars"""
        with open(TOML_PATH, "w") as f:
            f.write("[common]\n")
            f.write(f'path = "{config_data["media_path"]}"\n\n')
            f.write("[spotify]\n")
            f.write(f'client_id = "{config_data["client_id"]}"\n')
            f.write(f'client_secret = "{config_data["client_secret"]}"\n')
            f.write(f'redirect_uri = "{config_data["redirect_uri"]}"\n')
            if config_data.get("playlist_id"):
                f.write(f'playlist_id = "{config_data["playlist_id"]}"\n')


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
                try:
                    sp.current_user_saved_tracks(limit=1)  # Just check if we can access liked tracks
                    logger.success('Using Spotify playlist: "Liked Songs"')
                    return playlist_id
                except Exception as e:
                    logger.error(f"Error accessing liked songs: {e}")
                    # Fall through to manual selection
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
