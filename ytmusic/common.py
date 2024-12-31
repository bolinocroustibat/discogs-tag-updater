from ytmusicapi import YTMusic
from configparser import ConfigParser
from pathlib import Path

import inquirer

from logger import FileLogger

INI_PATH = "config.ini"
parser = ConfigParser()
logger = FileLogger("ytmusic.log")


class Config:
    def __init__(self) -> None:
        global parser
        parser.read(INI_PATH)
        # Remove escape characters from the path and convert to Path object
        raw_path = parser.get("common", "path").replace("\\", "")
        self.media_path = Path(raw_path)
        # Try to get playlist_id, None if not set
        self.playlist_id = parser.get("ytmusic", "playlist_id", fallback=None)

    @staticmethod
    def write() -> None:
        """write ini file, with current vars"""
        global parser
        with open(INI_PATH, "w") as f:
            parser.write(f)


def setup_ytmusic() -> YTMusic:
    """Initialize YouTube Music client
    Note: First time setup requires running YTMusic.setup(filepath="oauth.json")
    """
    return YTMusic("oauth.json")


def list_user_playlists(ytm: YTMusic) -> list:
    """Get all playlists owned by the user

    Returns:
        list: List of dicts containing playlist info (name, id, track_count)
    """
    logger.info("Fetching your YouTube Music playlists...")
    playlists = ytm.get_library_playlists()

    # Format output
    user_playlists = []
    for playlist in playlists:
        user_playlists.append(
            {
                "name": playlist["title"],
                "id": playlist["playlistId"],
                "track_count": playlist["count"],
            }
        )

    return user_playlists


def select_playlist(ytm: YTMusic, playlist_id: str = None) -> str:
    """Get playlist ID from config or prompt user to select one"""
    if playlist_id:
        try:
            playlist = ytm.get_playlist(playlist_id)
            logger.success(f'Using playlist: "{playlist["title"]}"')
            return playlist_id
        except Exception as e:
            logger.error(f"Error accessing playlist: {e}")
            # Fall through to manual selection

    # Get user's playlists
    playlists = list_user_playlists(ytm)

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
            message="Select a playlist",
            choices=choices,
            carousel=True,
        )
    ]

    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Playlist selection cancelled")

    selected_id = answers["playlist_id"]
    selected_name = next(p["name"] for p in playlists if p["id"] == selected_id)
    logger.success(f'Using playlist: "{selected_name}"')
    return selected_id
